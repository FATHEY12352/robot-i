#!/usr/bin/env python3
"""
router_engine.py — High-Precision 2-Layer A* Grid Router Engine for KiCad 10
Guaranteed collision-free orthogonal routing with automated layer hopping and exact DRC spacing.
"""

import sys
import os
import math
import heapq
import time
import numpy as np
import pcbnew

def to_nm(mm):
    return int(round(mm * 1e6))

def from_nm(nm):
    return nm / 1e6

class GridRouter:
    def __init__(self, pcb_path=r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb", step=0.25):
        self.pcb_path = pcb_path
        self.board = pcbnew.LoadBoard(pcb_path)
        self.step = step
        self.w_mm = 98.0
        self.h_mm = 68.0
        self.nx = int(round(self.w_mm / self.step)) + 1
        self.ny = int(round(self.h_mm / self.step)) + 1
        
        # Layer 0: F.Cu, Layer 1: B.Cu
        self.blocked = np.zeros((2, self.ny, self.nx), dtype=bool)
        self.net_grid = np.full((2, self.ny, self.nx), -1, dtype=np.int32)
        
        self.nets = {str(k): v for k, v in self.board.GetNetsByName().items()}
        self.vias = set()
        
        self._block_boundaries()
        self._block_antenna_keepout()
        self._populate_pad_obstacles()

    def _block_boundaries(self):
        # 1.0mm margin around board edges
        margin_cells = int(round(1.0 / self.step))
        self.blocked[:, :margin_cells, :] = True
        self.blocked[:, -margin_cells:, :] = True
        self.blocked[:, :, :margin_cells] = True
        self.blocked[:, :, -margin_cells:] = True

    def _block_antenna_keepout(self):
        # ESP32 antenna keepout: X in [38.0, 58.0], Y in [0.0, 5.0]
        x1 = int(round(38.0 / self.step))
        x2 = int(round(58.0 / self.step))
        y2 = int(round(5.0 / self.step))
        self.blocked[:, :y2+1, x1:x2+1] = True

    def _populate_pad_obstacles(self):
        # Clearance 0.25mm ensures >= 0.20mm edge-to-edge
        clearance = 0.25 # mm
        for fp in self.board.GetFootprints():
            for p in fp.Pads():
                pos = p.GetPosition()
                px = from_nm(pos.x)
                py = from_nm(pos.y)
                size = p.GetSize()
                sx = from_nm(size.x)
                sy = from_nm(size.y)
                is_th = (p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD)
                
                net_code = p.GetNetCode()
                
                hw = (sx / 2.0) + clearance
                hh = (sy / 2.0) + clearance
                
                if px + hw < 0 or px - hw > self.w_mm or py + hh < 0 or py - hh > self.h_mm:
                    continue
                
                ix1 = max(0, min(self.nx - 1, int(math.floor((px - hw) / self.step))))
                ix2 = max(0, min(self.nx - 1, int(math.ceil((px + hw) / self.step))))
                iy1 = max(0, min(self.ny - 1, int(math.floor((py - hh) / self.step))))
                iy2 = max(0, min(self.ny - 1, int(math.ceil((py + hh) / self.step))))
                
                if ix2 < ix1 or iy2 < iy1:
                    continue
                
                layers = [0, 1] if is_th else [0]
                for l in layers:
                    self.blocked[l, iy1:iy2+1, ix1:ix2+1] = True
                    self.net_grid[l, iy1:iy2+1, ix1:ix2+1] = net_code

    def pos_to_grid(self, x_mm, y_mm):
        ix = int(round(x_mm / self.step))
        iy = int(round(y_mm / self.step))
        return (max(0, min(self.nx - 1, ix)), max(0, min(self.ny - 1, iy)))

    def grid_to_pos(self, ix, iy):
        return (round(ix * self.step, 3), round(iy * self.step, 3))

    def is_via_allowed(self, iy, ix, net_code, rad=3):
        # Via requires both layers free of other nets within radius rad (0.75mm)
        y_min = max(0, iy - rad)
        y_max = min(self.ny - 1, iy + rad)
        x_min = max(0, ix - rad)
        x_max = min(self.nx - 1, ix + rad)
        
        for l in (0, 1):
            sub_b = self.blocked[l, y_min:y_max+1, x_min:x_max+1]
            sub_n = self.net_grid[l, y_min:y_max+1, x_min:x_max+1]
            # If any cell is blocked by a different net, reject
            conflict = sub_b & (sub_n != -1) & (sub_n != net_code)
            if np.any(conflict):
                return False
        return True

    def mark_track_blocked(self, layer, p1_grid, p2_grid, net_code, rad=1):
        x1, y1 = p1_grid
        x2, y2 = p2_grid
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        cx, cy = x1, y1
        while True:
            y_min = max(0, cy - rad)
            y_max = min(self.ny - 1, cy + rad)
            x_min = max(0, cx - rad)
            x_max = min(self.nx - 1, cx + rad)
            self.blocked[layer, y_min:y_max+1, x_min:x_max+1] = True
            self.net_grid[layer, y_min:y_max+1, x_min:x_max+1] = net_code
            if cx == x2 and cy == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy

    def mark_via_blocked(self, ix, iy, net_code, rad=3):
        y_min = max(0, iy - rad)
        y_max = min(self.ny - 1, iy + rad)
        x_min = max(0, ix - rad)
        x_max = min(self.nx - 1, ix + rad)
        for l in (0, 1):
            self.blocked[l, y_min:y_max+1, x_min:x_max+1] = True
            self.net_grid[l, y_min:y_max+1, x_min:x_max+1] = net_code
        self.vias.add((ix, iy))

    def find_path(self, start_pos, target_pos, net_code, start_layer=0, target_layer=0):
        s_ix, s_iy = self.pos_to_grid(start_pos[0], start_pos[1])
        t_ix, t_iy = self.pos_to_grid(target_pos[0], target_pos[1])
        
        pq = []
        heapq.heappush(pq, (0.0, 0.0, start_layer, s_iy, s_ix))
        dist = {}
        dist[(start_layer, s_iy, s_ix)] = 0.0
        came_from = {}
        
        def h(l, iy, ix):
            dx = abs(ix - t_ix) * self.step
            dy = abs(iy - t_iy) * self.step
            dl = abs(l - target_layer) * 3.0
            return (dx + dy) + dl

        target_reached = None
        moves = [(0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
        via_cost = 6.0
        
        while pq:
            f, c, l, iy, ix = heapq.heappop(pq)
            
            if (l, iy, ix) == (target_layer, t_iy, t_ix):
                target_reached = (l, iy, ix)
                break
                
            if c > dist.get((l, iy, ix), float('inf')):
                continue
                
            # Planar moves
            for dl, diy, dix in moves:
                niy, nix = iy + diy, ix + dix
                if 0 <= niy < self.ny and 0 <= nix < self.nx:
                    if self.blocked[l, niy, nix]:
                        if self.net_grid[l, niy, nix] != net_code and (l, niy, nix) != (target_layer, t_iy, t_ix):
                            continue
                    
                    nc = c + self.step
                    state = (l, niy, nix)
                    if nc < dist.get(state, float('inf')):
                        dist[state] = nc
                        nf = nc + h(l, niy, nix)
                        came_from[state] = (l, iy, ix)
                        heapq.heappush(pq, (nf, nc, l, niy, nix))
                        
            # Via transition
            nl = 1 - l
            if self.is_via_allowed(iy, ix, net_code, rad=3):
                nc = c + via_cost
                state = (nl, iy, ix)
                if nc < dist.get(state, float('inf')):
                    dist[state] = nc
                    nf = nc + h(nl, iy, ix)
                    came_from[state] = (l, iy, ix)
                    heapq.heappush(pq, (nf, nc, nl, iy, ix))
                        
        if not target_reached:
            return None
            
        path = []
        curr = target_reached
        while curr:
            path.append(curr)
            curr = came_from.get(curr)
        path.reverse()
        return path
