import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import axios from 'axios';
import { errorMessage, pairFromFolder, tripletFromFolder } from './files.js';

const api = axios.create({ baseURL: '/api', timeout: 120000 });
const labels = { rgb: 'Optical', radar: 'Radar', mask: 'Mask', overlay: 'Overlay' };
const formatPercent = value => `${(value * 100).toFixed(2)}%`;
const formatMetric = value => value == null ? 'N/A' : formatPercent(value);
const modes = { segmentation: 'Segmentation', 'hand-test': 'Hand Test' };

function saveUrl(url, filename) {
  let objectUrl;
  if (url.startsWith('data:')) {
    const [header, content] = url.split(',', 2);
    const bytes = Uint8Array.from(atob(content), char => char.charCodeAt(0));
    objectUrl = URL.createObjectURL(new Blob([bytes], { type: header.slice(5).split(';')[0] }));
  }
  const link = document.createElement('a');
  link.href = objectUrl || url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  if (objectUrl) setTimeout(() => URL.revokeObjectURL(objectUrl), 10000);
}

function geotiffDownload(base64, name) {
  const bytes = Uint8Array.from(atob(base64), char => char.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([bytes], { type: 'image/tiff' }));
  saveUrl(url, name);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('Cannot prepare the overlay download. Please retry.'));
    image.src = url;
  });
}

function Spinner() { return <span className="spinner" aria-hidden="true" />; }

