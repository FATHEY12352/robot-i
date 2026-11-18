#!/usr/bin/env python3
"""
Full PCB Routing Synthesizer Test
"""
import pcbnew
import math
import heapq
import time
import numpy as np

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
add_via('GND', (8.7, 34.5), size_mm=0.6, drill_mm=0.3)
add_track('GND', pcbnew.F_Cu, 0.25, (8.7, 37.08), (8.7, 34.5))
add_polyline('GND', pcbnew.F_Cu, 0.4, [(8.7, 34.5), (26.5, 34.5)])
add_via('GND', (26.5, 34.5), size_mm=0.6, drill_mm=0.3)

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

# ----------------- CLEAN POWER CORRIDORS -----------------
add_track('+6V', pcbnew.F_Cu, 1.8, (20.0, 59.04), (80.0, 59.04))
add_track('+6V', pcbnew.F_Cu, 1.8, (65.0, 49.5), (65.0, 59.04))
add_polyline('V_SERVO', pcbnew.F_Cu, 1.5, [(58.54, 49.5), (58.54, 52.0), (63.0, 52.0), (63.0, 49.5), (64.0, 49.5)])
add_polyline('V_UBEC', pcbnew.B_Cu, 2.5, [(6.0, 42.0), (6.0, 46.5), (61.08, 46.5), (61.08, 49.5)])

add_polyline('+6V_BUCK', pcbnew.F_Cu, 3.0, [(41.48, 44.0), (46.3, 44.0), (46.3, 43.0)])
add_polyline('+6V_BUCK', pcbnew.F_Cu, 2.5, [(46.3, 44.0), (56.0, 44.0), (56.0, 49.5)])
add_track('+6V_BUCK', pcbnew.F_Cu, 1.0, (45.03, 49.5), (45.03, 44.0))
add_track('+6V_BUCK', pcbnew.F_Cu, 1.0, (49.73, 49.5), (49.73, 44.0))
add_via('+6V_BUCK', (41.48, 41.5), size_mm=0.6, drill_mm=0.3)
add_track('+6V_BUCK', pcbnew.F_Cu, 0.3, (41.48, 44.0), (41.48, 41.5))
add_via('+6V_BUCK', (24.68, 41.5), size_mm=0.6, drill_mm=0.3)
add_track('+6V_BUCK', pcbnew.B_Cu, 0.3, (41.48, 41.5), (24.68, 41.5))
add_polyline('+6V_BUCK', pcbnew.F_Cu, 0.3, [(24.68, 41.5), (24.675, 44.0)])
add_polyline('FB_SERVO', pcbnew.F_Cu, 0.25, [(24.062, 40.405), (26.325, 40.405), (26.325, 44.0), (24.675, 44.0), (24.675, 46.5)])

# SRV_PH
add_polyline('SRV_PH', pcbnew.F_Cu, 0.4, [(24.062, 36.595), (24.062, 34.5), (20.775, 34.5)])
add_track('SRV_PH', pcbnew.F_Cu, 0.5, (24.062, 36.595), (26.0, 36.595))
add_polyline('SRV_PH', pcbnew.F_Cu, 2.5, [(26.0, 36.595), (29.5, 36.595), (29.5, 44.0), (32.53, 44.0)])
add_via('SRV_PH', (29.5, 46.5), size_mm=0.8, drill_mm=0.4)
add_track('SRV_PH', pcbnew.F_Cu, 2.0, (29.5, 44.0), (29.5, 46.5))
add_via('SRV_PH', (17.5, 48.0), size_mm=0.8, drill_mm=0.4)
add_polyline('SRV_PH', pcbnew.B_Cu, 2.0, [(29.5, 46.5), (17.5, 46.5), (17.5, 48.0)])
add_track('SRV_PH', pcbnew.F_Cu, 2.0, (17.5, 48.0), (17.5, 49.9))

# VMOT
add_via('VMOT', (17.0, 25.5), size_mm=0.8, drill_mm=0.4)
add_track('VMOT', pcbnew.F_Cu, 1.5, (18.5, 25.5), (17.0, 25.5))
add_polyline('VMOT', pcbnew.B_Cu, 4.0, [(17.0, 25.5), (17.0, 50.0), (88.0, 50.0), (88.0, 7.5)])

add_via('VMOT', (86.0, 42.98), size_mm=0.7, drill_mm=0.35)
add_track('VMOT', pcbnew.B_Cu, 1.5, (88.0, 42.98), (86.0, 42.98))
add_track('VMOT', pcbnew.F_Cu, 0.6, (86.0, 42.98), (83.86, 42.98))

add_via('VMOT', (86.0, 18.98), size_mm=0.7, drill_mm=0.35)
add_track('VMOT', pcbnew.B_Cu, 1.5, (88.0, 18.98), (86.0, 18.98))
add_track('VMOT', pcbnew.F_Cu, 0.6, (86.0, 18.98), (83.86, 18.98))

