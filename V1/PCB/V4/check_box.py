import pcbnew

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

# Check all PTH pads and SMD pads on B.Cu between X=38..60, Y=5.2..10.0
print("Checking obstacles on B.Cu in X=[38..60], Y=[5.2..10.0]:")
found = False
for fp in b.GetFootprints():
    for p in fp.Pads():
        pos = p.GetPosition()
        px, py = pos.x/1e6, pos.y/1e6
        is_th = (p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD)
        if (is_th or p.IsOnLayer(pcbnew.B_Cu)) and 38 <= px <= 60 and 5.2 <= py <= 10.0:
            print(f"  {fp.GetReference()} pin {p.GetNumber()} [{p.GetNetname()}] at ({px:.2f}, {py:.2f})")
            found = True
if not found:
    print("  NONE! 100% CLEAR!")
