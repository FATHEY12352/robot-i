#!/usr/bin/env python3
"""
Step 1 & 2 Test: Ground planes, star tie, thermal vias, ground vias, and power corridors.
"""
import pcbnew
import math

PCB_PATH = r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb"

def to_nm(mm): return int(round(mm * 1e6))
def from_nm(nm): return nm / 1e6

board = pcbnew.LoadBoard(PCB_PATH)
nets = {str(k): v for k, v in board.GetNetsByName().items()}

# Clean existing tracks and zones
u2_thermal_vias = {(15.0, 15.5), (16.0, 15.5), (15.0, 14.5), (16.0, 14.5)}
for t in list(board.GetTracks()):
    if isinstance(t, pcbnew.PCB_VIA):
        pos = (round(from_nm(t.GetPosition().x), 2), round(from_nm(t.GetPosition().y), 2))
        if pos not in u2_thermal_vias:
            board.Delete(t)
    else:
        board.Delete(t)
for z in list(board.Zones()):
    if not z.GetIsRuleArea():
        board.Delete(z)

# Ground Zones
def add_zone(net_name, layer, pts, priority):
    z = pcbnew.ZONE(board)
    z.SetNet(nets[net_name])
    lset = pcbnew.LSET()
    lset.AddLayer(layer)
    z.SetLayerSet(lset)
    poly = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in pts: poly.Append(pcbnew.VECTOR2I(to_nm(x), to_nm(y)))
    poly.SetClosed(True)
    z.Outline().AddOutline(poly)
    z.SetLocalClearance(to_nm(0.20))
    z.SetThermalReliefGap(to_nm(0.25))
    z.SetThermalReliefSpokeWidth(to_nm(0.40))
    z.SetMinThickness(to_nm(0.1524))
    z.SetAssignedPriority(priority)
    board.Add(z)
    return z

pgnd_pts = [
    (0.5, 0.5), (0.5, 67.5), (97.5, 67.5), (97.5, 0.5),
    (74.5, 0.5), (74.5, 36.5), (26.0, 36.5), (26.0, 0.5)
]
add_zone('PGND', pcbnew.B_Cu, pgnd_pts, priority=1)
gnd_pts = [(26.0, 0.5), (74.5, 0.5), (74.5, 36.5), (26.0, 36.5)]
add_zone('GND', pcbnew.B_Cu, gnd_pts, priority=2)

def add_track(net_name, layer, width_mm, p1, p2):
    if math.isclose(p1[0], p2[0], abs_tol=1e-4) and math.isclose(p1[1], p2[1], abs_tol=1e-4): return None
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(to_nm(p1[0]), to_nm(p1[1])))
    t.SetEnd(pcbnew.VECTOR2I(to_nm(p2[0]), to_nm(p2[1])))
    t.SetWidth(to_nm(width_mm))
    t.SetLayer(layer)
    t.SetNet(nets[net_name])
    board.Add(t)
    return t

def add_polyline(net_name, layer, width_mm, pts):
    for i in range(len(pts) - 1): add_track(net_name, layer, width_mm, pts[i], pts[i+1])

def add_via(net_name, pos, size_mm=0.6, drill_mm=0.3):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(to_nm(pos[0]), to_nm(pos[1])))
    v.SetWidth(to_nm(size_mm))
    v.SetDrill(to_nm(drill_mm))
    v.SetNet(nets[net_name])
    board.Add(v)
    return v

# Star Ground at NT1
add_track('PGND', pcbnew.F_Cu, 0.5, (6.0, 37.08), (7.7, 37.08))
add_via('GND', (8.7, 35.5), size_mm=0.6, drill_mm=0.3)
add_track('GND', pcbnew.F_Cu, 0.25, (8.7, 37.08), (8.7, 35.5))
# GND corridor across to X = 26.5 mm on F.Cu at Y = 35.5 (so it does NOT cross VMOT on B.Cu!)
add_polyline('GND', pcbnew.F_Cu, 0.4, [(8.7, 35.5), (26.5, 35.5)])
add_via('GND', (26.5, 35.5), size_mm=0.6, drill_mm=0.3)

# Thermal Pad Ties
p_u2_25 = board.FindFootprintByReference('U2').FindPadByNumber('25').GetPosition()
for vx, vy in [(15.0, 14.5), (16.0, 14.5), (15.0, 15.5), (16.0, 15.5)]:
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(p_u2_25)
    t.SetEnd(pcbnew.VECTOR2I(to_nm(vx), to_nm(vy)))
    t.SetWidth(to_nm(0.3))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(nets['PGND'])
    board.Add(t)

