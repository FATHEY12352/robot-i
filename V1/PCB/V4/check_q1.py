import pcbnew
b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

q1 = b.FindFootprintByReference('Q1')
print("Q1 pads:")
for p in q1.Pads():
    print(f"  pin {p.GetNumber()} [{p.GetNetname()}] at ({p.GetPosition().x/1e6:.3f}, {p.GetPosition().y/1e6:.3f})")
