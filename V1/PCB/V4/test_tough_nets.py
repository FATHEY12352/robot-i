#!/usr/bin/env python3
"""
Test 4 tough nets on 0.20mm grid with 2-pass obstacle marking and escape stubs.
"""
import pcbnew
import math
import heapq
import numpy as np

PCB_PATH = r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb"
b = pcbnew.LoadBoard(PCB_PATH)

step = 0.20
w_mm, h_mm = 98.0, 68.0
nx = int(round(w_mm / step)) + 1
ny = int(round(h_mm / step)) + 1

blocked = np.zeros((2, ny, nx), dtype=bool)
via_blocked = np.zeros((2, ny, nx), dtype=bool)
net_grid = np.full((2, ny, nx), -1, dtype=np.int32)

# Pass 1: Block boundaries & antenna keepout
m = int(round(1.0 / step))
blocked[:, :m, :] = True
blocked[:, -m:, :] = True
blocked[:, :, :m] = True
blocked[:, :, -m:] = True

# Antenna keepout (38..58, 0..5)
x1, x2 = int(round(38.0 / step)), int(round(58.0 / step))
y2 = int(round(5.0 / step))
blocked[:, :y2+1, x1:x2+1] = True

# Pass 2: Block pad clearance
for fp in b.GetFootprints():
    ref = fp.GetReference()
    for p in fp.Pads():
        pos = p.GetPosition()
        px, py = pos.x / 1e6, pos.y / 1e6
        size = p.GetSize()
        sx, sy = size.x / 1e6, size.y / 1e6
        is_th = (p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD)
        
        is_fine_pitch = (ref in ['U1', 'U2', 'U3', 'U5', 'U6'])
        cl_x = 0.12 if is_fine_pitch and sx < 0.6 else 0.20
        cl_y = 0.12 if is_fine_pitch and sy < 0.6 else 0.20
        hw = (sx / 2.0) + cl_x
        hh = (sy / 2.0) + cl_y
        
        if px + hw < 0 or px - hw > w_mm or py + hh < 0 or py - hh > h_mm:
            continue
        
        ix1 = max(0, min(nx - 1, int(math.floor((px - hw) / step))))
        ix2 = max(0, min(nx - 1, int(math.ceil((px + hw) / step))))
        iy1 = max(0, min(ny - 1, int(math.floor((py - hh) / step))))
        iy2 = max(0, min(ny - 1, int(math.ceil((py + hh) / step))))
        
        layers = [0, 1] if is_th else [0]
        for l in layers:
            blocked[l, iy1:iy2+1, ix1:ix2+1] = True

# Pass 3: Restore copper cells of each pad to its own net_code
for fp in b.GetFootprints():
    ref = fp.GetReference()
    for p in fp.Pads():
        pos = p.GetPosition()
        px, py = pos.x / 1e6, pos.y / 1e6
        size = p.GetSize()
        sx, sy = size.x / 1e6, size.y / 1e6
        is_th = (p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD)
        net_code = p.GetNetCode()
        
        hw = sx / 2.0
        hh = sy / 2.0
        
        if px + hw < 0 or px - hw > w_mm or py + hh < 0 or py - hh > h_mm:
            continue
            
        ix1 = max(0, min(nx - 1, int(math.floor((px - hw) / step))))
        ix2 = max(0, min(nx - 1, int(math.ceil((px + hw) / step))))
        iy1 = max(0, min(ny - 1, int(math.floor((py - hh) / step))))
        iy2 = max(0, min(ny - 1, int(math.ceil((py + hh) / step))))
        
        layers = [0, 1] if is_th else [0]
        for l in layers:
            net_grid[l, iy1:iy2+1, ix1:ix2+1] = net_code
            c_ix = max(0, min(nx - 1, int(round(px / step))))
            c_iy = max(0, min(ny - 1, int(round(py / step))))
            net_grid[l, c_iy, c_ix] = net_code

# Precompute via blocked (rad=2 -> 0.40mm)
for l in [0, 1]:
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            sy1 = max(0, dy); sy2 = min(ny, ny + dy)
            sx1 = max(0, dx); sx2 = min(nx, nx + dx)
            ty1 = max(0, -dy); ty2 = min(ny, ny - dy)
            tx1 = max(0, -dx); tx2 = min(nx, nx - dx)
            via_blocked[l, ty1:ty2, tx1:tx2] |= blocked[l, sy1:sy2, sx1:sx2]

def find_path(p_start, p_target, net_code, l_start=0, l_target=0):
    s_ix = max(0, min(nx - 1, int(round(p_start[0] / step))))
    s_iy = max(0, min(ny - 1, int(round(p_start[1] / step))))
    t_ix = max(0, min(nx - 1, int(round(p_target[0] / step))))
    t_iy = max(0, min(ny - 1, int(round(p_target[1] / step))))
    
    pq = []
    heapq.heappush(pq, (0.0, 0.0, l_start, s_iy, s_ix))
    dist = {(l_start, s_iy, s_ix): 0.0}
    came_from = {}
    closed_set = set()
    moves = [(0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    
    def h(l, iy, ix):
        return (abs(ix - t_ix) + abs(iy - t_iy)) * step + abs(l - l_target) * 3.0
        
    target_reached = None
    while pq:
        f, c, l, iy, ix = heapq.heappop(pq)
        if (l, iy, ix) in closed_set: continue
        closed_set.add((l, iy, ix))
        if (l, iy, ix) == (l_target, t_iy, t_ix):
            target_reached = (l, iy, ix)
            break
        for dl, diy, dix in moves:
            niy, nix = iy + diy, ix + dix
            if 0 <= niy < ny and 0 <= nix < nx:
                if (l, niy, nix) in closed_set: continue
                if blocked[l, niy, nix]:
                    if net_grid[l, niy, nix] != net_code and (l, niy, nix) != (l_target, t_iy, t_ix):
                        continue
                nc = c + step
                state = (l, niy, nix)
                if nc < dist.get(state, float('inf')):
                    dist[state] = nc
                    nf = nc + h(l, niy, nix)
                    came_from[state] = (l, iy, ix)
                    heapq.heappush(pq, (nf, nc, l, niy, nix))
        nl = 1 - l
        if (nl, iy, ix) not in closed_set and not (via_blocked[0, iy, ix] or via_blocked[1, iy, ix]):
            nc = c + 5.0
            state = (nl, iy, ix)
            if nc < dist.get(state, float('inf')):
                dist[state] = nc
                nf = nc + h(nl, iy, ix)
                came_from[state] = (l, iy, ix)
                heapq.heappush(pq, (nf, nc, nl, iy, ix))
                
    if not target_reached: return None
    path = []
    curr = target_reached
    while curr:
        path.append(curr)
        curr = came_from.get(curr)
    path.reverse()
    return path

test_nets = ['M1_IN2', 'IMU_INT', 'SRV2_FB_IN', 'ENC1_B_RAW']
for netname in test_nets:
    net = b.GetNetsByName()[netname]
    pads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == netname]
    p0 = (pads[0].GetPosition().x / 1e6, pads[0].GetPosition().y / 1e6)
    p1 = (pads[1].GetPosition().x / 1e6, pads[1].GetPosition().y / 1e6)
    l0 = 0 if pads[0].GetAttribute() == pcbnew.PAD_ATTRIB_SMD else 1
    l1 = 0 if pads[1].GetAttribute() == pcbnew.PAD_ATTRIB_SMD else 1
    
    path = find_path(p0, p1, net.GetNetCode(), l_start=l0, l_target=l1)
    print(f"Net {netname:12s}: {'SUCCESS (len ' + str(len(path)) + ')' if path else 'FAILED'}")
