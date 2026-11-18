import pcbnew
import test_tough_nets as tt

b = tt.b
net = b.GetNetsByName()['M1_IN2']
pads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == 'M1_IN2']
p0 = (pads[0].GetPosition().x / 1e6, pads[0].GetPosition().y / 1e6)
p1 = (pads[1].GetPosition().x / 1e6, pads[1].GetPosition().y / 1e6)
s_ix = int(round(p0[0] / tt.step))
s_iy = int(round(p0[1] / tt.step))
t_ix = int(round(p1[0] / tt.step))
t_iy = int(round(p1[1] / tt.step))
net_code = net.GetNetCode()

print(f"s_ix={s_ix}, s_iy={s_iy}, net_code={net_code}")
print(f"Start: blocked={tt.blocked[0, s_iy, s_ix]}, net_grid={tt.net_grid[0, s_iy, s_ix]}")
print(f"t_ix={t_ix}, t_iy={t_iy}")
print(f"Target: blocked={tt.blocked[0, t_iy, t_ix]}, net_grid={tt.net_grid[0, t_iy, t_ix]}")
print(f"Via blocked at start: {tt.via_blocked[0, s_iy, s_ix]}")

# Check how many nodes were popped
# Let's run a debug search
pq = []
import heapq
heapq.heappush(pq, (0.0, 0.0, 0, s_iy, s_ix))
closed = set()
count = 0
while pq:
    f, c, l, iy, ix = heapq.heappop(pq)
    if (l, iy, ix) in closed: continue
    closed.add((l, iy, ix))
    count += 1
    if (l, iy, ix) == (0, t_iy, t_ix):
        print("Target reached!")
        break
    for dl, diy, dix in [(0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]:
        niy, nix = iy + diy, ix + dix
        if 0 <= niy < tt.ny and 0 <= nix < tt.nx:
            if (l, niy, nix) in closed: continue
            if tt.blocked[l, niy, nix]:
                if tt.net_grid[l, niy, nix] != net_code and (l, niy, nix) != (0, t_iy, t_ix):
                    continue
            heapq.heappush(pq, (c + tt.step, c + tt.step, l, niy, nix))
    nl = 1 - l
    if (nl, iy, ix) not in closed and not (tt.via_blocked[0, iy, ix] or tt.via_blocked[1, iy, ix]):
        heapq.heappush(pq, (c + 5.0, c + 5.0, nl, iy, ix))

print(f"Total popped: {count}")
