import pcbnew

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

# Check all PTH pads and SMD pads on B.Cu between X=38..75, Y=11..13
for fp in b.GetFootprints():
    for p in fp.Pads():
        pos = p.GetPosition()
        px, py = pos.x/1e6, pos.y/1e6
        is_th = (p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD)
        if (is_th or p.IsOnLayer(pcbnew.B_Cu)) and 38 <= px <= 75 and 10 <= py <= 14:
            print(f"Obstacle on B.Cu: {fp.GetReference()} pin {p.GetNumber()} [{p.GetNetname()}] at ({px:.2f}, {py:.2f})")
