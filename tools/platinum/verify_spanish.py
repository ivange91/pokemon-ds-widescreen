#!/usr/bin/env python3
"""Verify CPUS's layout addresses against private English and Spanish revision-0 ROMs.

Usage: python tools/platinum/verify_spanish.py english.nds spanish.nds
Only names and addresses are printed; no ROM bytes are written or distributed.
"""
import argparse
import hashlib
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from ndsrom import read_rom
sys.path.insert(0, str(ROOT / 'tools' / 'soulsilver'))
from match_heartgold import mask_thumb


def normalise(data):
    words = mask_thumb(data)
    return struct.pack('<' + 'H' * len(words), *words)


def occurrences(data, pattern):
    result = []
    offset = data.find(pattern)
    while offset >= 0:
        if offset % 2 == 0:
            result.append(offset)
        offset = data.find(pattern, offset + 1)
    return result


def table(code):
    result = {}
    for line in (ROOT / 'tools' / 'platinum' / (code + '.txt')).read_text().splitlines():
        address, isa, module, first, name = line.split()
        result[name] = (int(address, 16), isa, module, first)
    return result


def load(path, code, digest):
    raw = path.read_bytes()
    if raw[12:16] != code.encode() or raw[0x1E] != 0:
        raise ValueError(f'{path}: expected {code}, revision 0')
    if hashlib.sha1(raw).hexdigest() != digest:
        raise ValueError(f'{path}: this verifier expects the documented unmodified dump')
    main, overlays = read_rom(path)
    return {'main': (struct.unpack_from('<I', raw, 0x28)[0], main),
            **{'ov' + str(k): v for k, v in overlays.items()}}


def branch_target(data, offset, base):
    high, low = struct.unpack_from('<HH', data, offset)
    if high & 0xF800 != 0xF000 or low & 0xF800 != 0xF800:
        raise ValueError('Expected a Thumb BL at the matched call site')
    delta = ((high & 0x7FF) << 12) | ((low & 0x7FF) << 1)
    if delta & (1 << 22):
        delta -= 1 << 23
    return base + offset + 4 + delta


def verify(english, spanish):
    en = load(english, 'CPUE', 'c5072bf51a5ecc51ade99d3506c023f5bac3eeb3')
    es = load(spanish, 'CPUS', 'd30289ddffc5a5f91cdf72dc26fb66c8e9f17c4e')
    source, target = table('CPUE'), table('CPUS')
    header = (ROOT / 'frontend' / 'platinum.h').read_text()
    watched = set(re.findall(r'find\("([^"]+)"\)', header))
    watched.update(re.findall(r'"(BattleSubscreen_[^"]+|ov5_[0-9A-Fa-f]+)"', header))
    if set(target) != watched:
        raise ValueError('CPUS table must cover exactly the functions watched by PtFuncs')
    special = {'SaveData_CardSave_Main', 'BattleSubscreen_DrawGiveUpMoveMenu',
               'BattleSubscreen_DrawUseNextMonMenu'}
    cache = {}
    for name in sorted(watched - special):
        addr, isa, module, _ = source[name]
        dest, kind, dest_module, first = target[name]
        assert isa == kind == 't' and module == dest_module
        assert first == ('-' if module == 'main' else '?')
        eb, ed = en[module]
        sb, sd = es[module]
        if module not in cache:
            cache[module] = normalise(ed), normalise(sd)
        a, b = cache[module]
        offset = addr - eb
        matched = False
        for size in (128, 96, 64, 48, 32):
            pattern = a[offset:offset + size]
            if len(pattern) == size and occurrences(a, pattern) == [offset] and occurrences(b, pattern) == [dest - sb]:
                matched = True
                break
        assert matched, f'{name}: no unique instruction signature at the configured address'

    # The save routine differs internally. Four independently matched callers all
    # branch to the Spanish entry, rather than assuming a shift from a neighbour.
    eb, ed = en['main']
    sb, sd = es['main']
    a, b = normalise(ed), normalise(sd)
    for call in (0x02024F98, 0x02024FE2, 0x0202503A, 0x02025AB0):
        offset = call - eb
        pattern = a[offset - 32:offset + 36]
        assert occurrences(a, pattern) == [offset - 32]
        found = occurrences(b, pattern)
        assert len(found) == 1
        assert branch_target(ed, offset, eb) == source['SaveData_CardSave_Main'][0]
        assert branch_target(sd, found[0] + 32, sb) == target['SaveData_CardSave_Main'][0]

    # Two identical menu bodies cannot be distinguished by their instructions.
    # Their separate entries in the battle callback table retain their order;
    # surrounding callback pointers move by the same amount and data stays equal.
    eb, ed = en['ov16']
    sb, sd = es['ov16']
    for name, pointer in (('BattleSubscreen_DrawGiveUpMoveMenu', 0x02270968),
                          ('BattleSubscreen_DrawUseNextMonMenu', 0x02270998)):
        other = pointer + 0x308
        assert struct.unpack_from('<I', ed, pointer - eb)[0] == source[name][0] | 1
        assert struct.unpack_from('<I', sd, other - sb)[0] == target[name][0] | 1
        for delta in range(-12, 16, 4):
            left = struct.unpack_from('<I', ed, pointer - eb + delta)[0]
            right = struct.unpack_from('<I', sd, other - sb + delta)[0]
            assert right == (left + 0x308 if 0x02200000 <= left < 0x02300000 else left)
    print(f'PASS: {len(watched)} layout functions: 46 unique signatures, save entry via four callers, two callback-table entries.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('english', type=Path)
    parser.add_argument('spanish', type=Path)
    args = parser.parse_args()
    verify(args.english, args.spanish)
