import pcbnew

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

print("Components in motor area (X >= 75):")
for fp in b.GetFootprints():
    p = fp.GetPosition()
    if p.x/1e6 >= 75:
        print(f"  {fp.GetReference():12s} at ({p.x/1e6:6.2f}, {p.y/1e6:6.2f})")