for u_ref in ('U5', 'U6'):
    u_fp = board.FindFootprintByReference(u_ref)
    p17_x = from_nm(u_fp.GetPosition().x)
    for pnum in ('7', '9', '15', '16'):
        p = u_fp.FindPadByNumber(pnum)
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(p.GetPosition())
        t.SetEnd(pcbnew.VECTOR2I(to_nm(p17_x), p.GetPosition().y))
        t.SetWidth(to_nm(0.3))
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(nets['PGND'])
        board.Add(t)

# In-domain Ground Vias for all SMD GND and PGND pads
pad_boxes = []
for fp in board.GetFootprints():
    for p in fp.Pads():
        pos = p.GetPosition()
        size = p.GetSize()
        px, py = from_nm(pos.x), from_nm(pos.y)
        sx, sy = from_nm(size.x), from_nm(size.y)
        pad_boxes.append((px - sx/2 - 0.25, py - sy/2 - 0.25, px + sx/2 + 0.25, py + sy/2 + 0.25, p.GetNetname()))

def is_via_clear(vx, vy, netname, vr=0.55):
    for x1, y1, x2, y2, p_net in pad_boxes:
        if p_net != netname:
            if not (vx + vr < x1 or vx - vr > x2 or vy + vr < y1 or vy - vr > y2):
                return False
    return True

for netname in ['GND', 'PGND']:
    net = nets[netname]
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in ['U1', 'U2', 'U3', 'U5', 'U6', 'NT1', 'J_USB']: continue
        for p in fp.Pads():
            if p.GetNetname() == netname and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                px, py = from_nm(p.GetPosition().x), from_nm(p.GetPosition().y)
                if netname == 'GND' and not (26.0 <= px <= 74.5 and 0.5 <= py <= 36.5): continue
                if netname == 'PGND' and (26.0 <= px <= 74.5 and 0.5 <= py <= 36.5): continue
                for dist in [0.85, 1.05, 1.25, 1.45]:
                    found = False
                    for ang in [0, 90, 180, 270, 45, 135, 225, 315]:
                        rad = math.radians(ang)
                        vx = round(px + dist * math.cos(rad), 3)
                        vy = round(py + dist * math.sin(rad), 3)
                        if 1.0 < vx < 97.0 and 1.0 < vy < 67.0:
                            if is_via_clear(vx, vy, netname):
                                add_via(netname, (vx, vy), size_mm=0.6, drill_mm=0.3)
                                add_track(netname, pcbnew.F_Cu, 0.25, (px, py), (vx, vy))
                                found = True
                                break
                    if found: break

# J_USB shield ties on F.Cu
jusb = board.FindFootprintByReference('J_USB')
sh_pads = [p for p in jusb.Pads() if p.GetNumber() == 'SH']
sh1 = [p for p in sh_pads if from_nm(p.GetPosition().y) > 15][0]
sh2 = [p for p in sh_pads if from_nm(p.GetPosition().y) < 15][0]
for pnum, sh in [('A1', sh1), ('B12', sh1), ('A12', sh2), ('B1', sh2)]:
    p = jusb.FindPadByNumber(pnum)
    p_pos = (from_nm(p.GetPosition().x), from_nm(p.GetPosition().y))
    sh_pos = (from_nm(sh.GetPosition().x), from_nm(sh.GetPosition().y))
    add_track('GND', pcbnew.F_Cu, 0.3, p_pos, sh_pos)

# ----------------- POWER CORRIDORS -----------------
# Servo Power: +6V, V_SERVO, V_UBEC, +6V_BUCK
add_track('+6V', pcbnew.F_Cu, 1.8, (20.0, 59.04), (80.0, 59.04))
add_polyline('V_SERVO', pcbnew.F_Cu, 2.0, [(58.54, 49.5), (58.54, 51.5), (64.0, 51.5), (64.0, 49.5)])
add_track('+6V', pcbnew.F_Cu, 1.8, (65.0, 49.5), (65.0, 59.04))
add_polyline('V_UBEC', pcbnew.B_Cu, 2.5, [(6.0, 51.0), (61.08, 51.0), (61.08, 49.5)])

