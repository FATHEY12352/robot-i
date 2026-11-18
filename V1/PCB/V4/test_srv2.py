import pcbnew
import sys
import numpy as np
import heapq

sys.path.append(r"D:\projekt\ARM\PCB\V4")
from master_synthesizer import FastRouter

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")
r = FastRouter(b, step=0.25)

net = b.GetNetsByName()['SRV2_FB_IN']
pads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == 'SRV2_FB_IN']
for p in pads:
    print(p.GetNumber(), p.GetPosition().x/1e6, p.GetPosition().y/1e6, p.GetAttribute())

p0 = (pads[0].GetPosition().x/1e6, pads[0].GetPosition().y/1e6)
p1 = (pads[1].GetPosition().x/1e6, pads[1].GetPosition().y/1e6)
l0 = 0 if pads[0].GetAttribute() == pcbnew.PAD_ATTRIB_SMD else 1
l1 = 0 if pads[1].GetAttribute() == pcbnew.PAD_ATTRIB_SMD else 1

print(f"p0: {p0}, l0: {l0} -> p1: {p1}, l1: {l1}")
s_ix, s_iy = r.pos_to_grid(p0[0], p0[1])
t_ix, t_iy = r.pos_to_grid(p1[0], p1[1])
print(f"start grid: ({s_ix}, {s_iy}), target grid: ({t_ix}, {t_iy})")
print(f"start blocked: l0={r.blocked[l0, s_iy, s_ix]}, l1={r.blocked[1-l0, s_iy, s_ix]}, net={r.net_grid[l0, s_iy, s_ix]}")
print(f"target blocked: l1={r.blocked[l1, t_iy, t_ix]}, net={r.net_grid[l1, t_iy, t_ix]}")

path = r.find_path(p0, p1, net.GetNetCode(), start_layer=l0, target_layer=l1)
print("Path found:", len(path) if path else "None")
