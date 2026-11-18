import pcbnew
import math

b = pcbnew.LoadBoard(r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb")

# Find all pads whose bounding box in _populate_pad_obstacles covered (313*0.25, 66*0.25) = (78.25, 16.5)
target_x = 78.25
target_y = 16.5

print(f"Checking who covers ({target_x}, {target_y}):")
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
        if px - hw <= target_x <= px + hw and py - hh <= target_y <= py + hh:
            print(f"  Covered by {ref} pin {p.GetNumber()} [{p.GetNetname()}]: netcode={p.GetNetCode()}")

target_u1_x = 210 * 0.25  # 52.5
target_u1_y = 96 * 0.25   # 24.0
print(f"Checking who covers ({target_u1_x}, {target_u1_y}):")
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
        if px - hw <= target_u1_x <= px + hw and py - hh <= target_u1_y <= py + hh:
            print(f"  Covered by {ref} pin {p.GetNumber()} [{p.GetNetname()}]: netcode={p.GetNetCode()}")
