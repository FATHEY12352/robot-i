import pcbnew
b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

for fp in b.GetFootprints():
    ref = fp.GetReference()
    if ref.startswith('C_CP') or ref.startswith('C_VCP') or 'BOOT' in ref or 'BST' in ref:
        print(f"{ref} at ({fp.GetPosition().x/1e6:.2f}, {fp.GetPosition().y/1e6:.2f})")
        for p in fp.Pads():
            print(f"  pin {p.GetNumber()} [{p.GetNetname()}] at ({p.GetPosition().x/1e6:.3f}, {p.GetPosition().y/1e6:.3f})")
