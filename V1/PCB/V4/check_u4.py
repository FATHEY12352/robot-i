import pcbnew
b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

u4 = b.FindFootprintByReference('U4')
print("U4 pads:")
for p in u4.Pads():
    print(f"  pin {p.GetNumber()} [{p.GetNetname()}] at ({p.GetPosition().x/1e6:.3f}, {p.GetPosition().y/1e6:.3f})")
