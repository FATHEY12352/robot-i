import pcbnew
import math

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

tx = 76.5
ty = 16.5

for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname() == 'PGND':
            px = p.GetPosition().x / 1e6
            py = p.GetPosition().y / 1e6
            sx = p.GetSize().x / 1e6
            sy = p.GetSize().y / 1e6
            hw = sx/2 + 0.22
            hh = sy/2 + 0.22
            if px - hw <= tx <= px + hw and py - hh <= ty <= py + hh:
                print(f"PGND pad covering ({tx}, {ty}): {fp.GetReference()} pin {p.GetNumber()} at ({px}, {py}) size ({sx}, {sy})")
