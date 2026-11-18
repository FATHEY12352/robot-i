import pcbnew

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

u5_p2 = b.FindFootprintByReference('U5').FindPadByNumber('2')
u1_p24 = b.FindFootprintByReference('U1').FindPadByNumber('24')

print(f"U5.2: netcode={u5_p2.GetNetCode()}, netname='{u5_p2.GetNetname()}'")
print(f"U1.24: netcode={u1_p24.GetNetCode()}, netname='{u1_p24.GetNetname()}'")
