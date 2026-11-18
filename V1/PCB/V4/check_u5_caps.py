import pcbnew
b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

for fp in b.GetFootprints():
    p = fp.GetPosition()
    if p.x/1e6 > 75 and fp.GetReference().startswith('C_'):
        print(f"{fp.GetReference()} at ({p.x/1e6:.2f}, {p.y/1e6:.2f})")
        for pad in fp.Pads():
            print(f"  pin {pad.GetNumber()} [{pad.GetNetname()}] at ({pad.GetPosition().x/1e6:.3f}, {pad.GetPosition().y/1e6:.3f})")
