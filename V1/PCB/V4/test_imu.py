import pcbnew
import sys

sys.path.append(r"D:\projekt\ARM\PCB\V4")
from master_synthesizer import FastRouter

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")
r = FastRouter(b, step=0.25)

netname = 'IMU_INT'
net = b.GetNetsByName()[netname]
pads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == netname]
for p in pads:
    print(p.GetParentFootprint().GetReference(), p.GetNumber(), p.GetPosition().x/1e6, p.GetPosition().y/1e6)

p0 = (pads[0].GetPosition().x/1e6, pads[0].GetPosition().y/1e6)
p1 = (pads[1].GetPosition().x/1e6, pads[1].GetPosition().y/1e6)
l0 = 0 if pads[0].GetAttribute() == pcbnew.PAD_ATTRIB_SMD else 1
l1 = 0 if pads[1].GetAttribute() == pcbnew.PAD_ATTRIB_SMD else 1

path = r.find_path(p0, p1, net.GetNetCode(), start_layer=l0, target_layer=l1)
print("Path found:", len(path) if path else "None")
