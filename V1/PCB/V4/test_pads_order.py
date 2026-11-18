import pcbnew

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

pads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == 'SERVO2_FB']
for idx, p in enumerate(pads):
    print(f"pad[{idx}]: {p.GetParentFootprint().GetReference()} pin {p.GetNumber()} at ({p.GetPosition().x/1e6:.3f}, {p.GetPosition().y/1e6:.3f})")