add_polyline('+6V_BUCK', pcbnew.F_Cu, 3.0, [(41.48, 44.0), (46.3, 44.0), (46.3, 43.0)])
add_polyline('+6V_BUCK', pcbnew.F_Cu, 2.5, [(46.3, 44.0), (56.0, 44.0), (56.0, 49.5)])
add_track('+6V_BUCK', pcbnew.F_Cu, 1.0, (45.03, 49.5), (45.03, 44.0))
add_track('+6V_BUCK', pcbnew.F_Cu, 1.0, (49.73, 49.5), (49.73, 44.0))
add_via('+6V_BUCK', (41.48, 41.5), size_mm=0.6, drill_mm=0.3)
add_track('+6V_BUCK', pcbnew.F_Cu, 0.3, (41.48, 44.0), (41.48, 41.5))
add_via('+6V_BUCK', (24.68, 41.5), size_mm=0.6, drill_mm=0.3)
add_track('+6V_BUCK', pcbnew.B_Cu, 0.3, (41.48, 41.5), (24.68, 41.5))
add_polyline('+6V_BUCK', pcbnew.F_Cu, 0.3, [(24.68, 41.5), (24.68, 44.0)])
add_polyline('FB_SERVO', pcbnew.F_Cu, 0.25, [(24.06, 40.405), (26.325, 40.405), (26.325, 46.5), (24.675, 46.5)])

# SRV_PH
add_polyline('SRV_PH', pcbnew.F_Cu, 0.4, [(24.06, 36.595), (24.06, 34.5), (20.775, 34.5)])
add_polyline('SRV_PH', pcbnew.F_Cu, 2.5, [(24.06, 36.595), (29.5, 36.595), (29.5, 44.0), (32.53, 44.0)])
add_via('SRV_PH', (29.5, 46.5), size_mm=0.8, drill_mm=0.4)
add_track('SRV_PH', pcbnew.F_Cu, 2.0, (29.5, 44.0), (29.5, 46.5))
add_via('SRV_PH', (17.5, 48.0), size_mm=0.8, drill_mm=0.4)
add_polyline('SRV_PH', pcbnew.B_Cu, 2.0, [(29.5, 46.5), (17.5, 46.5), (17.5, 48.0)])
add_track('SRV_PH', pcbnew.F_Cu, 2.0, (17.5, 48.0), (17.5, 49.9))

# Motor Power: VMOT, M1_OUT1/2, M2_OUT1/2
# VMOT 4.0mm trunk along B.Cu at Y = 52.5 mm, then up at X = 88.0 mm
add_via('VMOT', (19.5, 25.5), size_mm=0.8, drill_mm=0.4)
add_polyline('VMOT', pcbnew.B_Cu, 4.0, [(19.5, 25.5), (19.5, 52.5), (88.0, 52.5), (88.0, 8.0)])
# Tap into U6 (Y=42.0) and C_VM2
add_via('VMOT', (85.5, 43.0), size_mm=0.8, drill_mm=0.4)
add_track('VMOT', pcbnew.B_Cu, 2.0, (88.0, 43.0), (85.5, 43.0))
add_track('VMOT', pcbnew.F_Cu, 0.6, (85.5, 43.0), (83.86, 42.98))
add_polyline('VMOT', pcbnew.F_Cu, 1.5, [(85.5, 43.0), (85.5, 37.0), (81.78, 37.0)])
add_track('VMOT', pcbnew.F_Cu, 2.0, (85.5, 30.0), (79.7, 30.0))
add_track('VMOT', pcbnew.B_Cu, 2.0, (88.0, 30.0), (85.5, 30.0))
add_via('VMOT', (85.5, 30.0), size_mm=0.8, drill_mm=0.4)
add_polyline('VMOT', pcbnew.F_Cu, 1.2, [(79.7, 30.0), (79.7, 33.95), (76.0, 33.95)])
add_polyline('VMOT', pcbnew.F_Cu, 1.2, [(79.7, 33.95), (79.7, 37.28), (76.0, 37.28)])

