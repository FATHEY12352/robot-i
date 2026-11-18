import pcbnew

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

for t in b.GetTracks():
    if t.GetNetname() == 'SERVO2_FB':
        if isinstance(t, pcbnew.PCB_VIA):
            print(f"VIA at ({t.GetPosition().x/1e6:.2f}, {t.GetPosition().y/1e6:.2f})")
        else:
            print(f"TRACK on {t.GetLayerName()} from ({t.GetStart().x/1e6:.2f}, {t.GetStart().y/1e6:.2f}) to ({t.GetEnd().x/1e6:.2f}, {t.GetEnd().y/1e6:.2f}) w={t.GetWidth()/1e6:.2f}")
