#!/usr/bin/env python3
"""
route_perfect_pcb.py — Master 2-Layer Copper Routing Script
ESP32-S3 Robotic Controller PCB (V4)
KiCad 10.0.6 programmatic synthesis via pcbnew
"""

import sys
import os
import math
import pcbnew

PCB_PATH = r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb"

def to_nm(mm):
    return int(round(mm * 1e6))

def from_nm(nm):
    return nm / 1e6

class PcbRouter:
    def __init__(self, pcb_path=PCB_PATH):
        self.pcb_path = pcb_path
        self.board = pcbnew.LoadBoard(pcb_path)
        self.nets = {str(k): v for k, v in self.board.GetNetsByName().items()}
        print(f"Loaded board: {len(self.board.GetFootprints())} footprints, {len(self.nets)} nets")

    def get_pad(self, ref, num):
        fp = self.board.FindFootprintByReference(ref)
        if not fp:
            raise ValueError(f"Footprint {ref} not found")
        p = fp.FindPadByNumber(str(num))
        if not p:
            raise ValueError(f"Pad {ref}.{num} not found")
        return p

    def get_pad_pos(self, ref, num):
        p = self.get_pad(ref, num)
        pos = p.GetPosition()
        return (from_nm(pos.x), from_nm(pos.y))

    def add_track(self, net_name, layer, width_mm, p1, p2):
        net = self.nets.get(net_name)
        if not net:
            raise ValueError(f"Net {net_name} not found")
        if math.isclose(p1[0], p2[0], abs_tol=1e-5) and math.isclose(p1[1], p2[1], abs_tol=1e-5):
            return None
        t = pcbnew.PCB_TRACK(self.board)
        t.SetStart(pcbnew.VECTOR2I(to_nm(p1[0]), to_nm(p1[1])))
        t.SetEnd(pcbnew.VECTOR2I(to_nm(p2[0]), to_nm(p2[1])))
        t.SetWidth(to_nm(width_mm))
        t.SetLayer(layer)
        t.SetNet(net)
        self.board.Add(t)
        return t

    def add_polyline(self, net_name, layer, width_mm, pts):
        tracks = []
        for i in range(len(pts) - 1):
            tr = self.add_track(net_name, layer, width_mm, pts[i], pts[i+1])
            if tr:
                tracks.append(tr)
        return tracks

    def add_via(self, net_name, pos, size_mm=0.6, drill_mm=0.3):
        net = self.nets.get(net_name)
        if not net:
            raise ValueError(f"Net {net_name} not found")
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(pcbnew.VECTOR2I(to_nm(pos[0]), to_nm(pos[1])))
        v.SetWidth(to_nm(size_mm))
        v.SetDrill(to_nm(drill_mm))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(net)
        self.board.Add(v)
        return v

    def add_copper_zone(self, net_name, layer, pts, priority=0):
        net = self.nets.get(net_name)
        if not net:
            raise ValueError(f"Net {net_name} not found")
        z = pcbnew.ZONE(self.board)
        z.SetNet(net)
        lset = pcbnew.LSET()
        lset.AddLayer(layer)
        z.SetLayerSet(lset)
        poly = pcbnew.SHAPE_LINE_CHAIN()
        for x, y in pts:
            poly.Append(pcbnew.VECTOR2I(to_nm(x), to_nm(y)))
        poly.SetClosed(True)
        z.Outline().AddOutline(poly)
        z.SetThermalReliefGap(to_nm(0.25))
        z.SetThermalReliefSpokeWidth(to_nm(0.40))
        z.SetMinThickness(to_nm(0.20))
        z.SetAssignedPriority(priority)
        self.board.Add(z)
        return z

    def clear_existing_tracks(self):
        removed_tracks = 0
        removed_vias = 0
        u2_thermal_vias = {(15.0, 15.5), (16.0, 15.5), (15.0, 14.5), (16.0, 14.5)}
        for t in list(self.board.GetTracks()):
            if isinstance(t, pcbnew.PCB_VIA):
                pos = (round(from_nm(t.GetPosition().x), 2), round(from_nm(t.GetPosition().y), 2))
                if pos not in u2_thermal_vias:
                    self.board.Delete(t)
                    removed_vias += 1
            else:
                self.board.Delete(t)
                removed_tracks += 1
        print(f"Removed {removed_tracks} tracks and {removed_vias} non-thermal vias")

    def clear_copper_zones(self):
        removed = 0
        for z in list(self.board.Zones()):
            if not z.GetIsRuleArea():
                self.board.Delete(z)
                removed += 1
        print(f"Removed {removed} copper zones (preserved keepout rule areas)")

    def save(self):
        zf = pcbnew.ZONE_FILLER(self.board)
        zf.Fill(self.board.Zones())
        self.board.Save(self.pcb_path)
        print("Board saved and zones filled successfully!")

    # -------------------------------------------------------------------------
    # 1. Ground Architecture & Split Ground Return
    # -------------------------------------------------------------------------
    def setup_ground_zones(self):
        print("--> Setting up split ground planes on B.Cu...")
        # Distinct priority per zone to eliminate zones_intersect errors:
        # Priority 1: North Digital GND zone
        self.add_copper_zone("GND", pcbnew.B_Cu, [
            (26.2, 0.5), (73.8, 0.5), (73.8, 36.2), (26.2, 36.2)
        ], priority=1)

        # Priority 2: Vertical tie channel
        self.add_copper_zone("GND", pcbnew.B_Cu, [
            (26.2, 36.0), (28.5, 36.0), (28.5, 55.5), (26.2, 55.5)
        ], priority=2)

        # Priority 3: South Digital GND shielding corridor
        self.add_copper_zone("GND", pcbnew.B_Cu, [
            (0.5, 55.5), (97.5, 55.5), (97.5, 67.0), (0.5, 67.0)
        ], priority=3)

        # Priority 4: West Power PGND Zone
        self.add_copper_zone("PGND", pcbnew.B_Cu, [
            (0.5, 25.2), (4.0, 25.2), (4.0, 0.5), (26.0, 0.5), (26.0, 55.0), (0.5, 55.0)
        ], priority=4)

        # Priority 5: East Power PGND Zone
        self.add_copper_zone("PGND", pcbnew.B_Cu, [
            (28.7, 36.4), (74.0, 36.4), (74.0, 0.5), (97.5, 0.5), (97.5, 55.0), (28.7, 55.0)
        ], priority=5)

        # Priority 6: J_USB shield ground area
        self.add_copper_zone("GND", pcbnew.B_Cu, [
            (0.5, 8.0), (3.8, 8.0), (3.8, 25.0), (0.5, 25.0)
        ], priority=6)

    # -------------------------------------------------------------------------
    # 2. Star Ground Tie at NT1
    # -------------------------------------------------------------------------
    def route_star_ground(self):
        print("--> Routing Star Ground at NT1...")
        p_bat2 = self.get_pad_pos("J_BAT", "2")   # PGND (6.0, 37.08)
        p_nt1_2 = self.get_pad_pos("NT1", "2")   # PGND (7.70, 37.08)
        p_nt1_1 = self.get_pad_pos("NT1", "1")   # GND (8.70, 37.08)

        self.add_polyline("PGND", pcbnew.F_Cu, 0.35, [p_bat2, p_nt1_2])
        self.add_polyline("GND", pcbnew.F_Cu, 0.35, [p_nt1_1, (8.7, 35.5)])
        self.add_via("GND", (8.7, 35.5), size_mm=0.6, drill_mm=0.3)

    # -------------------------------------------------------------------------
    # 3. Ground Stitching & Thermal Vias
    # -------------------------------------------------------------------------
    def route_ground_ties(self):
        print("--> Tying ground pads and thermal vias...")
        # Tie U2 standalone thermal vias to U2 pad 25 (PGND)
        p_u2_25 = self.get_pad_pos("U2", "25")
        for vx, vy in [(15.0, 15.5), (16.0, 15.5), (15.0, 14.5), (16.0, 14.5)]:
            self.add_polyline("PGND", pcbnew.F_Cu, 0.3, [p_u2_25, (vx, vy)])

        # Connect U1 thermal pad (Pin 41) to GND
        p_u1_41 = self.get_pad_pos("U1", "41")
        self.add_via("GND", (47.0, 14.0), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("GND", pcbnew.F_Cu, 0.4, [p_u1_41, (47.0, 14.0)])

        # Connect U1 Pin 1 (GND) to GND plane via via at (37.5, 6.24)
        p_u1_1 = self.get_pad_pos("U1", "1")
        self.add_via("GND", (37.5, 6.24), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("GND", pcbnew.F_Cu, 0.3, [p_u1_1, (37.5, 6.24)])

        # Connect U1 Pin 40 (GND) to GND plane via via at (58.5, 6.24)
        p_u1_40 = self.get_pad_pos("U1", "40")
        self.add_via("GND", (58.5, 6.24), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("GND", pcbnew.F_Cu, 0.3, [p_u1_40, (58.5, 6.24)])

    # -------------------------------------------------------------------------
    # 4. High-Current Servo Power (+6V, +6V_BUCK, V_SERVO, V_UBEC, SRV_PH)
    # -------------------------------------------------------------------------
    def route_servo_power(self):
        print("--> Routing High-Current Servo Power Distribution...")
        p_srv1_2 = self.get_pad_pos("J_SERVO1", "2")
        p_srv6_2 = self.get_pad_pos("J_SERVO6", "2")
        p_nt3_2 = self.get_pad_pos("NT3", "2")  # (65.0, 49.5)
        rail_y = p_srv1_2[1]

        # 1.8mm width horizontal rail across Pin 2 of J_SERVO1..6
        self.add_polyline("+6V", pcbnew.F_Cu, 1.8, [
            (p_srv1_2[0], rail_y), (p_srv6_2[0], rail_y)
        ])
        self.add_polyline("+6V", pcbnew.F_Cu, 0.5, [p_nt3_2, (p_nt3_2[0], 51.0)])
        self.add_polyline("+6V", pcbnew.F_Cu, 1.8, [(p_nt3_2[0], 51.0), (p_nt3_2[0], rail_y)])

        # V_SERVO: NT3.1 (64.0, 49.5) to V_SERVO_SEL.2 (58.54, 49.5)
        p_nt3_1 = self.get_pad_pos("NT3", "1")
        p_vsel_2 = self.get_pad_pos("V_SERVO_SEL", "2")
        self.add_polyline("V_SERVO", pcbnew.F_Cu, 0.5, [p_vsel_2, (p_vsel_2[0], 47.5)])
        self.add_polyline("V_SERVO", pcbnew.F_Cu, 2.0, [
            (p_vsel_2[0], 47.5), (p_nt3_1[0], 47.5)
        ])
        self.add_polyline("V_SERVO", pcbnew.F_Cu, 0.5, [(p_nt3_1[0], 47.5), p_nt3_1])

        # V_UBEC: J_SERVO_EXT.1 (6.0, 51.0) to V_SERVO_SEL.3 (61.08, 49.5)
        p_jext_1 = self.get_pad_pos("J_SERVO_EXT", "1")
        p_vsel_3 = self.get_pad_pos("V_SERVO_SEL", "3")
        self.add_polyline("V_UBEC", pcbnew.F_Cu, 2.0, [
            p_jext_1, (12.0, 51.0), (12.0, 46.5), (p_vsel_3[0], 46.5), p_vsel_3
        ])

        # +6V_BUCK: L_SERVO.2 -> bulk caps -> V_SERVO_SEL.1
        p_l_srv_2 = self.get_pad_pos("L_SERVO", "2")
        p_csrv1_1 = self.get_pad_pos("C_SRV_BULK1", "1")
        p_csrv2_1 = self.get_pad_pos("C_SRV_BULK2", "1")
        p_csrv3_1 = self.get_pad_pos("C_SRV_BULK3", "1")
        p_vsel_1 = self.get_pad_pos("V_SERVO_SEL", "1")
        p_rfb_srv1_1 = self.get_pad_pos("R_FB_SRV1", "1")

        self.add_polyline("+6V_BUCK", pcbnew.F_Cu, 3.5, [p_l_srv_2, p_csrv1_1])
        self.add_polyline("+6V_BUCK", pcbnew.F_Cu, 2.5, [
            p_csrv1_1, (46.3, 46.5), (p_vsel_1[0], 46.5), p_vsel_1
        ])
        self.add_polyline("+6V_BUCK", pcbnew.F_Cu, 0.8, [(p_csrv2_1[0], 46.5), p_csrv2_1])
        self.add_polyline("+6V_BUCK", pcbnew.F_Cu, 0.8, [(p_csrv3_1[0], 46.5), p_csrv3_1])
        self.add_polyline("+6V_BUCK", pcbnew.F_Cu, 0.5, [p_l_srv_2, (p_rfb_srv1_1[0], p_l_srv_2[1]), p_rfb_srv1_1])

        # SRV_PH: U3.8 -> C_BOOT_SRV.2 -> L_SERVO.1 -> D_CATCH_SRV.1
        p_u3_8 = self.get_pad_pos("U3", "8")
        p_cboot_srv_2 = self.get_pad_pos("C_BOOT_SRV", "2")
        p_l_srv_1 = self.get_pad_pos("L_SERVO", "1")
        p_dcatch_1 = self.get_pad_pos("D_CATCH_SRV", "1")

        self.add_polyline("SRV_PH", pcbnew.F_Cu, 0.4, [p_u3_8, p_cboot_srv_2])
        self.add_via("SRV_PH", (25.5, 36.59), size_mm=0.8, drill_mm=0.4)
        self.add_polyline("SRV_PH", pcbnew.F_Cu, 0.5, [p_u3_8, (25.5, 36.59)])
        self.add_via("SRV_PH", (32.53, 41.5), size_mm=0.8, drill_mm=0.4)
        self.add_polyline("SRV_PH", pcbnew.F_Cu, 2.0, [(32.53, 41.5), p_l_srv_1])
        self.add_via("SRV_PH", (17.5, 48.0), size_mm=0.8, drill_mm=0.4)
        self.add_polyline("SRV_PH", pcbnew.F_Cu, 2.0, [(17.5, 48.0), p_dcatch_1])
        self.add_polyline("SRV_PH", pcbnew.B_Cu, 2.0, [
            (25.5, 36.59), (28.0, 41.5), (32.53, 41.5)
        ])
        self.add_polyline("SRV_PH", pcbnew.B_Cu, 2.0, [(28.0, 41.5), (17.5, 48.0)])

    # -------------------------------------------------------------------------
    # 5. High-Current Motor Power (VMOT, M1/M2_OUT)
    # -------------------------------------------------------------------------
    def route_motor_power(self):
        print("--> Routing Motor Power & Outputs...")
        p_nt2_2 = self.get_pad_pos("NT2", "2")  # (19.5, 25.5)

        # VMOT Trunk: NT2.2 drops to B.Cu at (19.5, 25.5), runs along Y=53.0 to X=79.7, rises to F.Cu
        self.add_via("VMOT", (19.5, 25.5), size_mm=0.8, drill_mm=0.4)
        self.add_polyline("VMOT", pcbnew.B_Cu, 2.5, [
            (19.5, 25.5), (14.0, 25.5), (14.0, 53.0), (79.7, 53.0)
        ])
        self.add_via("VMOT", (79.7, 53.0), size_mm=0.8, drill_mm=0.4)

        # F.Cu Distribution along X = 79.7mm
        p_cvm2_1 = self.get_pad_pos("C_VM2_1", "1")  # (79.7, 30.0)
        p_cvm2_2 = self.get_pad_pos("C_VM2_2", "1")  # (76.0, 33.95)
        p_cvm2_3 = self.get_pad_pos("C_VM2_3", "1")  # (76.0, 37.275)
        p_cvcp2_2 = self.get_pad_pos("C_VCP2", "2")  # (81.775, 37.0)
        p_u6_11 = self.get_pad_pos("U6", "11")      # (83.862, 42.975)

        self.add_polyline("VMOT", pcbnew.F_Cu, 3.0, [(79.7, 53.0), p_cvm2_1])
        self.add_polyline("VMOT", pcbnew.F_Cu, 1.5, [(79.7, p_cvm2_2[1]), p_cvm2_2])
        self.add_polyline("VMOT", pcbnew.F_Cu, 1.5, [(79.7, p_cvm2_3[1]), p_cvm2_3])
        self.add_polyline("VMOT", pcbnew.F_Cu, 1.0, [(79.7, p_cvcp2_2[1]), p_cvcp2_2])
        self.add_polyline("VMOT", pcbnew.F_Cu, 1.5, [(79.7, 42.975), (82.5, 42.975)])
        self.add_polyline("VMOT", pcbnew.F_Cu, 0.4, [(82.5, 42.975), p_u6_11])

        # Connect U5 (Motor 1)
        p_cvm1_1 = self.get_pad_pos("C_VM1_1", "1")  # (79.7, 7.5)
        p_cvm1_2 = self.get_pad_pos("C_VM1_2", "1")  # (76.0, 11.95)
        p_cvm1_3 = self.get_pad_pos("C_VM1_3", "1")  # (76.0, 15.275)
        p_cvcp1_2 = self.get_pad_pos("C_VCP1", "2")  # (81.775, 13.5)
        p_u5_11 = self.get_pad_pos("U5", "11")      # (83.862, 18.975)

        self.add_polyline("VMOT", pcbnew.F_Cu, 3.0, [p_cvm2_1, p_cvm1_1])
        self.add_polyline("VMOT", pcbnew.F_Cu, 1.5, [(79.7, p_cvm1_2[1]), p_cvm1_2])
        self.add_polyline("VMOT", pcbnew.F_Cu, 1.5, [(79.7, p_cvm1_3[1]), p_cvm1_3])
        self.add_polyline("VMOT", pcbnew.F_Cu, 1.0, [(79.7, p_cvcp1_2[1]), p_cvcp1_2])
        self.add_polyline("VMOT", pcbnew.F_Cu, 1.5, [(79.7, 18.975), (82.5, 18.975)])
        self.add_polyline("VMOT", pcbnew.F_Cu, 0.4, [(82.5, 18.975), p_u5_11])

        # Motor 1 Outputs (M1_OUT1 routes on B.Cu directly into J_MOT1.1)
        p_u5_8 = self.get_pad_pos("U5", "8")
        p_mot1_1 = self.get_pad_pos("J_MOT1", "1")
        self.add_via("M1_OUT1", (78.138, 22.5), size_mm=0.8, drill_mm=0.4)
        self.add_polyline("M1_OUT1", pcbnew.F_Cu, 0.4, [p_u5_8, (78.138, 22.5)])
        self.add_polyline("M1_OUT1", pcbnew.B_Cu, 3.0, [(78.138, 22.5), (92.0, 22.5), p_mot1_1])

        p_u5_10 = self.get_pad_pos("U5", "10")
        p_mot1_2 = self.get_pad_pos("J_MOT1", "2")
        self.add_polyline("M1_OUT2", pcbnew.F_Cu, 0.4, [p_u5_10, (86.0, 19.625)])
        self.add_polyline("M1_OUT2", pcbnew.F_Cu, 1.5, [(86.0, 19.625), (88.0, 18.0)])
        self.add_polyline("M1_OUT2", pcbnew.F_Cu, 3.0, [(88.0, 18.0), p_mot1_2])

        # Motor 2 Outputs (M2_OUT1 routes on B.Cu directly into J_MOT2.1)
        p_u6_8 = self.get_pad_pos("U6", "8")
        p_mot2_1 = self.get_pad_pos("J_MOT2", "1")
        self.add_via("M2_OUT1", (78.138, 46.5), size_mm=0.8, drill_mm=0.4)
        self.add_polyline("M2_OUT1", pcbnew.F_Cu, 0.4, [p_u6_8, (78.138, 46.5)])
        self.add_polyline("M2_OUT1", pcbnew.B_Cu, 3.0, [(78.138, 46.5), (92.0, 46.5), p_mot2_1])

        p_u6_10 = self.get_pad_pos("U6", "10")
        p_mot2_2 = self.get_pad_pos("J_MOT2", "2")
        self.add_polyline("M2_OUT2", pcbnew.F_Cu, 0.4, [p_u6_10, (86.0, 43.625)])
        self.add_polyline("M2_OUT2", pcbnew.F_Cu, 1.5, [(86.0, 43.625), (88.0, 42.0)])
        self.add_polyline("M2_OUT2", pcbnew.F_Cu, 3.0, [(88.0, 42.0), p_mot2_2])

    # -------------------------------------------------------------------------
    # 6. Battery, Charger & 3.3V Logic Supply
    # -------------------------------------------------------------------------
    def route_power_supplies(self):
        print("--> Routing Battery, Charger & 3.3V Logic...")
        # VBAT_RAW
        p_bat1 = self.get_pad_pos("J_BAT", "1")
        p_q1_d5 = self.get_pad_pos("Q1", "5")
        p_q1_d8 = self.get_pad_pos("Q1", "8")
        p_jbal_1 = self.get_pad_pos("J_BAL", "1")
        p_cchg_out1 = self.get_pad_pos("C_CHG_OUT1", "1")
        p_cchg_out2 = self.get_pad_pos("C_CHG_OUT2", "1")
        p_u2_21 = self.get_pad_pos("U2", "21")

        self.add_polyline("VBAT_RAW", pcbnew.F_Cu, 1.5, [p_q1_d5, p_q1_d8])
        self.add_polyline("VBAT_RAW", pcbnew.F_Cu, 2.5, [p_bat1, (19.48, p_bat1[1]), p_q1_d5])
        self.add_polyline("VBAT_RAW", pcbnew.F_Cu, 0.8, [p_bat1, (8.5, p_bat1[1]), p_jbal_1])
        self.add_polyline("VBAT_RAW", pcbnew.F_Cu, 1.5, [
            p_q1_d8, (19.48, 13.0), p_u2_21, p_cchg_out1, p_cchg_out2
        ])
        for u2_vbat in ["19", "20", "22"]:
            self.add_polyline("VBAT_RAW", pcbnew.F_Cu, 0.4, [p_u2_21, self.get_pad_pos("U2", u2_vbat)])

        # VBAT
        p_q1_s1 = self.get_pad_pos("Q1", "1")
        p_q1_s3 = self.get_pad_pos("Q1", "3")
        p_tvs1 = self.get_pad_pos("D_TVS1", "1")
        p_nt2_1 = self.get_pad_pos("NT2", "1")
        p_u3_2 = self.get_pad_pos("U3", "2")
        p_cvsrv1 = self.get_pad_pos("C_VIN_SRV1", "1")
        p_cvsrv2 = self.get_pad_pos("C_VIN_SRV2", "1")
        p_dz1_1 = self.get_pad_pos("D_Z1", "1")
        p_ren_srv_1 = self.get_pad_pos("R_EN_SRV", "1")
        p_diso_2 = self.get_pad_pos("D_ISO", "2")

        self.add_polyline("VBAT", pcbnew.F_Cu, 1.5, [p_q1_s1, p_q1_s3])
        self.add_polyline("VBAT", pcbnew.F_Cu, 2.5, [p_q1_s3, (p_tvs1[0], p_q1_s3[1]), p_tvs1])
        self.add_polyline("VBAT", pcbnew.F_Cu, 2.0, [(18.5, p_q1_s1[1]), p_nt2_1])
        self.add_polyline("VBAT", pcbnew.F_Cu, 2.0, [p_q1_s3, (18.94, p_q1_s3[1]), p_u3_2])
        self.add_polyline("VBAT", pcbnew.F_Cu, 1.0, [p_u3_2, p_cvsrv1, p_cvsrv2])
        self.add_polyline("VBAT", pcbnew.F_Cu, 0.4, [p_nt2_1, (9.95, 25.5), p_dz1_1])
        self.add_polyline("VBAT", pcbnew.F_Cu, 0.4, [p_tvs1, p_ren_srv_1])

        # Feed VBAT across B.Cu to logic SS14 diode D_ISO pin 2
        self.add_via("VBAT", (25.0, 28.0), size_mm=0.8, drill_mm=0.4)
        self.add_polyline("VBAT", pcbnew.F_Cu, 1.0, [p_tvs1, (25.0, 30.5), (25.0, 28.0)])
        self.add_via("VBAT", (64.0, 28.0), size_mm=0.8, drill_mm=0.4)
        self.add_polyline("VBAT", pcbnew.B_Cu, 1.0, [(25.0, 28.0), (64.0, 28.0)])
        self.add_polyline("VBAT", pcbnew.F_Cu, 1.0, [(64.0, 28.0), (64.0, 14.0), p_diso_2])

        # VBUS
        p_usb_a4 = self.get_pad_pos("J_USB", "A4")
        p_usb_b9 = self.get_pad_pos("J_USB", "B9")
        p_cvbus1 = self.get_pad_pos("C_VBUS1", "1")
        p_cvbus2 = self.get_pad_pos("C_VBUS2", "1")
        p_cchg_in1 = self.get_pad_pos("C_CHG_IN1", "1")
        p_cchg_in2 = self.get_pad_pos("C_CHG_IN2", "1")
        p_u2_12 = self.get_pad_pos("U2", "12")
        p_l_chg_2 = self.get_pad_pos("L_CHG", "2")
        p_rstat_1 = self.get_pad_pos("R_STAT", "1")
        p_rchg_1 = self.get_pad_pos("R_CHG", "1")
        p_rntc_b_1 = self.get_pad_pos("R_NTC_BIAS", "1")

        self.add_polyline("VBUS", pcbnew.F_Cu, 1.5, [p_usb_a4, (2.0, 18.45), (2.0, 17.0), p_cvbus1])
        self.add_polyline("VBUS", pcbnew.F_Cu, 1.5, [p_cvbus1, (2.0, 19.5), p_cvbus2])
        self.add_polyline("VBUS", pcbnew.F_Cu, 1.5, [
            p_cvbus1, (7.55, 9.0), p_cchg_in1, p_cchg_in2, (22.5, 9.0), p_l_chg_2
        ])
        self.add_polyline("VBUS", pcbnew.F_Cu, 0.8, [p_cchg_in2, (16.75, 9.0), p_u2_12])
        self.add_polyline("VBUS", pcbnew.F_Cu, 0.4, [p_u2_12, self.get_pad_pos("U2", "13")])
        self.add_polyline("VBUS", pcbnew.F_Cu, 0.4, [p_cvbus2, (2.0, 24.5), p_rchg_1, (2.0, 27.5), p_rstat_1])
        self.add_polyline("VBUS", pcbnew.F_Cu, 0.4, [(7.55, 22.0), p_rntc_b_1])

        # VBATM (routed on B.Cu directly into J_BAL.2 PTH pin)
        self.add_via("VBATM", (14.75, 12.0), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("VBATM", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U2", "23"), (14.75, 12.0)])
        self.add_polyline("VBATM", pcbnew.B_Cu, 0.25, [(14.75, 12.0), (6.0, 12.0), self.get_pad_pos("J_BAL", "2")])

        # 3.3V Logic Supply (VBAT_LOGIC, LOG_SW, +3V3_PRE, +3V3)
        p_diso_1 = self.get_pad_pos("D_ISO", "1")
        p_chold_1 = self.get_pad_pos("C_HOLD", "1")
        p_u4_3 = self.get_pad_pos("U4", "3")
        p_cvin_log1 = self.get_pad_pos("C_VIN_LOG1", "1")
        p_cvin_log2 = self.get_pad_pos("C_VIN_LOG2", "1")
        p_ren_log_1 = self.get_pad_pos("R_EN_LOG", "1")

        self.add_polyline("VBAT_LOGIC", pcbnew.F_Cu, 1.0, [
            p_diso_1, p_cvin_log1, p_cvin_log2, (66.86, 14.0), p_u4_3
        ])
        self.add_polyline("VBAT_LOGIC", pcbnew.F_Cu, 1.0, [p_diso_1, (59.52, 14.0), p_chold_1])
        self.add_polyline("VBAT_LOGIC", pcbnew.F_Cu, 0.4, [p_u4_3, p_ren_log_1])

        # LOG_SW
        p_u4_2 = self.get_pad_pos("U4", "2")
        p_cboot_log_2 = self.get_pad_pos("C_BOOT_LOG", "2")
        p_l_log_1 = self.get_pad_pos("L_LOGIC", "1")
        self.add_polyline("LOG_SW", pcbnew.F_Cu, 1.0, [
            p_u4_2, (65.28, 17.5), p_cboot_log_2, (65.28, 32.75), p_l_log_1
        ])

        # +3V3_PRE (runs strictly along X = 71.725mm into FB1.1)
        p_l_log_2 = self.get_pad_pos("L_LOGIC", "2")
        p_cpre1 = self.get_pad_pos("C_PRE_LOG1", "1")
        p_cpre2 = self.get_pad_pos("C_PRE_LOG2", "1")
        p_cpre3 = self.get_pad_pos("C_PRE_LOG3", "1")
        p_rfb_log1_1 = self.get_pad_pos("R_FB_LOG1", "1")
        p_fb1_1 = self.get_pad_pos("FB1", "1")

        self.add_polyline("+3V3_PRE", pcbnew.F_Cu, 1.0, [
            p_l_log_2, (71.725, 28.25), p_cpre2, p_cpre3, (71.725, 34.06), p_fb1_1
        ])
        self.add_polyline("+3V3_PRE", pcbnew.F_Cu, 0.8, [p_cpre2, p_cpre1, (71.725, 23.5), p_rfb_log1_1])

        # +3V3 Post-Filter
        p_fb1_2 = self.get_pad_pos("FB1", "2")
        p_c3v3_1 = self.get_pad_pos("C_3V3_1", "1")
        p_c3v3_2 = self.get_pad_pos("C_3V3_2", "1")
        self.add_polyline("+3V3", pcbnew.F_Cu, 1.0, [p_fb1_2, (71.55, 31.94), p_c3v3_1, p_c3v3_2])

        # Distribution Trunk on B.Cu at Y = 33.0mm
        self.add_via("+3V3", (71.55, 33.0), size_mm=0.8, drill_mm=0.4)
        self.add_polyline("+3V3", pcbnew.F_Cu, 1.0, [p_fb1_2, (71.55, 33.0)])
        self.add_via("+3V3", (36.50, 7.51), size_mm=0.8, drill_mm=0.4)
        self.add_polyline("+3V3", pcbnew.B_Cu, 1.0, [(71.55, 33.0), (36.50, 33.0), (36.50, 7.51)])

        # Connect U1.2 and MCU decoupling capacitors (approaching U1.2 horizontally from West)
        p_u1_2 = self.get_pad_pos("U1", "2")
        p_cmcu1 = self.get_pad_pos("C_MCU1", "1")
        p_cmcu2 = self.get_pad_pos("C_MCU2", "1")
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.8, [(36.50, 7.51), p_cmcu1, p_cmcu2])
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.8, [(36.50, 7.51), p_u1_2])

        # Connect Reset & Boot pullups
        p_ren_1 = self.get_pad_pos("R_EN", "1")
        p_rboot_1 = self.get_pad_pos("R_BOOT", "1")
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.4, [p_cmcu2, (29.06, 7.28), (23.68, 7.28), p_ren_1])
        self.add_via("+3V3", (65.67, 4.5), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("+3V3", pcbnew.B_Cu, 0.6, [(71.55, 33.0), (65.67, 33.0), (65.67, 4.5)])
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.4, [(65.67, 4.5), p_rboot_1])

        # Connect expansion headers (+3V3 on pin 1)
        p_ji2c_1 = self.get_pad_pos("J_I2C", "1")
        p_jimu_1 = self.get_pad_pos("J_IMU", "1")
        p_jspi1_1 = self.get_pad_pos("J_SPI1", "1")
        p_jspi2_1 = self.get_pad_pos("J_SPI2", "1")
        p_jenc1_1 = self.get_pad_pos("J_ENC1", "1")
        p_jenc2_1 = self.get_pad_pos("J_ENC2", "1")

        self.add_polyline("+3V3", pcbnew.F_Cu, 0.8, [(36.50, 33.0), (36.0, 33.0), p_ji2c_1])
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.8, [(36.0, 33.0), (33.0, 33.0), p_jspi2_1])
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.8, [(36.50, 33.0), (48.0, 33.0), p_jimu_1])
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.8, [(71.55, 33.0), (62.0, 33.0), p_jspi1_1])

        # J_ENC1 and J_ENC2 on B.Cu
        self.add_via("+3V3", (95.0, 26.0), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("+3V3", pcbnew.B_Cu, 0.8, [(71.55, 33.0), (95.0, 33.0), (95.0, 26.0)])
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.8, [(95.0, 26.0), p_jenc1_1])
        self.add_via("+3V3", (95.0, 52.0), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("+3V3", pcbnew.B_Cu, 0.8, [(95.0, 33.0), (95.0, 52.0)])
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.8, [(95.0, 52.0), p_jenc2_1])

        # Connect I2C pullups & Encoder 1 pullups
        p_rpuscl_1 = self.get_pad_pos("R_PU_SCL", "1")
        p_rpusda_1 = self.get_pad_pos("R_PU_SDA", "1")
        p_rpue1a_1 = self.get_pad_pos("R_PU_E1A", "1")
        p_rpue1b_1 = self.get_pad_pos("R_PU_E1B", "1")
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.4, [p_ji2c_1, p_rpusda_1, p_rpuscl_1, p_rpue1a_1])
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.4, [(48.0, 33.0), (58.17, 33.0), p_rpue1b_1])

        # Connect Encoder 2 pullups
        p_rpue2a_1 = self.get_pad_pos("R_PU_E2A", "1")
        p_rpue2b_1 = self.get_pad_pos("R_PU_E2B", "1")
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.4, [p_rboot_1, (66.17, 4.5), p_rpue2a_1, p_rpue2b_1])

        # Connect Motor driver logic supplies along X = 74.5mm (clear of VMOT at X = 79.7mm)
        p_u5_5 = self.get_pad_pos("U5", "5")
        p_rslp1_1 = self.get_pad_pos("R_SLP1", "1")
        p_rflt1_1 = self.get_pad_pos("R_FLT1", "1")
        p_u6_5 = self.get_pad_pos("U6", "5")
        p_rslp2_1 = self.get_pad_pos("R_SLP2", "1")
        p_rflt2_1 = self.get_pad_pos("R_FLT2", "1")

        self.add_polyline("+3V3", pcbnew.F_Cu, 0.6, [
            (71.55, 33.0), (74.5, 33.0), (74.5, 25.82), p_rflt1_1, (74.5, 22.32), p_rslp1_1, (74.5, 18.32), p_u5_5
        ])
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.6, [
            (74.5, 33.0), (74.5, 44.33), p_rslp2_1, (74.5, 47.83), p_rflt2_1
        ])
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.4, [(74.5, 42.33), p_u6_5])

        # Connect ADC Schottky clamp diodes D_CLAMP1..5 pin 2 along vertical X = 29.06 rail
        p_clamp1 = self.get_pad_pos("D_CLAMP1", "2")
        p_clamp5 = self.get_pad_pos("D_CLAMP5", "2")
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.4, [(29.06, 7.28), p_clamp1, p_clamp5])
        p_clamp6 = self.get_pad_pos("D_CLAMP6", "2")
        self.add_polyline("+3V3", pcbnew.F_Cu, 0.4, [p_rpue1b_1, p_clamp6])

    # -------------------------------------------------------------------------
    # 7. High-Speed USB D+/D- Differential Pair
    # -------------------------------------------------------------------------
    def route_usb_diff_pair(self):
        print("--> Routing High-Speed USB D+/D- Differential Pair...")
        p_usb_dp = self.get_pad_pos("J_USB", "A6")  # (-2.04, 16.25)
        p_usb_dm = self.get_pad_pos("J_USB", "A7")  # (-2.04, 15.75)
        p_u1_dp = self.get_pad_pos("U1", "14")      # (39.25, 22.75)
        p_u1_dm = self.get_pad_pos("U1", "13")      # (39.25, 21.48)

        # Connect B6 to A6 around West side, B7 to A7 around East side
        p_usb_b6 = self.get_pad_pos("J_USB", "B6")  # (-2.04, 15.25)
        p_usb_b7 = self.get_pad_pos("J_USB", "B7")  # (-2.04, 16.75)
        self.add_polyline("USB_D+", pcbnew.F_Cu, 0.25, [p_usb_b6, (-3.5, 15.25), (-3.5, 16.25), p_usb_dp])
        self.add_polyline("USB_D-", pcbnew.F_Cu, 0.25, [p_usb_b7, (-1.0, 16.75), (-1.0, 15.75), p_usb_dm])

        # Differential pair corridor along clean GND (0.40mm width, 0.20mm spacing)
        # Both run completely parallel without crossing
        pts_dm = [p_usb_dm, (3.0, 15.75), (7.0, 21.48), p_u1_dm]
        pts_dp = [p_usb_dp, (3.0, 16.25), (7.0, 22.75), p_u1_dp]
        self.add_polyline("USB_D-", pcbnew.F_Cu, 0.4, pts_dm)
        self.add_polyline("USB_D+", pcbnew.F_Cu, 0.4, pts_dp)

    # -------------------------------------------------------------------------
    # 8. 6x Analog Feedback Channels
    # -------------------------------------------------------------------------
    def route_analog_feedback(self):
        print("--> Routing 6x Analog Feedback Channels & Noise Isolation...")
        adc_pins = ["4", "5", "6", "7", "12", "17"]
        bcu_y_tracks = [64.8, 65.2, 65.6, 66.0, 66.4, 66.8]
        bcu_x_tracks = [27.6, 28.4, 29.2, 30.0, 35.77, 46.17]

        for s in range(1, 7):
            fb_net = f"SERVO{s}_FB"
            in_net = f"SRV{s}_FB_IN"
            p_srv_4 = self.get_pad_pos(f"J_SERVO{s}", "4")
            p_rsfb_1 = self.get_pad_pos(f"R_SFB{s}", "1")
            p_rsfb_2 = self.get_pad_pos(f"R_SFB{s}", "2")
            p_cfb_1 = self.get_pad_pos(f"C_FB{s}", "1")
            p_clamp_3 = self.get_pad_pos(f"D_CLAMP{s}", "3")
            p_u1_adc = self.get_pad_pos("U1", adc_pins[s-1])

            via_y = bcu_y_tracks[s-1]
            via_x = p_srv_4[0]
            esc_x = bcu_x_tracks[s-1]

            self.add_polyline(in_net, pcbnew.F_Cu, 0.25, [p_srv_4, (via_x, via_y)])
            self.add_via(in_net, (via_x, via_y), size_mm=0.6, drill_mm=0.3)

            if s in [1, 2, 3, 4]:
                self.add_polyline(in_net, pcbnew.B_Cu, 0.25, [
                    (via_x, via_y), (esc_x, via_y), (esc_x, p_rsfb_1[1])
                ])
                self.add_via(in_net, (esc_x, p_rsfb_1[1]), size_mm=0.6, drill_mm=0.3)
                self.add_polyline(in_net, pcbnew.F_Cu, 0.25, [(esc_x, p_rsfb_1[1]), p_rsfb_1])
            else:
                self.add_polyline(in_net, pcbnew.B_Cu, 0.25, [
                    (via_x, via_y), (esc_x, via_y)
                ])
                self.add_via(in_net, (esc_x, via_y), size_mm=0.6, drill_mm=0.3)
                self.add_polyline(in_net, pcbnew.F_Cu, 0.25, [(esc_x, via_y), (esc_x, p_rsfb_1[1]), p_rsfb_1])

            self.add_polyline(fb_net, pcbnew.F_Cu, 0.25, [p_rsfb_2, p_cfb_1, p_u1_adc])
            self.add_polyline(fb_net, pcbnew.F_Cu, 0.25, [p_rsfb_2, p_clamp_3])

    # -------------------------------------------------------------------------
    # 9. Actuator Signals, PWM & Motor Inputs
    # -------------------------------------------------------------------------
    def route_actuator_signals(self):
        print("--> Routing Actuator Signals, PWM & Encoders...")
        # 6x Servo PWM
        # Series damping resistor R_PWM connects to J_SERVO.3 by jogging around the header pins
        pwm_configs = [
            ("15", 41.02, 24.8, 19.17),
            ("16", 42.28, 24.8, 31.17),
            ("28", 58.5,  21.48, 43.17),
            ("29", 59.5,  20.21, 55.17),
            ("30", 60.5,  18.94, 67.17),
            ("31", 61.5,  17.67, 79.17)
        ]

        for s in range(1, 7):
            pwm_net = f"SERVO{s}_PWM"
            out_net = f"SRV{s}_PWM_OUT"
            pin_num, vx, vy, x_col = pwm_configs[s-1]
            p_u1 = self.get_pad_pos("U1", pin_num)
            p_rpwm_1 = self.get_pad_pos(f"R_PWM{s}", "1")
            p_rpwm_2 = self.get_pad_pos(f"R_PWM{s}", "2")
            p_jsrv_3 = self.get_pad_pos(f"J_SERVO{s}", "3")

            # Jog 1.5mm to the West around header pins 1 & 2 to reach pin 3
            self.add_polyline(out_net, pcbnew.F_Cu, 0.3, [
                p_rpwm_2, (p_jsrv_3[0] - 1.5, p_rpwm_2[1]),
                (p_jsrv_3[0] - 1.5, p_jsrv_3[1]), p_jsrv_3
            ])

            via_u1 = (vx, vy)
            self.add_via(pwm_net, via_u1, size_mm=0.6, drill_mm=0.3)
            self.add_polyline(pwm_net, pcbnew.F_Cu, 0.25, [p_u1, via_u1])

            via_rpwm = (x_col, 51.5)
            self.add_via(pwm_net, via_rpwm, size_mm=0.6, drill_mm=0.3)
            self.add_polyline(pwm_net, pcbnew.B_Cu, 0.25, [via_u1, (x_col, vy), via_rpwm])
            self.add_polyline(pwm_net, pcbnew.F_Cu, 0.25, [via_rpwm, p_rpwm_1])

        # Dual Motor Driver Inputs (vias dropped at Y = 24.8, avoiding R_SFB6/C_FB6)
        motor_inputs = [
            ("M1_IN1", "22", "U5", "1", 15.725),
            ("M1_IN2", "24", "U5", "2", 16.375),
            ("M2_IN1", "25", "U6", "1", 39.725),
            ("M2_IN2", "26", "U6", "2", 40.375),
        ]
        for net_name, u1_pin, u_ref, u_pin, uy in motor_inputs:
            p_u1 = self.get_pad_pos("U1", u1_pin)
            p_u_in = self.get_pad_pos(u_ref, u_pin)
            via_u1 = (p_u1[0], 24.8)
            via_u = (74.5, uy)
            self.add_via(net_name, via_u1, size_mm=0.6, drill_mm=0.3)
            self.add_polyline(net_name, pcbnew.F_Cu, 0.25, [p_u1, via_u1])
            self.add_via(net_name, via_u, size_mm=0.6, drill_mm=0.3)
            self.add_polyline(net_name, pcbnew.B_Cu, 0.25, [via_u1, (p_u1[0], uy), via_u])
            self.add_polyline(net_name, pcbnew.F_Cu, 0.25, [via_u, p_u_in])

        # Internal motor driver pins
        self.add_polyline("M1_FAULT", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U5", "4"), self.get_pad_pos("R_FLT1", "2")])
        self.add_polyline("M1_SLEEP", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U5", "3"), self.get_pad_pos("R_SLP1", "2")])
        self.add_polyline("IPROPI1", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U5", "6"), self.get_pad_pos("R_PROP1", "1")])
        self.add_polyline("VCP1", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U5", "12"), self.get_pad_pos("C_VCP1", "1")])
        self.add_polyline("CPH1", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U5", "13"), self.get_pad_pos("C_FLY1", "1")])
        self.add_polyline("CPL1", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U5", "14"), self.get_pad_pos("C_FLY1", "2")])

        self.add_polyline("M2_FAULT", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U6", "4"), self.get_pad_pos("R_FLT2", "2")])
        self.add_polyline("M2_SLEEP", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U6", "3"), self.get_pad_pos("R_SLP2", "2")])
        self.add_polyline("IPROPI2", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U6", "6"), self.get_pad_pos("R_PROP2", "1")])
        self.add_polyline("VCP2", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U6", "12"), self.get_pad_pos("C_VCP2", "1")])
        self.add_polyline("CPH2", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U6", "13"), self.get_pad_pos("C_FLY2", "1")])
        self.add_polyline("CPL2", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U6", "14"), self.get_pad_pos("C_FLY2", "2")])

        # Dual Quadrature Encoders
        p_jenc1_3 = self.get_pad_pos("J_ENC1", "3")
        p_rpue1a_2 = self.get_pad_pos("R_PU_E1A", "2")
        p_rflte1a_1 = self.get_pad_pos("R_FLT_E1A", "1")
        p_rflte1a_2 = self.get_pad_pos("R_FLT_E1A", "2")
        p_cflte1a_1 = self.get_pad_pos("C_FLT_E1A", "1")
        p_u1_11 = self.get_pad_pos("U1", "11")

        self.add_via("ENC1_A_RAW", (91.0, p_jenc1_3[1]), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("ENC1_A_RAW", pcbnew.F_Cu, 0.25, [p_jenc1_3, (91.0, p_jenc1_3[1])])
        self.add_via("ENC1_A_RAW", (36.5, 33.0), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("ENC1_A_RAW", pcbnew.B_Cu, 0.25, [(91.0, p_jenc1_3[1]), (36.5, p_jenc1_3[1]), (36.5, 33.0)])
        self.add_polyline("ENC1_A_RAW", pcbnew.F_Cu, 0.25, [(36.5, 33.0), p_rflte1a_1, p_rpue1a_2])
        self.add_polyline("M1_ENC_A", pcbnew.F_Cu, 0.25, [p_rflte1a_2, p_cflte1a_1, p_u1_11])

        p_jenc1_4 = self.get_pad_pos("J_ENC1", "4")
        p_rpue1b_2 = self.get_pad_pos("R_PU_E1B", "2")
        p_rflte1b_1 = self.get_pad_pos("R_FLT_E1B", "1")
        p_rflte1b_2 = self.get_pad_pos("R_FLT_E1B", "2")
        p_cflte1b_1 = self.get_pad_pos("C_FLT_E1B", "1")
        p_u1_23 = self.get_pad_pos("U1", "23")

        self.add_via("ENC1_B_RAW", (91.0, p_jenc1_4[1]), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("ENC1_B_RAW", pcbnew.F_Cu, 0.25, [p_jenc1_4, (91.0, p_jenc1_4[1])])
        self.add_via("ENC1_B_RAW", (54.67, 33.0), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("ENC1_B_RAW", pcbnew.B_Cu, 0.25, [(91.0, p_jenc1_4[1]), (54.67, p_jenc1_4[1]), (54.67, 33.0)])
        self.add_polyline("ENC1_B_RAW", pcbnew.F_Cu, 0.25, [(54.67, 33.0), p_rflte1b_1, p_rpue1b_2])
        self.add_polyline("M1_ENC_B", pcbnew.F_Cu, 0.25, [p_rflte1b_2, p_cflte1b_1, p_u1_23])

        p_jenc2_3 = self.get_pad_pos("J_ENC2", "3")
        p_rpue2a_2 = self.get_pad_pos("R_PU_E2A", "2")
        p_rflte2a_1 = self.get_pad_pos("R_FLT_E2A", "1")
        p_rflte2a_2 = self.get_pad_pos("R_FLT_E2A", "2")
        p_cflte2a_1 = self.get_pad_pos("C_FLT_E2A", "1")
        p_u1_38 = self.get_pad_pos("U1", "38")

        self.add_via("ENC2_A_RAW", (89.92, 51.5), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("ENC2_A_RAW", pcbnew.F_Cu, 0.25, [p_jenc2_3, (89.92, 51.5)])
        self.add_via("ENC2_A_RAW", (59.17, 8.5), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("ENC2_A_RAW", pcbnew.B_Cu, 0.25, [(89.92, 51.5), (89.92, 8.5), (59.17, 8.5)])
        self.add_polyline("ENC2_A_RAW", pcbnew.F_Cu, 0.25, [(59.17, 8.5), p_rflte2a_1, p_rpue2a_2])
        self.add_polyline("M2_ENC_A", pcbnew.F_Cu, 0.25, [p_rflte2a_2, p_cflte2a_1, p_u1_38])

        p_jenc2_4 = self.get_pad_pos("J_ENC2", "4")
        p_rpue2b_2 = self.get_pad_pos("R_PU_E2B", "2")
        p_rflte2b_1 = self.get_pad_pos("R_FLT_E2B", "1")
        p_rflte2b_2 = self.get_pad_pos("R_FLT_E2B", "2")
        p_cflte2b_1 = self.get_pad_pos("C_FLT_E2B", "1")
        p_u1_39 = self.get_pad_pos("U1", "39")

        self.add_via("ENC2_B_RAW", (87.38, 51.5), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("ENC2_B_RAW", pcbnew.F_Cu, 0.25, [p_jenc2_4, (87.38, 51.5)])
        self.add_via("ENC2_B_RAW", (59.17, 11.0), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("ENC2_B_RAW", pcbnew.B_Cu, 0.25, [(87.38, 51.5), (87.38, 11.0), (59.17, 11.0)])
        self.add_polyline("ENC2_B_RAW", pcbnew.F_Cu, 0.25, [(59.17, 11.0), p_rflte2b_1, p_rpue2b_2])
        self.add_polyline("M2_ENC_B", pcbnew.F_Cu, 0.25, [p_rflte2b_2, p_cflte2b_1, p_u1_39])

    # -------------------------------------------------------------------------
    # 10. Communication Buses (SPI1, SPI2, I2C, IMU, UART0)
    # -------------------------------------------------------------------------
    def route_communication_buses(self):
        print("--> Routing SPI1, SPI2, I2C, IMU, UART0 Buses...")
        # SPI1 (vias at Y = 24.8, avoiding R_SFB6/C_FB6)
        spi1_signals = [
            ("SPI1_SCK",  "20", "3", 38.08),
            ("SPI1_MOSI", "19", "4", 40.62),
            ("SPI1_MISO", "21", "5", 43.16),
            ("SPI1_CS",   "18", "6", 45.70),
        ]
        for net_name, u1_pin, j_pin, jy in spi1_signals:
            p_u1 = self.get_pad_pos("U1", u1_pin)
            p_j = self.get_pad_pos("J_SPI1", j_pin)
            via_pos = (p_u1[0], 24.8)
            self.add_via(net_name, via_pos, size_mm=0.6, drill_mm=0.3)
            self.add_polyline(net_name, pcbnew.F_Cu, 0.25, [p_u1, via_pos])
            self.add_polyline(net_name, pcbnew.B_Cu, 0.25, [via_pos, (p_u1[0], jy), (p_j[0], jy), p_j])

        # SPI2
        spi2_signals = [
            ("SPI2_SCK",  "32", "3", 57.8, 16.40, 38.08),
            ("SPI2_MISO", "33", "5", 58.6, 15.13, 43.16),
            ("SPI2_MOSI", "34", "4", 59.4, 13.86, 40.62),
            ("SPI2_CS",   "35", "6", 60.2, 12.59, 45.70),
        ]
        for net_name, u1_pin, j_pin, vx, uy, jx in spi2_signals:
            p_u1 = self.get_pad_pos("U1", u1_pin)
            p_j = self.get_pad_pos("J_SPI2", j_pin)
            via_pos = (vx, uy)
            self.add_via(net_name, via_pos, size_mm=0.6, drill_mm=0.3)
            self.add_polyline(net_name, pcbnew.F_Cu, 0.25, [p_u1, via_pos])
            self.add_polyline(net_name, pcbnew.B_Cu, 0.25, [via_pos, (jx, uy), p_j])

        # I2C
        p_u1_scl = self.get_pad_pos("U1", "8")
        p_rpuscl_2 = self.get_pad_pos("R_PU_SCL", "2")
        p_ji2c_3 = self.get_pad_pos("J_I2C", "3")
        p_jimu_3 = self.get_pad_pos("J_IMU", "3")
        self.add_polyline("I2C_SCL", pcbnew.F_Cu, 0.25, [p_u1_scl, p_rpuscl_2, p_ji2c_3, p_jimu_3])

        p_u1_sda = self.get_pad_pos("U1", "9")
        p_rpusda_2 = self.get_pad_pos("R_PU_SDA", "2")
        p_ji2c_4 = self.get_pad_pos("J_I2C", "4")
        p_jimu_4 = self.get_pad_pos("J_IMU", "4")
        self.add_polyline("I2C_SDA", pcbnew.F_Cu, 0.25, [p_u1_sda, p_rpusda_2, p_ji2c_4, p_jimu_4])

        # IMU INT
        p_u1_imu = self.get_pad_pos("U1", "10")
        p_jimu_5 = self.get_pad_pos("J_IMU", "5")
        self.add_polyline("IMU_INT", pcbnew.F_Cu, 0.25, [p_u1_imu, (p_u1_imu[0], 29.5), (p_jimu_5[0], 29.5), p_jimu_5])

        # UART0 Debug (routes East of X=58.5, avoiding keepout and SW_BOOT)
        p_u1_txd = self.get_pad_pos("U1", "37")
        p_juart_1 = self.get_pad_pos("J_UART", "1")
        self.add_polyline("UART0_TXD", pcbnew.F_Cu, 0.25, [
            p_u1_txd, (59.0, p_u1_txd[1]), (59.0, 3.5), p_juart_1
        ])

        p_u1_rxd = self.get_pad_pos("U1", "36")
        p_juart_2 = self.get_pad_pos("J_UART", "2")
        self.add_via("UART0_RXD", (59.0, p_u1_rxd[1]), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("UART0_RXD", pcbnew.F_Cu, 0.25, [p_u1_rxd, (59.0, p_u1_rxd[1])])
        self.add_polyline("UART0_RXD", pcbnew.B_Cu, 0.25, [(59.0, p_u1_rxd[1]), (72.0, p_u1_rxd[1]), p_juart_2])

    # -------------------------------------------------------------------------
    # 11. Reset, Boot & Peripherals
    # -------------------------------------------------------------------------
    def route_peripherals(self):
        print("--> Routing Reset, Boot & Peripheral Nodes...")
        # ESP_EN: U1.3 -> C_EN.1 -> R_EN.2 -> SW_EN.1
        p_u1_en = self.get_pad_pos("U1", "3")
        p_cen_1 = self.get_pad_pos("C_EN", "1")
        p_ren_2 = self.get_pad_pos("R_EN", "2")
        p_swen_1 = self.get_pad_pos("SW_EN", "1")
        self.add_polyline("ESP_EN", pcbnew.F_Cu, 0.25, [p_u1_en, (37.5, p_u1_en[1]), (37.5, 5.0), p_cen_1, p_ren_2, p_swen_1])

        # BOOT: U1.27 -> R_BOOT.2 -> SW_BOOT.1 (routed on B.Cu)
        p_u1_boot = self.get_pad_pos("U1", "27")
        p_rboot_2 = self.get_pad_pos("R_BOOT", "2")
        p_swboot_1 = self.get_pad_pos("SW_BOOT", "1")
        self.add_via("BOOT", (58.0, p_u1_boot[1]), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("BOOT", pcbnew.F_Cu, 0.25, [p_u1_boot, (58.0, p_u1_boot[1])])
        self.add_via("BOOT", (64.05, 4.5), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("BOOT", pcbnew.B_Cu, 0.25, [
            (58.0, p_u1_boot[1]), (64.05, p_u1_boot[1]), (64.05, 4.5)
        ])
        self.add_polyline("BOOT", pcbnew.F_Cu, 0.25, [(64.05, 4.5), p_rboot_2, p_swboot_1])

        # GATE_PROT: Q1.4 -> R_GATE.1 -> D_Z1.2
        p_q1_4 = self.get_pad_pos("Q1", "4")
        p_rgate_1 = self.get_pad_pos("R_GATE", "1")
        p_dz1_2 = self.get_pad_pos("D_Z1", "2")
        self.add_polyline("GATE_PROT", pcbnew.F_Cu, 0.25, [p_q1_4, p_rgate_1, p_dz1_2])

        # Charger internal nodes (BST, CHG_LX routed via B.Cu to C_BST)
        p_u2_14 = self.get_pad_pos("U2", "14")
        p_cbst_1 = self.get_pad_pos("C_BST", "1")  # (63.725, 22.0)
        p_cbst_2 = self.get_pad_pos("C_BST", "2")  # (65.275, 22.0)
        p_u2_15 = self.get_pad_pos("U2", "15")
        p_l_chg_1 = self.get_pad_pos("L_CHG", "1")

        # BST on B.Cu (escaping East of U2)
        self.add_via("BST", (18.5, 15.75), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("BST", pcbnew.F_Cu, 0.25, [p_u2_14, (18.5, 15.75)])
        self.add_via("BST", (63.725, 21.0), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("BST", pcbnew.B_Cu, 0.25, [(18.5, 15.75), (18.5, 21.0), (63.725, 21.0)])
        self.add_polyline("BST", pcbnew.F_Cu, 0.25, [(63.725, 21.0), p_cbst_1])

        # CHG_LX on B.Cu
        self.add_polyline("CHG_LX", pcbnew.F_Cu, 1.0, [p_u2_15, p_l_chg_1])
        for p_lx in ["16", "17"]:
            self.add_polyline("CHG_LX", pcbnew.F_Cu, 0.4, [p_u2_15, self.get_pad_pos("U2", p_lx)])
        self.add_via("CHG_LX", (23.5, 17.73), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("CHG_LX", pcbnew.F_Cu, 0.4, [p_l_chg_1, (23.5, 17.73)])
        self.add_via("CHG_LX", (65.275, 22.5), size_mm=0.6, drill_mm=0.3)
        self.add_polyline("CHG_LX", pcbnew.B_Cu, 0.4, [(23.5, 17.73), (23.5, 22.5), (65.275, 22.5)])
        self.add_polyline("CHG_LX", pcbnew.F_Cu, 0.4, [(65.275, 22.5), p_cbst_2])

        # CC1 & CC2
        self.add_polyline("CC1", pcbnew.F_Cu, 0.25, [self.get_pad_pos("J_USB", "A5"), self.get_pad_pos("R_CC1", "1")])
        self.add_polyline("CC2", pcbnew.F_Cu, 0.25, [self.get_pad_pos("J_USB", "B5"), self.get_pad_pos("R_CC2", "1")])

        # VSET, ISET, NTC
        self.add_polyline("VSET", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U2", "3"), self.get_pad_pos("R_VSET", "1")])
        self.add_polyline("ISET", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U2", "11"), self.get_pad_pos("R_ISET", "1")])
        p_u2_4 = self.get_pad_pos("U2", "4")
        p_rntc_1 = self.get_pad_pos("R_NTC", "1")
        p_rntc_b_2 = self.get_pad_pos("R_NTC_BIAS", "2")
        self.add_polyline("NTC", pcbnew.F_Cu, 0.25, [p_u2_4, p_rntc_1, p_rntc_b_2])

        # LEDs
        self.add_polyline("CHG_STAT", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U2", "5"), self.get_pad_pos("D_STAT", "1")])
        self.add_polyline("CHG_LED", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U2", "6"), self.get_pad_pos("D_CHG", "1")])
        self.add_polyline("D_STAT_A", pcbnew.F_Cu, 0.25, [self.get_pad_pos("R_STAT", "2"), self.get_pad_pos("D_STAT", "2")])
        self.add_polyline("D_CHG_A", pcbnew.F_Cu, 0.25, [self.get_pad_pos("R_CHG", "2"), self.get_pad_pos("D_CHG", "2")])

        # Servo buck peripheral nodes
        self.add_polyline("SRV_BOOT", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U3", "1"), self.get_pad_pos("C_BOOT_SRV", "1")])
        self.add_polyline("SRV_EN", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U3", "3"), self.get_pad_pos("R_EN_SRV", "2")])
        self.add_polyline("SRV_RT", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U3", "4"), self.get_pad_pos("R_RT_SRV", "1")])
        self.add_polyline("FB_SERVO", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U3", "5"), self.get_pad_pos("R_FB_SRV1", "2"), self.get_pad_pos("R_FB_SRV2", "1")])
        self.add_polyline("SRV_COMP", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U3", "6"), self.get_pad_pos("R_COMP_SRV", "1"), self.get_pad_pos("C_COMP_SRV2", "1")])
        self.add_polyline("COMP_NODE", pcbnew.F_Cu, 0.25, [self.get_pad_pos("R_COMP_SRV", "2"), self.get_pad_pos("C_COMP_SRV1", "1")])

        # Logic buck peripheral nodes
        self.add_polyline("LOG_BOOT", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U4", "6"), self.get_pad_pos("C_BOOT_LOG", "1")])
        self.add_polyline("LOG_EN", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U4", "5"), self.get_pad_pos("R_EN_LOG", "2")])
        self.add_polyline("FB_3V3", pcbnew.F_Cu, 0.25, [self.get_pad_pos("U4", "4"), self.get_pad_pos("R_FB_LOG1", "2"), self.get_pad_pos("R_FB_LOG2", "1")])

    # -------------------------------------------------------------------------
    # 12. Master Routing Orchestrator
    # -------------------------------------------------------------------------
    def route_all(self):
        print("=== EXECUTING PERFECT PCB ROUTING ===")
        self.clear_existing_tracks()
        self.clear_copper_zones()
        self.setup_ground_zones()
        self.route_star_ground()
        self.route_servo_power()
        self.route_motor_power()
        self.route_power_supplies()
        self.route_usb_diff_pair()
        self.route_analog_feedback()
        self.route_actuator_signals()
        self.route_communication_buses()
        self.route_peripherals()
        self.route_ground_ties()
        self.save()
        print("=== ROUTING EXECUTION COMPLETE ===")

if __name__ == "__main__":
    router = PcbRouter()
    router.route_all()
