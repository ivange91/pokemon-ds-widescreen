#!/usr/bin/env python3
"""Verify the regional layout metadata using private ROMs (no game bytes are written).

    python tools/regions/verify.py --rom-dir test/regions
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools' / 'soulsilver')]
from ndsrom import read_rom
from recomp import autoload_image
from match_heartgold import mask_thumb, mask_arm


def normalise(data, isa):
    values = (mask_thumb if isa == 't' else mask_arm)(data)
    return struct.pack('<' + ('H' if isa == 't' else 'I') * len(values), *values)


def occurrences(data, pattern, step=2):
    result = []
    offset = data.find(pattern)
    while offset >= 0:
        if offset % step == 0:
            result.append(offset)
        offset = data.find(pattern, offset + 1)
    return result


def branch(data, offset, base, isa):
    if isa == 'a':
        word = struct.unpack_from('<I', data, offset)[0]
        assert word & 0x0F000000 == 0x0B000000
        delta = (word & 0xFFFFFF) << 2
        if delta & 0x2000000:
            delta -= 0x4000000
        return base + offset + 8 + delta
    high, low = struct.unpack_from('<HH', data, offset)
    assert high & 0xF800 == 0xF000 and low & 0xF800 == 0xF800
    delta = ((high & 2047) << 12) | ((low & 2047) << 1)
    if delta & 0x400000:
        delta -= 0x800000
    return base + offset + 4 + delta


def load(path):
    with path.open('rb') as f:
        header = f.read(64)
    main, overlays = read_rom(path)
    return {'main': (struct.unpack_from('<I', header, 0x28)[0], main),
            **{f'ov{i:03d}': v for i, v in overlays.items()}}


def verify_bw(paths):
    profiles = json.loads((ROOT / 'tools/regions/bw-profiles.json').read_text())
    for source, target in [('IRBO', 'IRBS'), ('IRAO', 'IRAS'), ('IREO', 'IRES'), ('IRDO', 'IRDS')]:
        en, es = load(paths[source]), load(paths[target])
        expected = []
        cache = {}

        def images(module, isa):
            if (module, isa) not in cache:
                cache[module, isa] = normalise(en[module][1], isa), normalise(es[module][1], isa)
            return cache[module, isa]

        for row in profiles[target]:
            module, isa = row['module'], row['isa']
            addr, dest = row['english'], row['spanish']
            eb, ed = en[module]
            sb, sd = es[module]
            a, b = images(module, isa)
            offset, new_offset = addr - eb, dest - sb
            step = 2 if isa == 't' else 4
            verified = False
            size = row['bytes']
            if size:
                pattern = a[offset:offset + size]
                verified = (occurrences(a, pattern, step) == [offset] and
                            occurrences(b, pattern, step) == [new_offset])
            for proof in row.get('arm_call_proof', []):
                assert proof['spanish_target'] == dest
                x, y = images(proof['module'], 'a')
                pb, pd = en[proof['module']]
                qb, qd = es[proof['module']]
                at, to = proof['english_call'] - pb, proof['spanish_call'] - qb
                pattern = x[at - 32:at + 36]
                if occurrences(x, pattern, 4) == [at - 32] and occurrences(y, pattern, 4) == [to - 32]:
                    assert branch(pd, at, pb, 'a') == addr and branch(qd, to, qb, 'a') == dest
                    verified = True
            for proof in row.get('evidence', []):
                if proof[0] == 'suffix' and proof[3] == dest:
                    _, skip, size, _ = proof
                    pattern = a[offset + skip:offset + skip + size]
                    if (occurrences(a, pattern, step) == [offset + skip] and
                            occurrences(b, pattern, step) == [new_offset + skip]):
                        # Identical short heap helpers are distinguished by the adjacent
                        # function sequence, in addition to their own entry instructions.
                        if row['name'] == 'GetFieldmapZoneHeapSize':
                            assert a[offset:offset + 16] == b[new_offset:new_offset + 16]
                        verified = True
                elif proof[0] == 'caller' and proof[1] == module and proof[3] == dest:
                    at = proof[2] - eb
                    x, y = images(module, 't')
                    pattern = x[at - 32:at + 36]
                    matches = occurrences(y, pattern)
                    if occurrences(x, pattern) == [at - 32] and len(matches) == 1:
                        assert branch(ed, at, eb, 't') == addr
                        assert branch(sd, matches[0] + 32, sb, 't') == dest
                        verified = True
            assert verified, (target, row['name'])
            expected.append(f"{dest:08x} {isa} {module} {'-' if module == 'main' else '?'} {row['name']}")
        actual = (ROOT / f'tools/regions/{target}.txt').read_text().splitlines()
        assert actual == expected
        print(f'{target}: {len(expected)} watched functions verified')


def verify_hgss(paths):
    layout = json.loads((ROOT / 'layouts/soulsilver-us.json').read_text())
    source = load(paths['IPGE'])
    for code, filename in [('IPKF', 'heartgold-es-fix'), ('IPGS', 'soulsilver-es')]:
        target = load(paths[code])
        profile = json.loads((ROOT / f'tools/soulsilver/{filename}.json').read_text())
        probes = json.loads((ROOT / f'tools/regions/{code}-probes.json').read_text())
        sections = {s['name']: s for s in layout['sections']}
        cache = {}
        for probe in probes:
            section = sections[probe['section']]
            key = section['source']
            if key == 'main':
                eb, ed = source['main']
                sb, sd = target['main']
            elif key == 'itcm':
                eb = sb = section['base']
                ed, sd = autoload_image(source['main'][1], eb), autoload_image(target['main'][1], sb)
            else:
                eb, ed = source[f'ov{key:03d}']
                sb, sd = target[f'ov{key:03d}']
            if key not in cache:
                cache[key] = normalise(ed, 't'), normalise(sd, 't')
            a, b = cache[key]
            offset, to = probe['english'] - eb, probe['target'] - sb
            pattern = a[offset:offset + probe['bytes']]
            assert occurrences(a, pattern) == [offset]
            assert occurrences(b, pattern) == [to]
            shifts = [delta for start, end, delta in profile['shifts'][probe['section']]
                      if start <= probe['english'] < end]
            assert shifts == [probe['target'] - probe['english']]
        print(f'{code}: all {len(probes)} application/focus probes verified')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom-dir', required=True, type=Path)
    args = parser.parse_args()
    known = json.loads((ROOT / 'tools/regions/verified-roms.json').read_text())
    by_hash = {r['sha1']: r['code'] for r in known}
    paths = {}
    for path in args.rom_dir.rglob('*.nds'):
        with path.open('rb') as file:
            digest = hashlib.file_digest(file, 'sha1').hexdigest()
        if digest in by_hash:
            paths[by_hash[digest]] = path
    missing = set(by_hash.values()) - paths.keys()
    if missing:
        parser.error('Missing verified ROMs: ' + ', '.join(sorted(missing)))
    verify_bw(paths)
    verify_hgss(paths)
    print('PASS: regional layout addresses verified against the private ROMs.')


if __name__ == '__main__':
    main()