# Tap into U5 (Y=18.0) and C_VM1
add_via('VMOT', (85.5, 19.0), size_mm=0.8, drill_mm=0.4)
add_track('VMOT', pcbnew.B_Cu, 2.0, (88.0, 19.0), (85.5, 19.0))
add_track('VMOT', pcbnew.F_Cu, 0.6, (85.5, 19.0), (83.86, 18.98))
add_polyline('VMOT', pcbnew.F_Cu, 1.5, [(85.5, 19.0), (85.5, 13.5), (81.78, 13.5)])
add_track('VMOT', pcbnew.F_Cu, 2.0, (85.5, 7.5), (79.7, 7.5))
add_track('VMOT', pcbnew.B_Cu, 2.0, (88.0, 7.5), (85.5, 7.5))
add_via('VMOT', (85.5, 7.5), size_mm=0.8, drill_mm=0.4)
add_polyline('VMOT', pcbnew.F_Cu, 1.2, [(79.7, 7.5), (79.7, 11.95), (76.0, 11.95)])
add_polyline('VMOT', pcbnew.F_Cu, 1.2, [(79.7, 11.95), (79.7, 15.28), (76.0, 15.28)])

# Motor Outputs (neckdown 0.50mm to escape pin, then 3.0mm to header)
add_via('M1_OUT1', (77.0, 23.08), size_mm=0.8, drill_mm=0.4)
add_track('M1_OUT1', pcbnew.F_Cu, 0.5, (78.14, 20.275), (77.0, 23.08))
add_track('M1_OUT1', pcbnew.B_Cu, 3.0, (77.0, 23.08), (92.0, 23.08))

add_track('M1_OUT2', pcbnew.F_Cu, 0.5, (83.86, 19.625), (85.5, 19.625))
add_polyline('M1_OUT2', pcbnew.F_Cu, 3.0, [(85.5, 19.625), (86.5, 18.0), (92.0, 18.0)])

add_via('M2_OUT1', (77.0, 47.08), size_mm=0.8, drill_mm=0.4)
add_track('M2_OUT1', pcbnew.F_Cu, 0.5, (78.14, 44.275), (77.0, 47.08))
add_track('M2_OUT1', pcbnew.B_Cu, 3.0, (77.0, 47.08), (92.0, 47.08))

add_track('M2_OUT2', pcbnew.F_Cu, 0.5, (83.86, 43.625), (85.5, 43.625))
add_polyline('M2_OUT2', pcbnew.F_Cu, 3.0, [(85.5, 43.625), (86.5, 42.0), (92.0, 42.0)])

# Battery & Logic Supply
add_polyline('VBAT_RAW', pcbnew.F_Cu, 2.5, [(6.0, 32.0), (19.48, 32.0)])
add_track('VBAT_RAW', pcbnew.F_Cu, 1.5, (19.48, 28.59), (19.48, 32.41))
add_polyline('VBAT_RAW', pcbnew.F_Cu, 0.8, [(6.0, 32.0), (8.5, 32.0), (8.5, 42.0)])
add_polyline('VBAT_RAW', pcbnew.F_Cu, 1.5, [(19.48, 28.59), (19.48, 13.0), (22.0, 13.0), (22.0, 9.0), (25.5, 9.0)])
u2_fp = board.FindFootprintByReference('U2')
for pnum in ['19', '20', '21', '22']:
    p_pos = (from_nm(u2_fp.FindPadByNumber(pnum).GetPosition().x), from_nm(u2_fp.FindPadByNumber(pnum).GetPosition().y))
    add_track('VBAT_RAW', pcbnew.F_Cu, 0.35, (19.48, p_pos[1]), p_pos)

add_polyline('VBAT', pcbnew.F_Cu, 2.0, [(14.53, 28.59), (14.53, 31.14), (12.5, 31.14), (12.5, 37.87), (18.94, 37.87)])
add_polyline('VBAT', pcbnew.F_Cu, 2.5, [(14.53, 28.59), (14.53, 25.5), (18.5, 25.5)])
add_polyline('VBAT', pcbnew.F_Cu, 2.0, [(14.53, 30.5), (22.85, 30.5)])
add_track('VBAT', pcbnew.F_Cu, 1.5, (12.5, 36.5), (12.5, 40.5))
add_polyline('VBAT', pcbnew.F_Cu, 1.2, [(12.5, 36.5), (14.53, 36.5)])
add_polyline('VBAT', pcbnew.F_Cu, 1.2, [(12.5, 40.5), (14.53, 40.5)])
add_via('VBAT', (14.53, 23.5), size_mm=0.7, drill_mm=0.35)
add_track('VBAT', pcbnew.F_Cu, 1.2, (14.53, 25.5), (14.53, 23.5))
add_via('VBAT', (64.0, 11.5), size_mm=0.7, drill_mm=0.35)
add_polyline('VBAT', pcbnew.B_Cu, 1.2, [(14.53, 23.5), (64.0, 23.5), (64.0, 11.5)])
add_track('VBAT', pcbnew.F_Cu, 1.2, (64.0, 11.5), (64.0, 14.0))

