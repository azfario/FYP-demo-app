import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { errorMessage, pairFromFolder } from './files.js';

const api = axios.create({ baseURL: '/api', timeout: 120000 });
const labels = { rgb: 'Optical', radar: 'Radar', mask: 'Mask', overlay: 'Overlay' };
const formatPercent = value => `${(value * 100).toFixed(2)}%`;

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
  const [pair, setPair] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [phase, setPhase] = useState('empty');
  const [error, setError] = useState('');
  const [view, setView] = useState('rgb');
  const [opacity, setOpacity] = useState(50);
  const [exporting, setExporting] = useState(false);
  const fileInput = useRef(null);
  const controller = useRef(null);
  const generation = useRef(0);
  const resultHeading = useRef(null);
  const busy = phase === 'validating' || phase === 'processing';

  async function refreshService() {
    setServiceError('');
    try {
      const response = await api.get('/model-info');
      setInfo(response.data);
    } catch (err) {
      setInfo(null);
      setServiceError(errorMessage(err));
    }
  }

  useEffect(() => {
    refreshService();
    return () => controller.current?.abort();
  }, []);

  function formData(selected) {
    const form = new FormData();
    form.append('s1', selected.s1, selected.s1.name);
    form.append('s2', selected.s2, selected.s2.name);
    return form;
  }

  async function chooseFolder(event) {
    const files = event.target.files;
    if (!files?.length) return;
    controller.current?.abort();
    const version = ++generation.current;
    setPair(null); setPreview(null); setResult(null); setError(''); setView('rgb'); setOpacity(50);
    try {
      const selected = pairFromFolder(files);
      setPair(selected); setPhase('validating');
      controller.current = new AbortController();
      const response = await api.post('/preview', formData(selected), { signal: controller.current.signal });
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
      const response = await api.post('/predict', formData(pair), { signal: controller.current.signal });
      if (version !== generation.current) return;
      setResult(response.data); setView('overlay'); setPhase('success');
      requestAnimationFrame(() => resultHeading.current?.focus({ preventScroll: true }));
    } catch (err) {
      if (version !== generation.current || axios.isCancel(err)) return;
      setPhase('error'); setError(errorMessage(err));
    }
  }

  function clearPair() {
    controller.current?.abort(); ++generation.current;
    setPair(null); setPreview(null); setResult(null); setError(''); setPhase('empty'); setView('rgb');
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
    <a className="skip-link" href="#workspace">Skip to workspace</a>
    <header className="site-header">
      <h1>Flood Segmentation</h1>
      <span className="device-label">{info ? `D4 · ${info.device.toUpperCase()}` : serviceError ? 'Service offline' : 'Connecting…'}</span>
    </header>

    <main id="workspace" tabIndex={-1}>
      <div className="workspace-grid">
        <div className="sidebar">
          <aside className="hud-panel upload-panel" aria-labelledby="upload-title">
            <h2 id="upload-title">Upload images</h2>
            <p className="instruction">Select a folder containing matching Sentinel-1 and Sentinel-2 GeoTIFFs.</p>
            {serviceError && <div className="error-notice" role="alert"><p>{serviceError}</p><button className="button secondary" onClick={refreshService}>Retry connection</button></div>}
            <input ref={fileInput} id="folder-input" className="file-input" type="file" webkitdirectory="" directory="" multiple onChange={chooseFolder} aria-label="Choose a folder containing matching Sentinel-1 and Sentinel-2 TIFFs" tabIndex={-1} />
            <button className="button choose-button" onClick={() => fileInput.current.click()} disabled={busy}>{pair ? 'Choose another folder' : 'Choose a folder'}<span aria-hidden="true">+</span></button>
            <p className="input-hint">512 × 512 GeoTIFFs · Up to 16 MiB each</p>

            {pair && <div className="pair-details"><strong>{pair.folder}</strong><span className="filename">{pair.s1.name}</span><span className="filename">{pair.s2.name}</span></div>}
            <p className={`status-line ${phase === 'success' ? 'success-text' : ''}`} role="status" aria-live="polite">{busy && <Spinner />}{status}</p>
            {error && <div className="inline-error" role="alert">{error}</div>}
            <button className="button primary segment-button" disabled={!preview || busy || !info} onClick={segment}>{phase === 'processing' ? 'Segmenting…' : result ? 'Segment again' : 'Segment image'}</button>
            {pair && <button className="text-button clear-button" onClick={clearPair} disabled={busy} aria-label="Clear selected images">Clear</button>}
          </aside>

          <section className="hud-panel performance-panel" aria-labelledby="performance-title">
            <h2 id="performance-title">Model performance</h2>
            <p className="model-name">D4 · DeepLabV3+ / MobileNetV2</p>
            {info ? <table><caption className="sr-only">Historical D4 centre-crop IoU and Dice scores</caption><thead><tr><th scope="col">Dataset</th><th scope="col">IoU</th><th scope="col">Dice</th></tr></thead><tbody>{info.metrics.map(metric => <tr key={metric.dataset}><th scope="row">{metric.dataset}</th><td>{formatPercent(metric.iou)}</td><td>{formatPercent(metric.dice)}</td></tr>)}</tbody></table> : <p className="metrics-status">{serviceError ? 'Model metrics unavailable.' : 'Loading metrics…'}</p>}
            <p className="accuracy-note">Historical 256 × 256 centre-crop scores, not whole-image accuracy. Water predictions can include permanent water.</p>
            <div className="compute-section" aria-labelledby="compute-title">
              <h3 id="compute-title">Computational performance</h3>
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

          <section className="hud-panel results-panel" aria-labelledby="viewer-title" aria-busy={busy}>
            <div className="viewer-heading"><h2 id="viewer-title" ref={resultHeading} tabIndex={-1}>Results</h2>{preview && <span className="image-size">{preview.width} × {preview.height} px</span>}</div>
            {pair && <p className="tile-name">{pair.tileId}</p>}
            <div className="view-tabs" role="group" aria-label="Image view">{Object.entries(labels).map(([key, label]) => <button key={key} className={view === key ? 'view-tab active' : 'view-tab'} aria-pressed={view === key} disabled={!source || (!result && (key === 'mask' || key === 'overlay'))} onClick={() => setView(key)}>{label}</button>)}</div>
            <div className={`image-stage ${!source ? 'empty-stage' : ''}`}>
              {source ? <>
                <img className="main-image" src={view === 'overlay' ? source.rgb : source[view]} alt={`${labels[view]} view of ${pair.tileId}`} width="512" height="512" />
                {view === 'overlay' && <img className="overlay-image" src={source.overlay_layer} style={{ opacity: opacity / 100 }} alt="" aria-hidden="true" width="512" height="512" />}
              </> : <p className="empty-copy">Upload a satellite pair to preview.</p>}
              {busy && <div className="processing-cover"><Spinner /><span>{phase === 'validating' ? 'Preparing preview…' : 'Processing image…'}</span></div>}
            </div>
            {source && <div className="viewer-caption"><span>{view === 'rgb' ? 'Sentinel-2 · RGB' : view === 'radar' ? 'Sentinel-1 · VV radar' : view === 'mask' ? 'White: water · Black: background · Grey: no data' : 'Blue: predicted water'}</span>{result && <span>{result.inference_ms.toFixed(0)} ms · {result.device.toUpperCase()}</span>}</div>}
            {result && view === 'overlay' && <div className="opacity-control"><label htmlFor="opacity">Overlay opacity</label><input id="opacity" type="range" min="0" max="100" value={opacity} onChange={e => setOpacity(Number(e.target.value))} /><output htmlFor="opacity">{opacity}%</output></div>}
            {result && <div className="download-actions" aria-label="Download results"><button className="button secondary" onClick={() => saveUrl(result.images.mask, `${result.tile_id}_mask.png`)}>Mask PNG</button><button className="button secondary" disabled={exporting} onClick={downloadOverlay}>{exporting ? 'Preparing…' : 'Overlay PNG'}</button><button className="button secondary" onClick={() => geotiffDownload(result.mask_geotiff_base64, `${result.tile_id}_mask.tif`)}>Mask GeoTIFF</button></div>}
          </section>
      </div>
    </main>
  </>;
}
