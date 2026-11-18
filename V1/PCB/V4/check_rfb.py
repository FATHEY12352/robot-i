import pcbnew
b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

for ref in ['R_FB_SRV1', 'R_FB_SRV2']:
    fp = b.FindFootprintByReference(ref)
    print(f"{ref} at ({fp.GetPosition().x/1e6:.2f}, {fp.GetPosition().y/1e6:.2f})")
    for p in fp.Pads():
        print(f"  pin {p.GetNumber()} [{p.GetNetname()}] at ({p.GetPosition().x/1e6:.3f}, {p.GetPosition().y/1e6:.3f})")
