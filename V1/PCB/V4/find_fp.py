import pcbnew
b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")
for fp in b.GetFootprints():
    p = fp.GetPosition()
    if 74 <= p.x/1e6 <= 78 and 10 <= p.y/1e6 <= 25:
        print(fp.GetReference(), p.x/1e6, p.y/1e6)