# VBUS
for pnum in ['A4', 'B4', 'A9', 'B9']:
    p = jusb.FindPadByNumber(pnum)
    pos = (from_nm(p.GetPosition().x), from_nm(p.GetPosition().y))
    add_track('VBUS', pcbnew.F_Cu, 0.4, pos, (3.5, pos[1]))
add_polyline('VBUS', pcbnew.F_Cu, 1.5, [(3.5, 14.5), (3.5, 17.5), (3.5, 9.0), (11.0, 9.0), (14.5, 9.0)])
for pnum in ['12', '13']:
    p_pos = (from_nm(u2_fp.FindPadByNumber(pnum).GetPosition().x), from_nm(u2_fp.FindPadByNumber(pnum).GetPosition().y))
    add_track('VBUS', pcbnew.F_Cu, 0.4, (p_pos[0], 9.0), p_pos)

# 3.3V Logic Supply
add_polyline('VBAT_LOGIC', pcbnew.F_Cu, 0.8, [(60.0, 14.0), (59.53, 14.0), (59.53, 19.5)])
add_polyline('VBAT_LOGIC', pcbnew.F_Cu, 0.8, [(60.0, 14.0), (66.86, 14.0), (66.86, 18.45)])
add_polyline('VBAT_LOGIC', pcbnew.F_Cu, 0.8, [(66.86, 14.0), (70.2, 14.0), (70.2, 11.5)])

# LOG_SW routed cleanly on B.Cu to avoid C_BST and R_FB_LOG1
add_track('LOG_SW', pcbnew.F_Cu, 0.8, (66.86, 17.5), (67.5, 17.5))
add_via('LOG_SW', (67.5, 18.5), size_mm=0.7, drill_mm=0.35)
add_track('LOG_SW', pcbnew.F_Cu, 0.8, (67.5, 17.5), (67.5, 18.5))
add_polyline('LOG_SW', pcbnew.B_Cu, 0.8, [(67.5, 18.5), (67.5, 32.75)])
add_via('LOG_SW', (67.5, 32.75), size_mm=0.7, drill_mm=0.35)
add_track('LOG_SW', pcbnew.F_Cu, 0.8, (63.725, 24.5), (65.275, 24.5)) # C_BOOT_LOG connection
add_track('LOG_SW', pcbnew.F_Cu, 0.8, (65.275, 24.5), (67.5, 24.5))
add_via('LOG_SW', (67.5, 24.5), size_mm=0.7, drill_mm=0.35)

add_polyline('+3V3_PRE', pcbnew.F_Cu, 0.8, [(67.5, 28.25), (71.725, 28.25), (71.725, 34.06), (72.5, 34.06)])

# +3V3 clean on B.Cu
add_via('+3V3', (74.0, 31.94), size_mm=0.7, drill_mm=0.35)
add_track('+3V3', pcbnew.F_Cu, 0.6, (72.5, 31.94), (74.0, 31.94))
add_polyline('+3V3', pcbnew.B_Cu, 0.8, [(74.0, 31.94), (74.0, 38.0), (71.725, 38.0)])
add_via('+3V3', (71.725, 38.0), size_mm=0.7, drill_mm=0.35)
add_polyline('+3V3', pcbnew.F_Cu, 0.8, [(71.725, 36.5), (71.725, 39.0)])
add_via('+3V3', (36.5, 7.51), size_mm=0.7, drill_mm=0.35)
add_polyline('+3V3', pcbnew.B_Cu, 0.8, [(74.0, 31.94), (74.0, 7.51), (36.5, 7.51)])
add_polyline('+3V3', pcbnew.F_Cu, 0.8, [(33.5, 7.28), (36.5, 7.45), (36.5, 7.51), (39.25, 7.51)])

print("--> Refilling zones...")
zf = pcbnew.ZONE_FILLER(board)
zf.Fill(board.Zones())
board.Save(PCB_PATH)
print("--> Board saved! Step 1 & 2 complete.")
