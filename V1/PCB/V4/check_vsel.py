import pcbnew
b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

fp = b.FindFootprintByReference('V_SERVO_SEL')
print("V_SERVO_SEL pads:")
for p in fp.Pads():
    print(f"  pin {p.GetNumber()} [{p.GetNetname()}] at ({p.GetPosition().x/1e6:.3f}, {p.GetPosition().y/1e6:.3f})")
