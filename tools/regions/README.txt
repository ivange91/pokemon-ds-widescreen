SPANISH REGIONAL LAYOUTS

Supports the supplied revision-0 IRBS, IRAS, IRES, IRDS and IPGS ROMs.
HeartGold is the exact Spanish FIX image identified by its SHA-1 in
verified-roms.json. Its IPKF header is misleading; unrelated French ROMs are
rejected. The previously supplied IPGJ SoulSilver FIX is not supported.
Spanish Platinum (CPUS) lives in tools/platinum/.

The tables and profiles contain addresses, lengths and hashes, not game code.
BW tables use English function names so the existing frontend can recognise
Spanish scenes. Match evidence is in bw-profiles.json: unique normalised
instruction signatures, with verified callers or neighbouring functions used
where short functions are otherwise ambiguous. The four map/heap addresses
in frontend/bw2map.h were checked against the respective ROMs.

HGSS uses the existing tables_only.py portable-profile mechanism and per-overlay
bases in frontend/hgss_regions.h. All 195 application/focus probes were matched
uniquely. Unresolved non-critical chunks are mapped outside watched RAM instead
of guessing their addresses. These tables are for interpreter/JIT builds, not
Spanish static recompilation. No CPU or instruction translation was changed.

Reproduce the checks with private ROMs:
    python tools/regions/verify.py --rom-dir YOUR_EXTRACTED_ROM_FOLDER
    python tools/platinum/verify_spanish.py --help
The verified-roms.json hashes identify the tested images. Hashes do not prove
that every revision or modified dump is compatible.

Windows, Linux, macOS, Android, iOS and Switch build scripts include the tables.
Only Windows was compiled and executed for this change. Existing build_all.sh
prepares English symbol tables and the address-only HGSS generated directory.
Use the original platform build scripts; see docs/build-en-es.txt.

Validation: English/Spanish startup smoke tests, Spanish intros and initial
scenes, BW start menus, Platinum menus/bag/save. Replacement IPGS reaches the
initial room correctly and completes an 18,000-frame continuous movement test.
Restoring the automated HGSS test snapshot produced a black screen in both
JIT and interpreter; snapshot restoration is not validated. An English HGSS
continuous capture also went black, so this needs separate renderer/harness
investigation before attributing it to regional layouts.
This is not a full playthrough; battles, later areas
and transitions need further gameplay testing. Test ROMs, snapshots, generated
code and binaries remain local and ignored by Git.
