"""FastAPI boundary for temporary paired-raster uploads."""
from contextlib import asynccontextmanager
from functools import lru_cache
from io import BytesIO
import json
import logging
import time
from zipfile import ZipFile, ZIP_STORED

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .inference import ROOT, Predictor
from .evaluation import comparison_images, evaluate_mask, read_reference
from .preprocessing import InputError, MAX_FILE_BYTES, read_pair
from .visualization import geotiff_base64, png_bytes, png_url, previews, result_images
from .water_separation import load_reference, separation_result

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    app.state.predictor = None
    app.state.load_error = None
    try:
        app.state.predictor = await run_in_threadpool(Predictor)
    except Exception:
        logger.exception("D4 startup failed")
        app.state.load_error = "Model unavailable. Check the bundled checkpoint and normalization files."
    yield


app = FastAPI(title="D4 Flood Segmentation", version="1.0.0", lifespan=lifespan, docs_url=None, redoc_url=None)
app.mount("/api/docs-assets", StaticFiles(directory=ROOT / "backend/static/docs"), name="docs-assets")


@app.get("/docs", include_in_schema=False)
def documentation():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="D4 API documentation",
                               swagger_js_url="/api/docs-assets/swagger-ui-bundle.js",
                               swagger_css_url="/api/docs-assets/swagger-ui.css",
                               swagger_favicon_url="/api/docs-assets/favicon-32x32.png",
                               swagger_ui_parameters={"validatorUrl": None})


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        hand_test = scope["path"] in ("/api/hand-test/preview", "/api/hand-test/predict")
        limit = (3 if hand_test else 2) * MAX_FILE_BYTES + 65536
        limit_error = "The triplet exceeds the 48 MiB upload limit." if hand_test else "The pair exceeds the 32 MiB upload limit."
        headers = dict(scope["headers"])
        try:
            too_large = int(headers.get(b"content-length", b"0")) > limit
        except ValueError:
            return await JSONResponse({"detail": "Invalid Content-Length."}, status_code=400)(scope, receive, send)
        if too_large:
            return await JSONResponse({"detail": limit_error}, status_code=413)(scope, receive, send)
        total = 0

        async def bounded_receive():
            nonlocal total
            message = await receive()
            total += len(message.get("body", b""))
            if total > limit:
                raise HTTPException(413, limit_error)
            return message

        await self.app(scope, bounded_receive, send)


app.add_middleware(BodyLimit)


def predictor():
    service = getattr(app.state, "predictor", None)
    if service is None:
        raise HTTPException(503, getattr(app.state, "load_error", None) or "Model is starting. Please retry shortly.")
    return service


@app.exception_handler(InputError)
async def input_error(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=422)


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logger.error("Request failed", exc_info=(type(exc), exc, exc.__traceback__))
    return JSONResponse({"detail": "Prediction failed. Check the backend logs and retry."}, status_code=500)


@app.get("/api/health")
def health():
    service = getattr(app.state, "predictor", None)
    return JSONResponse({"status": "ready" if service else "unavailable", "model_ready": service is not None,
                         "device": str(service.device) if service else None}, status_code=200 if service else 503)


@app.get("/api/model-info")
def model_info():
    service = predictor()
    return {**service.info, "device": str(service.device)}


async def uploaded_pair(request, s1, s2):
    service = predictor()
    try:
        form = await request.form()
        if len(form.multi_items()) != 2 or len(form.getlist("s1")) != 1 or len(form.getlist("s2")) != 1:
            raise InputError("Upload exactly one S1 and one S2 file, not several pairs or extra files.")
        a = await s1.read(MAX_FILE_BYTES + 1)
        b = await s2.read(MAX_FILE_BYTES + 1)
        return await run_in_threadpool(read_pair, a, b, s1.filename or "", s2.filename or "", service.statistics)
    finally:
        await s1.close()
        await s2.close()


@app.post("/api/preview")
async def preview(request: Request, s1: UploadFile = File(...), s2: UploadFile = File(...)):
    pair = await uploaded_pair(request, s1, s2)
    rgb, radar = await run_in_threadpool(previews, pair)
    _, separation = await run_in_threadpool(load_reference, pair, ROOT)
    return {"tile_id": pair.tile_id, "width": 512, "height": 512, "rgb": png_url(rgb), "radar": png_url(radar),
            "water_separation": separation}