add_via('VMOT', (79.7, 30.0), size_mm=0.8, drill_mm=0.4)
add_polyline('VMOT', pcbnew.B_Cu, 2.0, [(88.0, 30.0), (79.7, 30.0)])
add_polyline('VMOT', pcbnew.F_Cu, 1.2, [(79.7, 30.0), (79.7, 33.95), (76.0, 33.95)])
add_polyline('VMOT', pcbnew.F_Cu, 1.2, [(79.7, 33.95), (79.7, 37.28), (76.0, 37.28)])
add_polyline('VMOT', pcbnew.F_Cu, 0.8, [(85.5, 37.0), (81.78, 37.0)])
add_via('VMOT', (85.5, 37.0), size_mm=0.6, drill_mm=0.3)
add_track('VMOT', pcbnew.B_Cu, 0.8, (88.0, 37.0), (85.5, 37.0))

add_via('VMOT', (79.7, 7.5), size_mm=0.8, drill_mm=0.4)
add_polyline('VMOT', pcbnew.B_Cu, 2.0, [(88.0, 7.5), (79.7, 7.5)])
add_polyline('VMOT', pcbnew.F_Cu, 1.2, [(79.7, 7.5), (79.7, 11.95), (76.0, 11.95)])
add_polyline('VMOT', pcbnew.F_Cu, 1.2, [(79.7, 11.95), (79.7, 15.28), (76.0, 15.28)])
add_polyline('VMOT', pcbnew.F_Cu, 0.8, [(85.5, 13.5), (81.78, 13.5)])
add_via('VMOT', (85.5, 13.5), size_mm=0.6, drill_mm=0.3)
add_track('VMOT', pcbnew.B_Cu, 0.8, (88.0, 13.5), (85.5, 13.5))

# Motor Outputs
add_via('M1_OUT1', (77.0, 23.08), size_mm=0.8, drill_mm=0.4)
add_track('M1_OUT1', pcbnew.F_Cu, 0.5, (78.14, 20.275), (77.0, 23.08))
add_track('M1_OUT1', pcbnew.B_Cu, 3.0, (77.0, 23.08), (92.0, 23.08))

add_track('M1_OUT2', pcbnew.F_Cu, 0.5, (83.86, 19.625), (86.5, 19.625))
add_polyline('M1_OUT2', pcbnew.F_Cu, 3.0, [(86.5, 19.625), (87.5, 18.0), (92.0, 18.0)])

add_via('M2_OUT1', (77.0, 47.08), size_mm=0.8, drill_mm=0.4)
add_track('M2_OUT1', pcbnew.F_Cu, 0.5, (78.14, 44.275), (77.0, 47.08))
add_track('M2_OUT1', pcbnew.B_Cu, 3.0, (77.0, 47.08), (92.0, 47.08))

add_track('M2_OUT2', pcbnew.F_Cu, 0.5, (83.86, 43.625), (86.5, 43.625))
add_polyline('M2_OUT2', pcbnew.F_Cu, 3.0, [(86.5, 43.625), (87.5, 42.0), (92.0, 42.0)])

# Battery Supply
add_via('VBAT_RAW', (8.0, 32.0), size_mm=0.8, drill_mm=0.4)
add_track('VBAT_RAW', pcbnew.F_Cu, 2.5, (6.0, 32.0), (8.0, 32.0))
add_polyline('VBAT_RAW', pcbnew.B_Cu, 2.5, [(8.0, 32.0), (19.48, 32.0)])
add_via('VBAT_RAW', (19.48, 32.0), size_mm=0.8, drill_mm=0.4)
add_track('VBAT_RAW', pcbnew.F_Cu, 1.5, (19.48, 28.59), (19.48, 32.41))
add_polyline('VBAT_RAW', pcbnew.F_Cu, 1.5, [(19.48, 28.59), (19.48, 13.0), (22.0, 13.0), (22.0, 9.0), (25.5, 9.0)])
u2_fp = board.FindFootprintByReference('U2')
for pnum in ['19', '20', '21', '22']:
    p_pos = (from_nm(u2_fp.FindPadByNumber(pnum).GetPosition().x), from_nm(u2_fp.FindPadByNumber(pnum).GetPosition().y))
    add_track('VBAT_RAW', pcbnew.F_Cu, 0.35, (19.48, p_pos[1]), p_pos)

