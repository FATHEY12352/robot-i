import pcbnew

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

# Check all F.Cu pads between X=6..55, Y=45..48
print("Checking obstacles on F.Cu in X=[6..55], Y=[45..48]:")
found = False
for fp in b.GetFootprints():
    for p in fp.Pads():
        pos = p.GetPosition()
        px, py = pos.x/1e6, pos.y/1e6
        is_th = (p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD)
        if (is_th or p.IsOnLayer(pcbnew.F_Cu)) and 6 <= px <= 55 and 45 <= py <= 48:
            print(f"  {fp.GetReference()} pin {p.GetNumber()} [{p.GetNetname()}] at ({px:.2f}, {py:.2f})")
            found = True