export default function App() {
  const [info, setInfo] = useState(null);
  const [serviceError, setServiceError] = useState('');
  const [mode, setMode] = useState('segmentation');
  const [busyModes, setBusyModes] = useState({});
  const reportBusy = useCallback((key, value) => setBusyModes(current => ({ ...current, [key]: value })), []);
  const busy = Object.values(busyModes).some(Boolean);

  async function refreshService() {
    setServiceError('');
    try { setInfo((await api.get('/model-info')).data); }
    catch (err) { setInfo(null); setServiceError(errorMessage(err)); }
  }
  useEffect(() => { refreshService(); }, []);

  function navigateTabs(event) {
    const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
    if (busy || !keys.includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 'segmentation' : event.key === 'End' ? 'hand-test' : mode === 'segmentation' ? 'hand-test' : 'segmentation';
    setMode(next);
    document.getElementById(`tab-${next}`)?.focus();
  }

  return <>
    <a className="skip-link" href="#workspace">Skip to workspace</a>
    <header className="site-header"><h1>Flood Segmentation</h1><span className="device-label">{info ? `D4 · ${info.device.toUpperCase()}` : serviceError ? 'Service offline' : 'Connecting…'}</span></header>
    <main id="workspace" tabIndex={-1}>
      <div className="mode-tabs view-tabs" role="tablist" aria-label="Workspace" onKeyDown={navigateTabs}>{Object.entries(modes).map(([key, label]) => <button key={key} id={`tab-${key}`} type="button" role="tab" aria-selected={mode === key} aria-controls={`panel-${key}`} tabIndex={mode === key ? 0 : -1} disabled={busy} className={`view-tab ${mode === key ? 'active' : ''}`} onClick={() => setMode(key)}>{label}</button>)}</div>
      {Object.keys(modes).map(key => <div key={key} id={`panel-${key}`} role="tabpanel" aria-labelledby={`tab-${key}`} hidden={mode !== key}><Workspace mode={key} info={info} serviceError={serviceError} refreshService={refreshService} onBusyChange={reportBusy} /></div>)}
    </main>
  </>;
}

function Workspace({ mode, info, serviceError, refreshService, onBusyChange }) {
  const handTest = mode === 'hand-test';
  const defaultView = handTest ? 'compare' : 'rgb';
  const viewLabels = handTest ? { compare: 'Compare', ...labels } : labels;
  const endpoint = handTest ? '/hand-test' : '';
  const [pair, setPair] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [phase, setPhase] = useState('empty');
  const [error, setError] = useState('');
  const [view, setView] = useState(defaultView);
  const [opacity, setOpacity] = useState(50);
  const [exporting, setExporting] = useState(false);
  const fileInput = useRef(null);
  const controller = useRef(null);
  const generation = useRef(0);
  const resultHeading = useRef(null);
  const busy = phase === 'validating' || phase === 'processing';

  useLayoutEffect(() => { onBusyChange(mode, busy); }, [busy, mode, onBusyChange]);
  useEffect(() => () => controller.current?.abort(), []);

  function formData(selected) {
    const form = new FormData();
    form.append('s1', selected.s1, selected.s1.name);
    form.append('s2', selected.s2, selected.s2.name);
    if (handTest) form.append('ground_truth', selected.groundTruth, selected.groundTruth.name);
    return form;
  }

  async function chooseFolder(event) {
    const files = event.target.files;
    if (!files?.length) return;
    controller.current?.abort();
    const version = ++generation.current;
    setPair(null); setPreview(null); setResult(null); setError(''); setView(defaultView); setOpacity(50);
    try {
      const selected = handTest ? tripletFromFolder(files) : pairFromFolder(files);
      setPair(selected); setPhase('validating');
      controller.current = new AbortController();
      const response = await api.post(`${endpoint}/preview`, formData(selected), { signal: controller.current.signal });
      if (version !== generation.current) return;
      setPreview(response.data); setPhase('ready');
    } catch (err) {
      if (version !== generation.current || axios.isCancel(err)) return;
      setPhase('error'); setError(errorMessage(err));
    } finally { event.target.value = ''; }
  }

  async function segment() {
    if (!pair || busy) return;
    controller.current?.abort();
    controller.current = new AbortController();
    const version = generation.current;
    setError(''); setResult(null); setPhase('processing');
    try {
      const response = await api.post(`${endpoint}/predict`, formData(pair), { signal: controller.current.signal });
      if (version !== generation.current) return;
      setResult(response.data); setView(handTest ? 'compare' : 'overlay'); setPhase('success');
      requestAnimationFrame(() => resultHeading.current?.focus({ preventScroll: true }));
    } catch (err) {
      if (version !== generation.current || axios.isCancel(err)) return;
      setPhase('error'); setError(errorMessage(err));
    }
  }

  function clearPair() {
    controller.current?.abort(); ++generation.current;
    setPair(null); setPreview(null); setResult(null); setError(''); setPhase('empty'); setView(defaultView); setOpacity(50);
  }

  async function downloadOverlay() {
    setExporting(true);
    try {
      const [base, layer] = await Promise.all([loadImage(result.images.rgb), loadImage(result.images.overlay_layer)]);
      const canvas = document.createElement('canvas');
      canvas.width = result.width; canvas.height = result.height;
      const context = canvas.getContext('2d');
      context.drawImage(base, 0, 0); context.globalAlpha = opacity / 100; context.drawImage(layer, 0, 0);
      saveUrl(canvas.toDataURL('image/png'), `${result.tile_id}_overlay_${opacity}.png`);
    } catch (err) { setError(err.message); }
    finally { setExporting(false); }
  }

  const source = result?.images || preview;
  const status = { empty: 'No folder selected.', validating: 'Validating images…', ready: 'Ready to segment.', processing: 'Segmenting…', success: 'Segmentation complete.', error: 'Check the selected files.' }[phase];

  return <>
      <div className="workspace-grid">
        <div className="sidebar">
          <aside className="hud-panel upload-panel" aria-labelledby={`${mode}-upload-title`}>
            <h2 id={`${mode}-upload-title`}>Upload images</h2>
            <p className="instruction">{handTest ? 'Select a folder containing matching Sentinel-1, Sentinel-2 and ground-truth GeoTIFFs.' : 'Select a folder containing matching Sentinel-1 and Sentinel-2 GeoTIFFs.'}</p>
            {serviceError && <div className="error-notice" role="alert"><p>{serviceError}</p><button className="button secondary" onClick={refreshService}>Retry connection</button></div>}
            <input ref={fileInput} id={`${mode}-folder-input`} className="file-input" type="file" webkitdirectory="" directory="" multiple onChange={chooseFolder} aria-label={handTest ? 'Choose a folder containing matching Sentinel-1, Sentinel-2 and ground truth' : 'Choose a folder containing matching Sentinel-1 and Sentinel-2 TIFFs'} tabIndex={-1} />
            <button className="button choose-button" onClick={() => fileInput.current.click()} disabled={busy}>{pair ? 'Choose another folder' : 'Choose a folder'}<span aria-hidden="true">+</span></button>
            <p className="input-hint">512 × 512 GeoTIFFs · Up to 16 MiB each</p>

            {pair && <div className="pair-details"><strong>{pair.folder}</strong><span className="filename">{pair.s1.name}</span><span className="filename">{pair.s2.name}</span>{handTest && <span className="filename">{pair.groundTruth.name}</span>}</div>}
            <p className={`status-line ${phase === 'success' ? 'success-text' : ''}`} role="status" aria-live="polite">{busy && <Spinner />}{status}</p>
            {error && <div className="inline-error" role="alert">{error}</div>}
            <button className="button primary segment-button" disabled={!preview || busy || !info} onClick={segment}>{phase === 'processing' ? 'Segmenting…' : result ? 'Segment again' : 'Segment image'}</button>
            {pair && <button className="text-button clear-button" onClick={clearPair} disabled={busy} aria-label="Clear selected images">Clear</button>}
          </aside>

          <section className="hud-panel performance-panel" aria-labelledby={`${mode}-performance-title`}>
            <h2 id={`${mode}-performance-title`}>Model performance</h2>
            <p className="model-name">D4 · DeepLabV3+ / MobileNetV2</p>
            {info ? <table><caption className="sr-only">Historical D4 centre-crop IoU and Dice scores</caption><thead><tr><th scope="col">Dataset</th><th scope="col">IoU</th><th scope="col">Dice</th></tr></thead><tbody>{info.metrics.map(metric => <tr key={metric.dataset}><th scope="row">{metric.dataset}</th><td>{formatPercent(metric.iou)}</td><td>{formatPercent(metric.dice)}</td></tr>)}</tbody></table> : <p className="metrics-status">{serviceError ? 'Model metrics unavailable.' : 'Loading metrics…'}</p>}
            <p className="accuracy-note">Historical 256 × 256 centre-crop scores, not whole-image accuracy. Water predictions can include permanent water.</p>
            <div className="compute-section" aria-labelledby={`${mode}-compute-title`}>
              <h3 id={`${mode}-compute-title`}>Computational performance</h3>
              <dl className="compute-metrics">
                <div><dt>Parameters</dt><dd>{info ? info.parameter_count.toLocaleString('en-US') : 'Unavailable'}</dd></div>
                <div><dt>Device</dt><dd>{info ? info.device.toUpperCase() : 'Unavailable'}</dd></div>
                <div><dt>Inference</dt><dd>{result ? `${result.inference_ms.toFixed(1)} ms` : 'Awaiting run'}</dd></div>
                <div><dt>Processing</dt><dd>{result ? `${result.processing_ms.toFixed(1)} ms` : 'Awaiting run'}</dd></div>
              </dl>
              <p className="compute-note">{result ? `${result.width} × ${result.height} px · ${result.patch_count} patches. ` : 'Per 512 × 512 image, four patches. '}Inference measures the model step; processing includes server preparation and export. Network time is excluded.</p>
            </div>
          </section>
        </div>

          <section className="hud-panel results-panel" aria-labelledby={`${mode}-viewer-title`} aria-busy={busy}>
            <div className="viewer-heading"><h2 id={`${mode}-viewer-title`} ref={resultHeading} tabIndex={-1}>Results</h2>{preview && <span className="image-size">{preview.width} × {preview.height} px</span>}</div>
            {pair && <p className="tile-name">{pair.tileId}</p>}
            <div className={`view-tabs ${handTest ? 'hand-view-tabs' : ''}`} role="group" aria-label="Image view">{Object.entries(viewLabels).map(([key, label]) => <button key={key} className={view === key ? 'view-tab active' : 'view-tab'} aria-pressed={view === key} disabled={!source || (!result && (key === 'mask' || key === 'overlay'))} onClick={() => setView(key)}>{label}</button>)}</div>
            <div className="viewer-body">
            {source && view === 'compare' ? <div className="comparison-grid">
              <figure><figcaption>Ground truth</figcaption><div className="image-stage"><img className="comparison-image" src={source.ground_truth} alt={`Ground truth for ${pair.tileId}`} width="512" height="512" /></div></figure>
              <figure><figcaption>D4 prediction</figcaption><div className={`image-stage ${!result ? 'empty-stage' : ''}`}>{result ? <img className="comparison-image" src={source.comparison_prediction} alt={`D4 prediction for ${pair.tileId}`} width="512" height="512" /> : <p className="empty-copy">Click Segment image to show the prediction.</p>}</div></figure>
            </div> : <div className={`image-stage ${!source ? 'empty-stage' : ''}`}>
              {source ? <>
                <img className="main-image" src={view === 'overlay' ? source.rgb : source[view]} alt={`${labels[view]} view of ${pair.tileId}`} width="512" height="512" />
                {view === 'overlay' && <img className="overlay-image" src={source.overlay_layer} style={{ opacity: opacity / 100 }} alt="" aria-hidden="true" width="512" height="512" />}
              </> : <p className="empty-copy">{handTest ? 'Upload a satellite triplet to preview.' : 'Upload a satellite pair to preview.'}</p>}
            </div>}
            {busy && <div className="processing-cover"><Spinner /><span>{phase === 'validating' ? 'Preparing preview…' : 'Processing image…'}</span></div>}
            </div>
            {source && <div className="viewer-caption"><span>{view === 'compare' ? 'White: water · Black: background · Grey: excluded' : view === 'rgb' ? 'Sentinel-2 · RGB' : view === 'radar' ? 'Sentinel-1 · VV radar' : view === 'mask' ? 'White: water · Black: background · Grey: no data' : 'Blue: predicted water'}</span>{result && <span>{result.inference_ms.toFixed(0)} ms · {result.device.toUpperCase()}</span>}</div>}
            {result?.evaluation && <section className="evaluation-panel" aria-label="Full-image comparison against uploaded ground truth"><h3>Full-image comparison against uploaded ground truth</h3><dl className="evaluation-metrics">{[['Water IoU', 'iou'], ['Dice', 'dice'], ['Pixel accuracy', 'pixel_accuracy']].map(([label, key]) => <div key={key}><dt>{label}</dt><dd>{formatMetric(result.evaluation[key])}</dd></div>)}</dl><p>{result.evaluation.evaluated_pixels.toLocaleString('en-US')} evaluated pixels · {result.evaluation.excluded_pixels.toLocaleString('en-US')} excluded</p></section>}
            {result && view === 'overlay' && <div className="opacity-control"><label htmlFor={`${mode}-opacity`}>Overlay opacity</label><input id={`${mode}-opacity`} type="range" min="0" max="100" value={opacity} onChange={e => setOpacity(Number(e.target.value))} /><output htmlFor={`${mode}-opacity`}>{opacity}%</output></div>}
            {result && <div className="download-actions" aria-label="Download results"><button className="button secondary" onClick={() => saveUrl(result.images.mask, `${result.tile_id}_mask.png`)}>Mask PNG</button><button className="button secondary" disabled={exporting} onClick={downloadOverlay}>{exporting ? 'Preparing…' : 'Overlay PNG'}</button><button className="button secondary" onClick={() => geotiffDownload(result.mask_geotiff_base64, `${result.tile_id}_mask.tif`)}>Mask GeoTIFF</button></div>}
          </section>
      </div>
  </>;
}