add_polyline('VBAT', pcbnew.F_Cu, 1.5, [(14.53, 28.59), (14.53, 31.14), (12.0, 31.14), (12.0, 37.87), (18.94, 37.87)])
add_polyline('VBAT', pcbnew.F_Cu, 2.0, [(14.53, 28.59), (14.53, 25.5), (18.5, 25.5)])
add_track('VBAT', pcbnew.F_Cu, 1.5, (12.0, 36.5), (12.0, 40.5))
add_polyline('VBAT', pcbnew.F_Cu, 1.2, [(12.0, 36.5), (14.53, 36.5)])
add_polyline('VBAT', pcbnew.F_Cu, 1.2, [(12.0, 40.5), (14.53, 40.5)])
add_via('VBAT', (12.0, 23.5), size_mm=0.7, drill_mm=0.35)
add_polyline('VBAT', pcbnew.F_Cu, 1.2, [(14.53, 25.5), (12.0, 25.5), (12.0, 23.5)])
add_via('VBAT', (64.0, 13.0), size_mm=0.7, drill_mm=0.35)
add_polyline('VBAT', pcbnew.B_Cu, 1.2, [(12.0, 23.5), (64.0, 23.5), (64.0, 13.0)])
add_track('VBAT', pcbnew.F_Cu, 1.2, (64.0, 13.0), (64.0, 14.0))

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

add_track('LOG_SW', pcbnew.F_Cu, 0.5, (66.862, 17.5), (64.0, 17.5))
add_via('LOG_SW', (64.0, 17.5), size_mm=0.7, drill_mm=0.35)
add_polyline('LOG_SW', pcbnew.B_Cu, 0.8, [(64.0, 17.5), (64.0, 32.75), (67.5, 32.75)])
add_via('LOG_SW', (67.5, 32.75), size_mm=0.7, drill_mm=0.35)
add_via('LOG_SW', (64.0, 24.5), size_mm=0.7, drill_mm=0.35)
add_track('LOG_SW', pcbnew.F_Cu, 0.5, (65.275, 24.5), (64.0, 24.5))

add_polyline('+3V3_PRE', pcbnew.F_Cu, 0.8, [(67.5, 28.25), (71.0, 28.25), (71.0, 34.06), (72.5, 34.06)])

add_via('+3V3', (74.0, 31.94), size_mm=0.7, drill_mm=0.35)
add_track('+3V3', pcbnew.F_Cu, 0.6, (72.5, 31.94), (74.0, 31.94))
add_polyline('+3V3', pcbnew.B_Cu, 0.8, [(74.0, 31.94), (74.0, 38.0), (71.725, 38.0)])
add_via('+3V3', (71.725, 38.0), size_mm=0.7, drill_mm=0.35)
add_polyline('+3V3', pcbnew.F_Cu, 0.8, [(71.725, 36.5), (71.725, 39.0)])
add_polyline('+3V3', pcbnew.B_Cu, 0.8, [(74.0, 31.94), (60.0, 31.94), (60.0, 7.51), (39.25, 7.51)])
add_via('+3V3', (39.25, 7.51), size_mm=0.7, drill_mm=0.35)
add_polyline('+3V3', pcbnew.F_Cu, 0.8, [(33.5, 7.28), (36.5, 7.45), (36.5, 7.51), (39.25, 7.51)])

# USB Diff Pair & CC
u1_fp = board.FindFootprintByReference('U1')
p_usb_dp = (from_nm(jusb.FindPadByNumber("A6").GetPosition().x), from_nm(jusb.FindPadByNumber("A6").GetPosition().y))
p_usb_dm = (from_nm(jusb.FindPadByNumber("A7").GetPosition().x), from_nm(jusb.FindPadByNumber("A7").GetPosition().y))
p_usb_b6 = (from_nm(jusb.FindPadByNumber("B6").GetPosition().x), from_nm(jusb.FindPadByNumber("B6").GetPosition().y))
p_usb_b7 = (from_nm(jusb.FindPadByNumber("B7").GetPosition().x), from_nm(jusb.FindPadByNumber("B7").GetPosition().y))
p_u1_dp = (from_nm(u1_fp.FindPadByNumber("14").GetPosition().x), from_nm(u1_fp.FindPadByNumber("14").GetPosition().y))
p_u1_dm = (from_nm(u1_fp.FindPadByNumber("13").GetPosition().x), from_nm(u1_fp.FindPadByNumber("13").GetPosition().y))

add_polyline("USB_D+", pcbnew.F_Cu, 0.25, [p_usb_b6, (-3.5, 15.25), (-3.5, 16.25), p_usb_dp])
add_polyline("USB_D-", pcbnew.F_Cu, 0.25, [p_usb_b7, (-1.0, 16.75), (-1.0, 15.75), p_usb_dm])
add_polyline("USB_D-", pcbnew.F_Cu, 0.4, [p_usb_dm, (3.0, 15.75), (5.0, 23.2), (32.0, 23.2), (35.0, 21.48), p_u1_dm])
add_polyline("USB_D+", pcbnew.F_Cu, 0.4, [p_usb_dp, (3.0, 16.25), (5.0, 23.8), (32.0, 23.8), (35.0, 22.75), p_u1_dp])

