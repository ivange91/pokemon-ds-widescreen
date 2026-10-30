Spanish Platinum (CPUS, revision 0)
=================================

CPUS.txt contains only the 49 function addresses watched by frontend/platinum.h.
It is a layout table, not a complete symbol map. Overlay bytes are read from the
player's ROM by FuncWatch; the distributed table contains no game instructions.
Use the original English names, including ov5_* names, as the frontend's keys.

Reference dumps used for the comparison (SHA-1):
CPUE revision 0: c5072bf51a5ecc51ade99d3506c023f5bac3eeb3
CPUS revision 0: d30289ddffc5a5f91cdf72dc26fb66c8e9f17c4e

Run the private-ROM verification without extracting or writing game code:
  python tools/platinum/verify_spanish.py english.nds spanish.nds

46 watched entries match unique normalised instruction sequences. The save
routine at 02025C28 is confirmed by four independent matched callers. The two
identical battle-menu routines are distinguished by their callback-table entries:
  DrawGiveUpMoveMenu: EN 02270968 -> ES 02270C70 -> function 0226A0B8
  DrawUseNextMonMenu: EN 02270998 -> ES 02270CA0 -> function 0226A270
Neighbouring callbacks relocate consistently and the table's data is unchanged.
The verifier also checks that every function watched by PtFuncs has an entry.

Build with the original all-games scripts; see docs/build-en-es.txt.
Spanish and English saves are separate (platinum-es.sav and platinum.sav).

Static verification is not full playthrough validation. Test transitions, the
introduction's touch prompts, exploration, menus, saving, battles and level-up
panels with the actual Spanish ROM. The existing introduction control converts
A into a touch while the Poke Ball is visible; B advances its preceding dialogue.
