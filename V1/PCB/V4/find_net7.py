import pcbnew
b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")
for netname, net in b.GetNetsByName().items():
    if net.GetNetCode() == 7:
        print(f"Net 7 is {netname}")