p_usb_a5 = (from_nm(jusb.FindPadByNumber("A5").GetPosition().x), from_nm(jusb.FindPadByNumber("A5").GetPosition().y))
p_usb_b5 = (from_nm(jusb.FindPadByNumber("B5").GetPosition().x), from_nm(jusb.FindPadByNumber("B5").GetPosition().y))
add_polyline("CC1", pcbnew.F_Cu, 0.25, [p_usb_a5, (3.0, 17.25)])
add_polyline("CC2", pcbnew.F_Cu, 0.25, [p_usb_b5, (3.0, 14.25)])

# ----------------- 3-PASS FAST ROUTER -----------------
class MasterRouter:
    def __init__(self, board, step=0.20):
        self.board = board
        self.step = step
        self.w_mm, self.h_mm = 98.0, 68.0
        self.nx = int(round(self.w_mm / self.step)) + 1
        self.ny = int(round(self.h_mm / self.step)) + 1
        
        self.blocked = np.zeros((2, self.ny, self.nx), dtype=bool)
        self.via_blocked = np.zeros((2, self.ny, self.nx), dtype=bool)
        self.net_grid = np.full((2, self.ny, self.nx), -1, dtype=np.int32)
        
        self.nets = {str(k): v for k, v in self.board.GetNetsByName().items()}
        self.vias = set()
        
        self._block_boundaries()
        self._block_antenna_keepout()
        self._populate_pad_obstacles()
        self._populate_track_obstacles()
        self._precompute_via_blocked()

    def _block_boundaries(self):
        m = int(round(1.0 / self.step))
        self.blocked[:, :m, :] = True
        self.blocked[:, -m:, :] = True
        self.blocked[:, :, :m] = True
        self.blocked[:, :, -m:] = True

    def _block_antenna_keepout(self):
        x1 = int(round(38.0 / self.step))
        x2 = int(round(58.0 / self.step))
        y2 = int(round(5.0 / self.step))
        self.blocked[:, :y2+1, x1:x2+1] = True

    def _populate_pad_obstacles(self):
        # Pass 1: Clearance
        for fp in self.board.GetFootprints():
            ref = fp.GetReference()
            for p in fp.Pads():
                pos = p.GetPosition()
                px, py = from_nm(pos.x), from_nm(pos.y)
                size = p.GetSize()
                sx, sy = from_nm(size.x), from_nm(size.y)
                is_th = (p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD)
                net_code = p.GetNetCode()
                
                is_fine_pitch = (ref in ['U1', 'U2', 'U3', 'U5', 'U6'])
                cl_x = 0.12 if is_fine_pitch and sx < 0.6 else 0.20
                cl_y = 0.12 if is_fine_pitch and sy < 0.6 else 0.20
                hw = (sx / 2.0) + cl_x
                hh = (sy / 2.0) + cl_y
                
                if px + hw < 0 or px - hw > self.w_mm or py + hh < 0 or py - hh > self.h_mm:
                    continue
                
                ix1 = max(0, min(self.nx - 1, int(math.floor((px - hw) / self.step))))
                ix2 = max(0, min(self.nx - 1, int(math.ceil((px + hw) / self.step))))
                iy1 = max(0, min(self.ny - 1, int(math.floor((py - hh) / self.step))))
                iy2 = max(0, min(self.ny - 1, int(math.ceil((py + hh) / self.step))))
                
                layers = [0, 1] if is_th else [0]
                for l in layers:
                    self.blocked[l, iy1:iy2+1, ix1:ix2+1] = True
                    for iy in range(iy1, iy2+1):
                        for ix in range(ix1, ix2+1):
                            cur = self.net_grid[l, iy, ix]
                            if cur == -1: self.net_grid[l, iy, ix] = net_code
                            elif cur != net_code: self.net_grid[l, iy, ix] = -2

        # Pass 2: Restore copper
        for fp in self.board.GetFootprints():
            for p in fp.Pads():
                pos = p.GetPosition()
                px, py = from_nm(pos.x), from_nm(pos.y)
                size = p.GetSize()
                sx, sy = from_nm(size.x), from_nm(size.y)
                is_th = (p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD)
                net_code = p.GetNetCode()
                hw, hh = sx / 2.0, sy / 2.0
                if px + hw < 0 or px - hw > self.w_mm or py + hh < 0 or py - hh > self.h_mm:
                    continue
                ix1 = max(0, min(self.nx - 1, int(math.floor((px - hw) / self.step))))
                ix2 = max(0, min(self.nx - 1, int(math.ceil((px + hw) / self.step))))
                iy1 = max(0, min(self.ny - 1, int(math.floor((py - hh) / self.step))))
                iy2 = max(0, min(self.ny - 1, int(math.ceil((py + hh) / self.step))))
                layers = [0, 1] if is_th else [0]
                for l in layers:
                    self.net_grid[l, iy1:iy2+1, ix1:ix2+1] = net_code
                    c_ix = max(0, min(self.nx - 1, int(round(px / self.step))))
                    c_iy = max(0, min(self.ny - 1, int(round(py / self.step))))
                    self.net_grid[l, c_iy, c_ix] = net_code

    def _populate_track_obstacles(self):
        for t in list(self.board.GetTracks()):
            l_idx = 0 if t.GetLayer() == pcbnew.F_Cu else 1
            net_code = t.GetNetCode()
            w = from_nm(t.GetWidth())
            rad = max(1, int(math.ceil((w / 2.0 + 0.20) / self.step)))
            if isinstance(t, pcbnew.PCB_VIA):
                p = t.GetPosition()
                ix, iy = self.pos_to_grid(from_nm(p.x), from_nm(p.y))
                self.mark_via_blocked(ix, iy, net_code, rad=3)
            else:
                p1, p2 = t.GetStart(), t.GetEnd()
                ix1, iy1 = self.pos_to_grid(from_nm(p1.x), from_nm(p1.y))
                ix2, iy2 = self.pos_to_grid(from_nm(p2.x), from_nm(p2.y))
                self.mark_track_blocked(l_idx, (ix1, iy1), (ix2, iy2), net_code, rad=rad)

    def _precompute_via_blocked(self, rad=2):
        for l in [0, 1]:
            for dy in range(-rad, rad+1):
                for dx in range(-rad, rad+1):
                    sy1, sy2 = max(0, dy), min(self.ny, self.ny + dy)
                    sx1, sx2 = max(0, dx), min(self.nx, self.nx + dx)
                    ty1, ty2 = max(0, -dy), min(self.ny, self.ny - dy)
                    tx1, tx2 = max(0, -dx), min(self.nx, self.nx - dx)
                    self.via_blocked[l, ty1:ty2, tx1:tx2] |= self.blocked[l, sy1:sy2, sx1:sx2]

    def pos_to_grid(self, x_mm, y_mm):
        ix = int(round(x_mm / self.step))
        iy = int(round(y_mm / self.step))
        return (max(0, min(self.nx - 1, ix)), max(0, min(self.ny - 1, iy)))

    def is_via_allowed(self, iy, ix, net_code):
        if self.via_blocked[0, iy, ix] or self.via_blocked[1, iy, ix]: return False
        for vx, vy in self.vias:
            if abs(ix - vx) <= 2 and abs(iy - vy) <= 2: return False
        return True

    def mark_track_blocked(self, layer, p1_grid, p2_grid, net_code, rad=1):
        x1, y1 = p1_grid
        x2, y2 = p2_grid
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        cx, cy = x1, y1
        while True:
            y_min, y_max = max(0, cy - rad), min(self.ny - 1, cy + rad)
            x_min, x_max = max(0, cx - rad), min(self.nx - 1, cx + rad)
            self.blocked[layer, y_min:y_max+1, x_min:x_max+1] = True
            for iy in range(y_min, y_max+1):
                for ix in range(x_min, x_max+1):
                    cur = self.net_grid[layer, iy, ix]
                    if cur == -1: self.net_grid[layer, iy, ix] = net_code
                    elif cur != net_code: self.net_grid[layer, iy, ix] = -2
            v_rad = rad + 2
            vy_min, vy_max = max(0, cy - v_rad), min(self.ny - 1, cy + v_rad)
            vx_min, vx_max = max(0, cx - v_rad), min(self.nx - 1, cx + v_rad)
            self.via_blocked[layer, vy_min:vy_max+1, vx_min:vx_max+1] = True
            if cx == x2 and cy == y2: break
            e2 = 2 * err
            if e2 > -dy: err -= dy; cx += sx
            if e2 < dx: err += dx; cy += sy

    def mark_via_blocked(self, ix, iy, net_code, rad=3):
        for l in (0, 1):
            y_min, y_max = max(0, iy - rad), min(self.ny - 1, iy + rad)
            x_min, x_max = max(0, ix - rad), min(self.nx - 1, ix + rad)
            self.blocked[l, y_min:y_max+1, x_min:x_max+1] = True
            self.via_blocked[l, y_min:y_max+1, x_min:x_max+1] = True
            self.net_grid[l, y_min:y_max+1, x_min:x_max+1] = net_code
        self.vias.add((ix, iy))

    def find_path(self, start_pos, target_pos, net_code, start_layer=0, target_layer=0):
        s_ix, s_iy = self.pos_to_grid(start_pos[0], start_pos[1])
        t_ix, t_iy = self.pos_to_grid(target_pos[0], target_pos[1])
        pq = []
        heapq.heappush(pq, (0.0, 0.0, start_layer, s_iy, s_ix))
        dist = {(start_layer, s_iy, s_ix): 0.0}
        came_from = {}
        closed_set = set()
        
        def h(l, iy, ix):
            return (abs(ix - t_ix) + abs(iy - t_iy)) * self.step + abs(l - target_layer) * 3.0

        target_reached = None
        moves = [(0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
        via_cost = 5.0
        
        while pq:
            f, c, l, iy, ix = heapq.heappop(pq)
            if (l, iy, ix) in closed_set: continue
            closed_set.add((l, iy, ix))
            if (l, iy, ix) == (target_layer, t_iy, t_ix):
                target_reached = (l, iy, ix)
                break
            for dl, diy, dix in moves:
                niy, nix = iy + diy, ix + dix
                if 0 <= niy < self.ny and 0 <= nix < self.nx:
                    if (l, niy, nix) in closed_set: continue
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
            nl = 1 - l
            if (nl, iy, ix) not in closed_set and self.is_via_allowed(iy, ix, net_code):
                nc = c + via_cost
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

    def find_multi_path(self, reached_cells, target_pos, net_code, target_layer=0):
        t_ix, t_iy = self.pos_to_grid(target_pos[0], target_pos[1])
        pq = []
        dist = {}
        came_from = {}
        closed_set = set()
        
        def h(l, iy, ix):
            return (abs(ix - t_ix) + abs(iy - t_iy)) * self.step + abs(l - target_layer) * 3.0

        for l, iy, ix in reached_cells:
            dist[(l, iy, ix)] = 0.0
            heapq.heappush(pq, (h(l, iy, ix), 0.0, l, iy, ix))
            
        target_reached = None
        moves = [(0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
        via_cost = 5.0
        
        while pq:
            f, c, l, iy, ix = heapq.heappop(pq)
            if (l, iy, ix) in closed_set: continue
            closed_set.add((l, iy, ix))
            if (l, iy, ix) == (target_layer, t_iy, t_ix):
                target_reached = (l, iy, ix)
                break
            for dl, diy, dix in moves:
                niy, nix = iy + diy, ix + dix
                if 0 <= niy < self.ny and 0 <= nix < self.nx:
                    if (l, niy, nix) in closed_set: continue
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
            nl = 1 - l
            if (nl, iy, ix) not in closed_set and self.is_via_allowed(iy, ix, net_code):
                nc = c + via_cost
                state = (nl, iy, ix)
                if nc < dist.get(state, float('inf')):
                    dist[state] = nc
                    nf = nc + h(nl, iy, ix)
                    came_from[state] = (l, iy, ix)
                    heapq.heappush(pq, (nf, nc, nl, iy, ix))
                    
        if not target_reached: return None
        path = []
        curr = target_reached
        while curr and curr in came_from:
            path.append(curr)
            curr = came_from[curr]
        path.append(curr)
        path.reverse()
        return path

    def compress_path(self, path):
        if not path or len(path) < 2: return [], []
        vias = []
        tracks = []
        curr_layer = path[0][0]
        curr_seg = [path[0]]
        for pt in path[1:]:
            l, iy, ix = pt
            if l != curr_layer:
                vias.append((round(curr_seg[-1][2] * self.step, 3), round(curr_seg[-1][1] * self.step, 3), curr_seg[-1][2], curr_seg[-1][1]))
                if len(curr_seg) >= 2: tracks.append((curr_layer, curr_seg))
                curr_layer = l
                curr_seg = [pt]
            else: curr_seg.append(pt)
        if len(curr_seg) >= 2: tracks.append((curr_layer, curr_seg))
            
        compressed = []
        for layer, seg in tracks:
            p_start = (round(seg[0][2] * self.step, 3), round(seg[0][1] * self.step, 3), seg[0][2], seg[0][1])
            p_prev = (round(seg[1][2] * self.step, 3), round(seg[1][1] * self.step, 3), seg[1][2], seg[1][1])
            dx, dy = p_prev[0] - p_start[0], p_prev[1] - p_start[1]
            for i in range(2, len(seg)):
                p_curr = (round(seg[i][2] * self.step, 3), round(seg[i][1] * self.step, 3), seg[i][2], seg[i][1])
                cur_dx, cur_dy = p_curr[0] - p_prev[0], p_curr[1] - p_prev[1]
                if (dx == 0 and cur_dx == 0) or (dy == 0 and cur_dy == 0): p_prev = p_curr
                else:
                    compressed.append((layer, p_start, p_prev))
                    p_start, p_prev, dx, dy = p_prev, p_curr, cur_dx, cur_dy
            compressed.append((layer, p_start, p_prev))
        return compressed, vias

    def commit_path(self, path, net, width_mm=0.25, p_start_mm=None, p_end_mm=None):
        tracks, vias = self.compress_path(path)
        net_code = net.GetNetCode()
        for vx_mm, vy_mm, vix, viy in vias:
            v = pcbnew.PCB_VIA(self.board)
            v.SetPosition(pcbnew.VECTOR2I(to_nm(vx_mm), to_nm(vy_mm)))
            v.SetWidth(to_nm(0.6))
            v.SetDrill(to_nm(0.3))
            v.SetNet(net)
            self.board.Add(v)
            self.mark_via_blocked(vix, viy, net_code, rad=3)
            
        rad_track = max(1, int(math.ceil((width_mm/2.0 + 0.20) / self.step)))
        for layer_idx, p_s, p_e in tracks:
            layer = pcbnew.F_Cu if layer_idx == 0 else pcbnew.B_Cu
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(pcbnew.VECTOR2I(to_nm(p_s[0]), to_nm(p_s[1])))
            t.SetEnd(pcbnew.VECTOR2I(to_nm(p_e[0]), to_nm(p_e[1])))
            t.SetWidth(to_nm(width_mm))
            t.SetLayer(layer)
            t.SetNet(net)
            self.board.Add(t)
            self.mark_track_blocked(layer_idx, (p_s[2], p_s[3]), (p_e[2], p_e[3]), net_code, rad=rad_track)

        if p_start_mm:
            f_mm = (round(path[0][2]*self.step, 3), round(path[0][1]*self.step, 3))
            l_start = pcbnew.F_Cu if path[0][0] == 0 else pcbnew.B_Cu
            if not (math.isclose(p_start_mm[0], f_mm[0], abs_tol=1e-3) and math.isclose(p_start_mm[1], f_mm[1], abs_tol=1e-3)):
                t1 = pcbnew.PCB_TRACK(self.board)
                t1.SetStart(pcbnew.VECTOR2I(to_nm(p_start_mm[0]), to_nm(p_start_mm[1])))
                t1.SetEnd(pcbnew.VECTOR2I(to_nm(f_mm[0]), to_nm(f_mm[1])))
                t1.SetWidth(to_nm(width_mm))
                t1.SetLayer(l_start)
                t1.SetNet(net)
                self.board.Add(t1)

        if p_end_mm:
            l_mm = (round(path[-1][2]*self.step, 3), round(path[-1][1]*self.step, 3))
            l_end = pcbnew.F_Cu if path[-1][0] == 0 else pcbnew.B_Cu
            if not (math.isclose(p_end_mm[0], l_mm[0], abs_tol=1e-3) and math.isclose(p_end_mm[1], l_mm[1], abs_tol=1e-3)):
                t2 = pcbnew.PCB_TRACK(self.board)
                t2.SetStart(pcbnew.VECTOR2I(to_nm(l_mm[0]), to_nm(l_mm[1])))
                t2.SetEnd(pcbnew.VECTOR2I(to_nm(p_end_mm[0]), to_nm(p_end_mm[1])))
                t2.SetWidth(to_nm(width_mm))
                t2.SetLayer(l_end)
                t2.SetNet(net)
                self.board.Add(t2)

print("--> Initializing MasterRouter...")
router = MasterRouter(board, step=0.20)

# All signal nets to route
nets_to_route = [
    # Dedicated Local Subsystems
    ('CPH1', 0.25), ('CPL1', 0.25), ('CPH2', 0.25), ('CPL2', 0.25),
    ('VCP1', 0.25), ('VCP2', 0.25), ('IPROPI1', 0.25), ('IPROPI2', 0.25),
    ('SRV_BOOT', 0.25), ('SRV_EN', 0.25), ('SRV_RT', 0.25),
    ('SRV_COMP', 0.25), ('COMP_NODE', 0.25),
    ('LOG_BOOT', 0.25), ('LOG_EN', 0.25), ('FB_3V3', 0.25),
    ('BST', 0.25), ('CHG_LX', 0.35), ('VSET', 0.25), ('ISET', 0.25), ('NTC', 0.25),
    ('CHG_STAT', 0.25), ('CHG_LED', 0.25), ('D_STAT_A', 0.25), ('D_CHG_A', 0.25),
    ('GATE_PROT', 0.25), ('VBATM', 0.25), ('BOOT', 0.25), ('ESP_EN', 0.25),
    ('CC1', 0.25), ('CC2', 0.25),
    # Actuator PWM
    ('SERVO1_PWM', 0.25), ('SRV1_PWM_OUT', 0.25),
    ('SERVO2_PWM', 0.25), ('SRV2_PWM_OUT', 0.25),
    ('SERVO3_PWM', 0.25), ('SRV3_PWM_OUT', 0.25),
    ('SERVO4_PWM', 0.25), ('SRV4_PWM_OUT', 0.25),
    ('SERVO5_PWM', 0.25), ('SRV5_PWM_OUT', 0.25),
    ('SERVO6_PWM', 0.25), ('SRV6_PWM_OUT', 0.25),
    # Motor Control
    ('M1_IN1', 0.25), ('M1_IN2', 0.25), ('M2_IN1', 0.25), ('M2_IN2', 0.25),
    ('M1_SLEEP', 0.25), ('M2_SLEEP', 0.25), ('M1_FAULT', 0.25), ('M2_FAULT', 0.25),
    # Encoders
    ('ENC1_A_RAW', 0.25), ('ENC1_B_RAW', 0.25), ('M1_ENC_A', 0.25), ('M1_ENC_B', 0.25),
    ('ENC2_A_RAW', 0.25), ('ENC2_B_RAW', 0.25), ('M2_ENC_A', 0.25), ('M2_ENC_B', 0.25),
    # Analog Feedback
    ('SERVO1_FB', 0.25), ('SRV1_FB_IN', 0.25),
    ('SERVO2_FB', 0.25), ('SRV2_FB_IN', 0.25),
    ('SERVO3_FB', 0.25), ('SRV3_FB_IN', 0.25),
    ('SERVO4_FB', 0.25), ('SRV4_FB_IN', 0.25),
    ('SERVO5_FB', 0.25), ('SRV5_FB_IN', 0.25),
    ('SERVO6_FB', 0.25), ('SRV6_FB_IN', 0.25),
    # Digital Buses
    ('SPI1_SCK', 0.25), ('SPI1_MOSI', 0.25), ('SPI1_MISO', 0.25), ('SPI1_CS', 0.25),
    ('SPI2_SCK', 0.25), ('SPI2_MOSI', 0.25), ('SPI2_MISO', 0.25), ('SPI2_CS', 0.25),
    ('I2C_SCL', 0.25), ('I2C_SDA', 0.25), ('IMU_INT', 0.25),
    ('UART0_RXD', 0.25), ('UART0_TXD', 0.25),
]

t0 = time.time()
routed_count = 0
failed_list = []

for netname, width in nets_to_route:
    net = nets[netname]
    pads = [p for fp in board.GetFootprints() for p in fp.Pads() if p.GetNetname() == netname]
    if len(pads) < 2: continue
    
    # Sort pads by MST (connect closest pairs first)
    coords = [(from_nm(p.GetPosition().x), from_nm(p.GetPosition().y), 0 if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD else 1) for p in pads]
    
    # Special CC stubs
    if netname == 'CC1':
        coords = [(3.0, 17.25, 0) if c[0] < 0 else c for c in coords]
    elif netname == 'CC2':
        coords = [(3.0, 14.25, 0) if c[0] < 0 else c for c in coords]
        
    # Find closest pair
    best_d = float('inf')
    best_pair = (0, 1)
    for i in range(len(coords)):
        for j in range(i+1, len(coords)):
            d = (coords[i][0] - coords[j][0])**2 + (coords[i][1] - coords[j][1])**2
            if d < best_d:
                best_d = d
                best_pair = (i, j)
                
    i0, i1 = best_pair
    p0, p1 = coords[i0], coords[i1]
    
    path = router.find_path((p0[0], p0[1]), (p1[0], p1[1]), net.GetNetCode(), start_layer=p0[2], target_layer=p1[2])
    if path:
        router.commit_path(path, net, width_mm=width, p_start_mm=(p0[0], p0[1]), p_end_mm=(p1[0], p1[1]))
        reached = set(path)
        connected = {i0, i1}
        
        # Connect remaining pads to the tree
        while len(connected) < len(coords):
            # Pick unconnected pad closest to any connected pad
            best_cand_d = float('inf')
            best_cand_idx = None
            for u in range(len(coords)):
                if u not in connected:
                    for c_idx in connected:
                        d = (coords[u][0] - coords[c_idx][0])**2 + (coords[u][1] - coords[c_idx][1])**2
                        if d < best_cand_d:
                            best_cand_d = d
                            best_cand_idx = u
            pu = coords[best_cand_idx]
            branch = router.find_multi_path(reached, (pu[0], pu[1]), net.GetNetCode(), target_layer=pu[2])
            if branch:
                router.commit_path(branch, net, width_mm=width, p_start_mm=None, p_end_mm=(pu[0], pu[1]))
                reached.update(branch)
                connected.add(best_cand_idx)
            else:
                print(f"  Warning: branch to pad {best_cand_idx} of {netname} failed")
                break
                
        routed_count += 1
        print(f"Routed {netname:15s} (width {width}mm)")
    else:
        print(f"FAILED to route {netname}")
        failed_list.append(netname)

t1 = time.time()
print(f"=== SYNTHESIS COMPLETE: Routed {routed_count}/{len(nets_to_route)} signal nets in {t1-t0:.2f}s ===")
if failed_list:
    print(f"Failed nets: {failed_list}")

print("--> Refilling all copper zones...")
zf = pcbnew.ZONE_FILLER(board)
zf.Fill(board.Zones())
board.Save(PCB_PATH)
print("--> Board saved to PCB_PATH!")
