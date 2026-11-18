import pcbnew
import sys
import heapq

sys.path.append(r"D:\projekt\ARM\PCB\V4")
from master_synthesizer import FastRouter

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")
r = FastRouter(b, step=0.25)

netname = 'M1_IN2'
net = b.GetNetsByName()[netname]
pads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == netname]
p0 = (pads[0].GetPosition().x/1e6, pads[0].GetPosition().y/1e6)
p1 = (pads[1].GetPosition().x/1e6, pads[1].GetPosition().y/1e6)
l0 = 0
l1 = 0

s_ix, s_iy = r.pos_to_grid(p0[0], p0[1])
t_ix, t_iy = r.pos_to_grid(p1[0], p1[1])
net_code = net.GetNetCode()

print(f"Start: ({s_ix}, {s_iy}) -> Target: ({t_ix}, {t_iy})")
print(f"Start cell: blocked={r.blocked[l0, s_iy, s_ix]}, net={r.net_grid[l0, s_iy, s_ix]}")
print(f"Target cell: blocked={r.blocked[l1, t_iy, t_ix]}, net={r.net_grid[l1, t_iy, t_ix]}")

# Check 4-neighborhood of start
moves = [(0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
for dl, diy, dix in moves:
    niy, nix = s_iy + diy, s_ix + dix
    print(f"  Start neighbor ({diy}, {dix}) -> ({nix}, {niy}): blocked={r.blocked[l0, niy, nix]}, net={r.net_grid[l0, niy, nix]}")

# Check 4-neighborhood of target
for dl, diy, dix in moves:
    niy, nix = t_iy + diy, t_ix + dix
    print(f"  Target neighbor ({diy}, {dix}) -> ({nix}, {niy}): blocked={r.blocked[l1, niy, nix]}, net={r.net_grid[l1, niy, nix]}")

# Let's run BFS to see reachable cells
visited = set()
q = [(l0, s_iy, s_ix)]
visited.add((l0, s_iy, s_ix))
while q:
    l, iy, ix = q.pop(0)
    for dl, diy, dix in moves:
        niy, nix = iy + diy, ix + dix
        if 0 <= niy < r.ny and 0 <= nix < r.nx:
            if (l, niy, nix) not in visited:
                if not r.blocked[l, niy, nix] or r.net_grid[l, niy, nix] == net_code or (l, niy, nix) == (l1, t_iy, t_ix):
                    visited.add((l, niy, nix))
                    q.append((l, niy, nix))
    nl = 1 - l
    if (nl, iy, ix) not in visited and r.is_via_allowed(iy, ix, net_code):
        visited.add((nl, iy, ix))
        q.append((nl, iy, ix))

print(f"Total reachable cells from start: {len(visited)}")
print(f"Is target reachable? {(l1, t_iy, t_ix) in visited}")
