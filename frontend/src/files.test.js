import { describe, expect, it } from 'vitest';
import { pairFromFolder, errorMessage } from './files.js';

const image = (sensor, tile = 'Bolivia_103757', extra = {}) => ({ name: `${tile}_${sensor}Hand.tif`, size: 3000, webkitRelativePath: `bolivia 1/${tile}_${sensor}Hand.tif`, ...extra });
describe('folder upload boundary', () => {
  it('identifies a pair regardless of directory listing order', () => {
    const result = pairFromFolder([image('S2'), image('S1')]);
    expect(result.tileId).toBe('Bolivia_103757');
    expect(result.folder).toBe('bolivia 1');
    expect(result.s1.name).toContain('S1Hand');
  });
  it('ignores operating system metadata', () => {
    expect(pairFromFolder([image('S1'), image('S2'), { name: '.DS_Store' }]).tileId).toBe('Bolivia_103757');
  });
  it('rejects the parent containing several pairs', () => {
    expect(() => pairFromFolder([image('S1'), image('S2'), image('S1', 'Bolivia_129334'), image('S2', 'Bolivia_129334')])).toThrow('parent');
  });
  it('rejects missing partners, unrelated files and mismatched tile IDs', () => {
    expect(() => pairFromFolder([image('S1')])).toThrow('two TIFFs');
    expect(() => pairFromFolder([image('S1'), { name: 'photo.png', size: 200 }])).toThrow('_S2Hand');
    expect(() => pairFromFolder([image('S1'), image('S2', 'Bolivia_129334')])).toThrow('different tiles');
  });
  it('rejects oversized or empty rasters', () => {
    expect(() => pairFromFolder([image('S1', undefined, { size: 17 * 1024 * 1024 }), image('S2')])).toThrow('16 MiB');
    expect(() => pairFromFolder([image('S1', undefined, { size: 0 }), image('S2')])).toThrow('empty');
  });
  it('rejects pairs in different subfolders', () => {
    expect(() => pairFromFolder([image('S1'), image('S2', undefined, { webkitRelativePath: 'other/file.tif' })])).toThrow('same tile folder');
  });
  it('shows API validation and service failures as useful messages', () => {
    expect(errorMessage({ response: { data: { detail: 'Wrong bands' } } })).toBe('Wrong bands');
    expect(errorMessage({ code: 'ERR_NETWORK' })).toContain('backend container');
  });
});