def predict_result(pair, service, started, reference=None):
    mask, inference_ms = service.predict(pair)
    images = result_images(pair, mask)
    geotiff = geotiff_base64(pair, mask)
    separation = separation_result(pair, mask, ROOT)
    extra = {}
    if reference is not None:
        images.update(comparison_images(reference, mask))
        extra["evaluation"] = evaluate_mask(mask, reference)
    return {"tile_id": pair.tile_id, "width": 512, "height": 512, "device": str(service.device),
            "threshold": 0.5, "patch_count": 4, "inference_ms": round(inference_ms, 2),
            "processing_ms": round((time.perf_counter() - started) * 1000, 2),
            "images": images, "mask_geotiff_base64": geotiff, "water_separation": separation, **extra}


@app.post("/api/predict")
async def predict(request: Request, s1: UploadFile = File(...), s2: UploadFile = File(...)):
    started = time.perf_counter()
    pair = await uploaded_pair(request, s1, s2)
    return await run_in_threadpool(predict_result, pair, predictor(), started)


async def uploaded_triplet(request, s1, s2, ground_truth):
    try:
        form = await request.form()
        fields = ("s1", "s2", "ground_truth")
        if len(form.multi_items()) != 3 or any(len(form.getlist(field)) != 1 for field in fields):
            raise InputError("Upload exactly one S1, one S2 and one ground-truth TIFF from the same folder.")
        service = predictor()
        a, b, label = [await upload.read(MAX_FILE_BYTES + 1) for upload in (s1, s2, ground_truth)]
        pair = await run_in_threadpool(read_pair, a, b, s1.filename or "", s2.filename or "", service.statistics)
        reference = await run_in_threadpool(read_reference, label, ground_truth.filename or "", pair)
        return pair, reference
    finally:
        for upload in (s1, s2, ground_truth):
            await upload.close()


@app.post("/api/hand-test/preview")
async def hand_test_preview(request: Request, s1: UploadFile = File(...), s2: UploadFile = File(...),
                            ground_truth: UploadFile = File(...)):
    pair, reference = await uploaded_triplet(request, s1, s2, ground_truth)
    rgb, radar = await run_in_threadpool(previews, pair)
    _, separation = await run_in_threadpool(load_reference, pair, ROOT)
    return {"tile_id": pair.tile_id, "width": 512, "height": 512, "rgb": png_url(rgb),
            "radar": png_url(radar), "water_separation": separation, **comparison_images(reference)}


@app.post("/api/hand-test/predict")
async def hand_test_predict(request: Request, s1: UploadFile = File(...), s2: UploadFile = File(...),
                            ground_truth: UploadFile = File(...)):
    started = time.perf_counter()
    pair, reference = await uploaded_triplet(request, s1, s2, ground_truth)
    return await run_in_threadpool(predict_result, pair, predictor(), started, reference)


@lru_cache(maxsize=1)
def sample_manifest():
    return json.loads((ROOT / "sample/manifest.json").read_text())


def sample_record(sample_id):
    item = next((s for s in sample_manifest() if s["id"] == sample_id), None)
    if item is None:
        raise HTTPException(404, "Sample not found.")
    return item


@app.get("/api/samples")
def samples():
    return [{**s, "thumbnail_url": f"/api/samples/{s['id']}/thumbnail", "download_url": f"/api/samples/{s['id']}/download"}
            for s in sample_manifest()]


@lru_cache(maxsize=15)
def thumbnail_bytes(sample_id):
    item = sample_record(sample_id)
    folder = ROOT / "sample" / item["folder"]
    pair = read_pair((folder / item["s1"]).read_bytes(), (folder / item["s2"]).read_bytes(),
                     item["s1"], item["s2"], predictor().statistics)
    return png_bytes(previews(pair)[0], size=256)


@app.get("/api/samples/{sample_id}/thumbnail")
def thumbnail(sample_id: int):
    return Response(thumbnail_bytes(sample_id), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/samples/{sample_id}/download")
def download_sample(sample_id: int):
    item = sample_record(sample_id)
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_STORED) as archive:
        for field in ("s1", "s2"):
            archive.write(ROOT / "sample" / item["folder"] / item[field], arcname=f"{item['folder']}/{item[field]}")
    return Response(stream.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="bolivia-{sample_id}.zip"'})
