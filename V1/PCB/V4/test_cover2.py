import pcbnew
import math

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

s_ix, s_iy = 313, 66
t_ix, t_iy = 210, 96

step = 0.25
nx = int(round(98.0 / step)) + 1
ny = int(round(68.0 / step)) + 1

for fp in b.GetFootprints():
    ref = fp.GetReference()
    for p in fp.Pads():
        pos = p.GetPosition()
        px = pos.x / 1e6
        py = pos.y / 1e6
        size = p.GetSize()
        sx = size.x / 1e6
        sy = size.y / 1e6
        is_fine_pitch = (ref in ['U1', 'U2', 'U3', 'U5', 'U6'])
        cl_x = 0.12 if is_fine_pitch and sx < 0.6 else 0.22
        cl_y = 0.12 if is_fine_pitch and sy < 0.6 else 0.22
        hw = (sx / 2.0) + cl_x
        hh = (sy / 2.0) + cl_y
        
        ix1 = max(0, min(nx - 1, int(math.floor((px - hw) / step))))
        ix2 = max(0, min(nx - 1, int(math.ceil((px + hw) / step))))
        iy1 = max(0, min(ny - 1, int(math.floor((py - hh) / step))))
        iy2 = max(0, min(ny - 1, int(math.ceil((py + hh) / step))))
        
        if iy1 <= s_iy <= iy2 and ix1 <= s_ix <= ix2:
            print(f"Start ({s_ix}, {s_iy}) hit by {ref} pin {p.GetNumber()} [{p.GetNetname()}] netcode={p.GetNetCode()}")
            
        if iy1 <= t_iy <= iy2 and ix1 <= t_ix <= ix2:
            print(f"Target ({t_ix}, {t_iy}) hit by {ref} pin {p.GetNumber()} [{p.GetNetname()}] netcode={p.GetNetCode()}")
