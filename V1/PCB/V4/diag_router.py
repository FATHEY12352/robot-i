import pcbnew

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

for ref in ["D_CLAMP1", "D_CLAMP2", "D_CLAMP3", "D_CLAMP4"]:
    fp = b.FindFootprintByReference(ref)
    print(f"{ref} at ({fp.GetPosition().x/1e6:.2f}, {fp.GetPosition().y/1e6:.2f})")
    for p in fp.Pads():
        print(f"  pin {p.GetNumber()} [{p.GetNetname()}] at ({p.GetPosition().x/1e6:.3f}, {p.GetPosition().y/1e6:.3f})")
