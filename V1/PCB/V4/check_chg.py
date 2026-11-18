import pcbnew
b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")
for ref in ['L_CHG', 'C_BST', 'U2']:
    fp = b.FindFootprintByReference(ref)
    p = fp.GetPosition()
    print(f"{ref} at ({p.x/1e6:.2f}, {p.y/1e6:.2f})")
    for pad in fp.Pads():
        if pad.GetNetname() in ['CHG_LX', 'BST']:
            print(f"  pad {pad.GetNumber()} [{pad.GetNetname()}] at ({pad.GetPosition().x/1e6:.2f}, {pad.GetPosition().y/1e6:.2f})")
