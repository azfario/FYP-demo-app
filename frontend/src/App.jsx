import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { errorMessage, pairFromFolder } from './files.js';

const api = axios.create({ baseURL: '/api', timeout: 120000 });
const labels = { rgb: 'Optical', radar: 'Radar', mask: 'Mask', overlay: 'Overlay' };
const formatPercent = value => `${(value * 100).toFixed(2)}%`;

function saveUrl(url, filename) {
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
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
  const [samples, setSamples] = useState([]);
  const [sampleError, setSampleError] = useState('');
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

  async function refreshSamples() {
    setSampleError('');
    try { setSamples((await api.get('/samples')).data); }
    catch (err) { setSampleError(errorMessage(err)); }
  }

  useEffect(() => {
    refreshService(); refreshSamples();
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
  const status = { empty: 'Waiting for a satellite pair', validating: 'Checking bands and alignment…', ready: 'Pair checked. Ready to segment.', processing: 'Segmenting the full image…', success: 'Full-image segmentation complete', error: 'Your attention is needed' }[phase];

  return <>
    <a className="skip-link" href="#workspace">Skip to workspace</a>
    <header className="site-header">
      <a href="#workspace" className="wordmark">Flood segmentation<span>D4 research demo</span></a>
      <nav aria-label="Main navigation">
        <a href="#workspace">Workspace</a><a href="#samples">Samples</a><a href="#model">Model</a>
      </nav>
      <span className="device-label">{info ? `${info.device.toUpperCase()} available` : serviceError ? 'Service offline' : 'Connecting…'}</span>
    </header>

    <main>
      <section id="workspace" className="workspace-section scroll-mt-24" aria-labelledby="page-title">
        <div className="intro">
          <div><p className="eyeline">Sentinel-1 + Sentinel-2</p><h1 id="page-title">Two satellite views.<br />One flood map.</h1></div>
          <p className="intro-copy">Look at the landscape, then look closer. Upload a matching satellite pair to map predicted water across the full image.</p>
        </div>

        {serviceError && <div className="notice error-notice" role="alert"><p>{serviceError}</p><button className="button secondary" onClick={refreshService}>Reconnect to model</button></div>}

        <div className="workspace-grid">
          <aside className="upload-panel" aria-labelledby="upload-title">
            <div className="step-label">Your starting point</div>
            <h2 id="upload-title">Bring a satellite pair.</h2>
            <p className="muted">Choose a folder with two matching GeoTIFFs. One radar image. One optical image. The same place.</p>
            <div className="folder-example" aria-label="Example folder structure">
              <strong>bolivia 1 /</strong>
              <span>Bolivia_103757_S1Hand.tif</span>
              <span>Bolivia_103757_S2Hand.tif</span>
            </div>
            <input ref={fileInput} id="folder-input" className="file-input" type="file" webkitdirectory="" directory="" multiple onChange={chooseFolder} aria-label="Choose a folder containing matching Sentinel-1 and Sentinel-2 TIFFs" tabIndex={-1} />
            <button className="button choose-button" onClick={() => fileInput.current.click()} disabled={busy}>{pair ? 'Choose another folder' : 'Choose a folder'}<span aria-hidden="true">+</span></button>
            <p className="input-hint">512 × 512 GeoTIFFs · Up to 16 MiB each</p>

            {pair && <div className="pair-details"><strong>{pair.folder}</strong><div><span>Radar · 2 bands</span><span className="filename">{pair.s1.name}</span></div><div><span>Optical · 13 bands</span><span className="filename">{pair.s2.name}</span></div></div>}
            <p className={`status-line ${phase === 'success' ? 'success-text' : ''}`} role="status" aria-live="polite">{busy && <Spinner />}{status}</p>
            {error && <div className="inline-error" role="alert">{error}</div>}
            <button className="button primary segment-button" disabled={!preview || busy || !info} onClick={segment}>{phase === 'processing' ? 'Mapping water…' : result ? 'Run segmentation again' : 'Segment this image'}</button>
            {pair && <button className="text-button clear-button" onClick={clearPair} disabled={busy}>Clear this pair</button>}
            <div className="sample-hint"><p>Need an image to begin?</p><a href="#samples">Choose from 15 Bolivia samples</a><span>Download a pair, unzip it, then select its folder.</span></div>
          </aside>

          <section className="results-panel" aria-labelledby="viewer-title" aria-busy={busy}>
            <div className="viewer-heading"><div><p className="eyeline">The landscape</p><h2 id="viewer-title" ref={resultHeading} tabIndex={-1}>{pair ? pair.tileId.replace('_', ' / ') : 'Your image, in focus.'}</h2></div>{preview && <span className="image-size">512 × 512 px</span>}</div>
            <div className="view-tabs" role="group" aria-label="Image view">{Object.entries(labels).map(([key, label]) => <button key={key} className={view === key ? 'view-tab active' : 'view-tab'} aria-pressed={view === key} disabled={!source || (!result && (key === 'mask' || key === 'overlay'))} onClick={() => setView(key)}>{label}</button>)}</div>
            <div className={`image-stage ${!source ? 'empty-stage' : ''}`}>
              {source ? <>
                <img className="main-image" src={view === 'overlay' ? source.rgb : source[view]} alt={`${labels[view]} view of ${pair.tileId}`} width="512" height="512" />
                {view === 'overlay' && <img className="overlay-image" src={source.overlay_layer} style={{ opacity: opacity / 100 }} alt="" aria-hidden="true" width="512" height="512" />}
              </> : <div className="empty-copy"><span className="empty-number" aria-hidden="true">S1 + S2</span><h3>A place for the full picture.</h3><p>Your satellite preview will appear here once you choose a valid pair.</p><span>Original imagery, mask, and overlay in one workspace.</span></div>}
              {busy && <div className="processing-cover"><Spinner /><span>{phase === 'validating' ? 'Preparing your images' : 'Reading four patches'}</span></div>}
            </div>
            <div className="viewer-caption"><span>{view === 'rgb' ? 'Sentinel-2 · natural-colour preview' : view === 'radar' ? 'Sentinel-1 · VV radar preview' : view === 'mask' ? 'White: predicted water · Black: background · Grey: no data' : 'Blue: predicted water · Displayed over Sentinel-2'}</span><span>{result ? 'Full tile · 4 patches' : 'No prediction yet'}</span></div>
            {result && <div className="result-controls"><div className="opacity-control"><label htmlFor="opacity">Overlay opacity</label><input id="opacity" type="range" min="0" max="100" value={opacity} onChange={e => setOpacity(Number(e.target.value))} /><output htmlFor="opacity">{opacity}%</output></div><div className="timing"><span>Measured inference</span><strong>{result.inference_ms.toFixed(0)} ms <span>/ {result.device.toUpperCase()}</span></strong></div></div>}
            {result && <div className="download-actions" aria-label="Download results"><button className="button secondary" onClick={() => saveUrl(result.images.mask, `${result.tile_id}_mask.png`)}>Mask PNG</button><button className="button secondary" disabled={exporting} onClick={downloadOverlay}>{exporting ? 'Preparing…' : 'Overlay PNG'}</button><button className="button secondary" onClick={() => geotiffDownload(result.mask_geotiff_base64, `${result.tile_id}_mask.tif`)}>Mask GeoTIFF</button></div>}
            <p className="viewer-note">{result ? 'Predicted water is a flood indicator, not a distinction between floodwater and permanent water. Patch boundaries may affect the result.' : 'Previews use display-only contrast adjustments. D4 receives the original 15 bands with its saved preprocessing.'}</p>
          </section>
        </div>
      </section>

      <section id="samples" className="samples-section scroll-mt-24" aria-labelledby="samples-title">
        <div className="section-heading"><div><p className="eyeline">From Sen1Floods11</p><h2 id="samples-title">Start somewhere real.</h2></div><p>Fifteen views of Bolivia. Each download contains the matching radar and optical TIFFs in one folder.</p></div>
        {sampleError ? <div className="notice error-notice" role="alert"><p>{sampleError}</p><button className="button secondary" onClick={refreshSamples}>Reload samples</button></div> : samples.length ? <div className="sample-grid">{samples.map(sample => <a className="sample-card" key={sample.id} href={sample.download_url} download aria-label={`Download ${sample.folder}, ${sample.tile_id}, matching S1 and S2 TIFFs`}><img src={sample.thumbnail_url} width="256" height="256" loading="lazy" alt={`Sentinel-2 optical preview of ${sample.tile_id}`} onError={event => { event.currentTarget.style.visibility = 'hidden'; event.currentTarget.nextElementSibling.textContent = 'Preview unavailable'; }} /><span className="sample-label">Bolivia {sample.id}</span><span className="sample-download">Download pair <span aria-hidden="true">↓</span></span></a>)}</div> : <p role="status" className="muted">Loading sample images…</p>}
        <p className="sample-footnote">Bolivia is the model’s held-out test region. These samples are for demonstration, not a new independent evaluation.</p>
      </section>

      <section id="model" className="model-section scroll-mt-24" aria-labelledby="model-title"><div className="model-intro"><p className="eyeline">Behind the prediction</p><h2 id="model-title">A trained model.<br />An honest view of its results.</h2><p>DeepLabV3+ with a MobileNetV2 backbone. The D4 checkpoint is loaded as trained, with no retraining in this app.</p><a className="body-link" href="/docs" target="_blank" rel="noreferrer">Open API documentation</a></div><div className="model-facts">{info ? <><dl className="facts-grid"><div><dt>Checkpoint</dt><dd>D4 · seed {info.seed}</dd></div><div><dt>Parameters</dt><dd>{info.parameter_count.toLocaleString()}</dd></div><div><dt>Input</dt><dd>2 radar + 13 optical bands</dd></div><div><dt>Running on</dt><dd>{info.device.toUpperCase()}</dd></div></dl><div className="metrics-heading"><h3>Historical centre-crop evaluation</h3><p>256 × 256 pixels. These scores do not measure the full-image predictions shown above.</p></div><table><caption className="sr-only">Historical D4 seed 2026 centre-crop scores</caption><thead><tr><th scope="col">Dataset</th><th scope="col">IoU</th><th scope="col">Dice</th></tr></thead><tbody>{info.metrics.map(metric => <tr key={metric.dataset}><th scope="row">{metric.dataset}</th><td>{formatPercent(metric.iou)}</td><td>{formatPercent(metric.dice)}</td></tr>)}</tbody></table><p className="metric-source">Source: {info.source}</p></> : <p className="muted">{serviceError ? 'Model details will appear when the inference service is available.' : 'Loading model details…'}</p>}</div></section>
    </main>
    <footer><span>Flood segmentation · FYP research demo</span><a href="https://github.com/cloudtostreet/Sen1Floods11" target="_blank" rel="noreferrer">Imagery: Sen1Floods11</a><span>Runs locally. Uploaded images are not retained.</span></footer>
  </>;
}
