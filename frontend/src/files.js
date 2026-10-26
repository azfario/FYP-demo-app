export function pairFromFolder(fileList) {
  const files = Array.from(fileList).filter(file => !/^(\.DS_Store|Thumbs\.db|desktop\.ini|\._.*)$/i.test(file.name));
  if (files.length !== 2) throw new Error('Select one folder containing exactly two TIFFs: matching Sentinel-1 and Sentinel-2 images. Do not select a parent folder containing several pairs.');
  const s1 = files.find(file => /_S1Hand\.tiff?$/i.test(file.name));
  const s2 = files.find(file => /_S2Hand\.tiff?$/i.test(file.name));
  if (!s1 || !s2) throw new Error('This folder needs one _S1Hand.tif and one _S2Hand.tif file from Sen1Floods11.');
  const tile = file => file.name.replace(/_S[12]Hand\.tiff?$/i, '');
  if (tile(s1) !== tile(s2)) throw new Error('These images belong to different tiles. Choose matching S1 and S2 filenames.');
  if (files.some(file => file.size > 16 * 1024 * 1024)) throw new Error('Each TIFF must be 16 MiB or smaller.');
  if (files.some(file => file.size === 0)) throw new Error('A TIFF is empty. Replace it with the original dataset file.');
  const directories = files.map(file => (file.webkitRelativePath || file.name).split('/').slice(0, -1).join('/'));
  if (directories[0] !== directories[1]) throw new Error('Both TIFFs must be inside the same tile folder.');
  return { s1, s2, tileId: tile(s1), folder: directories[0].split('/').pop() || tile(s1) };
}

export function errorMessage(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return 'Both S1 and S2 TIFF files are required. Choose the tile folder again.';
  if (error.code === 'ERR_NETWORK' || [502, 503, 504].includes(error.response?.status)) return 'The inference service is unavailable. Check that the backend container is running, then retry.';
  return error.message || 'Something went wrong. Please retry.';
}
