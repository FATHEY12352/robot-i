import pcbnew
import math
import numpy as np

# Load the logic from test_pass2
import test_pass2 as tp

s_ix, s_iy = tp.s_ix, tp.s_iy
print(f"Start: ({s_ix}, {s_iy})")
for dx in range(0, -15, -1):
    ix = s_ix + dx
    print(f"  x={ix*0.25:.2f} (ix={ix}): blocked={tp.blocked[0, s_iy, ix]}, net_grid={tp.net_grid[0, s_iy, ix]}")
