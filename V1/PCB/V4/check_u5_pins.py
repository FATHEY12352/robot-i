import pcbnew
b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

u5 = b.FindFootprintByReference('U5')
print("U5 pins:")
for p in u5.Pads():
    print(f"  pin {p.GetNumber():2s} [{p.GetNetname():10s}] at ({p.GetPosition().x/1e6:.3f}, {p.GetPosition().y/1e6:.3f})")
