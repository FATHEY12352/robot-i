import os
import sys
import math
import pcbnew

def generate_layout():
    pcb_path = r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb"
    board = pcbnew.LoadBoard(pcb_path)
    print("Loaded board with", len(board.GetFootprints()), "footprints")

    # -------------------------------------------------------------------------
    # 1. Clear existing tracks, vias, drawings, zones to start clean
    # -------------------------------------------------------------------------
    # Remove existing drawings (Edge.Cuts etc)
    drawings = list(board.GetDrawings())
    for d in drawings:
        board.Remove(d)
    
    # Remove existing vias
    tracks = list(board.GetTracks())
    for t in tracks:
        board.Remove(t)

    # Remove existing zones
    zones = list(board.Zones())
    for z in zones:
        board.Remove(z)

    # -------------------------------------------------------------------------
    # 2. Board Outline: Closed 98.0mm x 68.0mm rectangle on Edge.Cuts
    # -------------------------------------------------------------------------
    outline_pts = [
        (0.0, 0.0),
        (98.0, 0.0),
        (98.0, 68.0),
        (0.0, 68.0),
        (0.0, 0.0)
    ]
    line_width = int(0.1 * 1e6)
    for i in range(len(outline_pts) - 1):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        p1 = pcbnew.VECTOR2I(int(outline_pts[i][0] * 1e6), int(outline_pts[i][1] * 1e6))
        p2 = pcbnew.VECTOR2I(int(outline_pts[i+1][0] * 1e6), int(outline_pts[i+1][1] * 1e6))
        seg.SetStart(p1)
        seg.SetEnd(p2)
        seg.SetWidth(line_width)
        board.Add(seg)
    print("Added 4 Edge.Cuts boundary segments (98x68mm)")

    # -------------------------------------------------------------------------
    # 3. 4x M3 Mounting Holes with 5mm corner margins
    # H1: (5,5), H2: (93,5), H3: (93,63), H4: (5,63)
    # -------------------------------------------------------------------------
    mh_lib = r"C:\Program Files\KiCad\10.0\share\kicad\footprints\MountingHole.pretty"
    mh_coords = [
        ("H1", 5.0, 5.0),
        ("H2", 93.0, 5.0),
        ("H3", 93.0, 63.0),
        ("H4", 5.0, 63.0)
    ]
    # Remove existing H1..H4 if present
    for ref, _, _ in mh_coords:
        existing = board.FindFootprintByReference(ref)
        if existing:
            board.Remove(existing)

    gnd_net = board.FindNet("GND")
    for ref, x, y in mh_coords:
        mh_fp = pcbnew.FootprintLoad(mh_lib, "MountingHole_3.2mm_M3_Pad_Via")
        if not mh_fp:
            raise RuntimeError(f"Could not load MountingHole_3.2mm_M3_Pad_Via for {ref}")
        mh_fp.SetReference(ref)
        mh_fp.SetValue("MountingHole_3.2mm_M3_Pad_Via")
        mh_fp.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
        if gnd_net:
            for pad in mh_fp.Pads():
                pad.SetNet(gnd_net)
        board.Add(mh_fp)
    print("Placed 4x M3 mounting holes H1..H4 with GND net")

    # -------------------------------------------------------------------------
    # 4. Master Component Placement Map
    # ref -> (x_mm, y_mm, rotation_deg)
    # -------------------------------------------------------------------------
    placements = {
        # --- Zone 4: North / Center - ESP32-S3 & Logic ---
        "U1":           (25.0, 11.0, 0),     # ESP32-S3-WROOM-1 (antenna overhanging top)
        "SW_BOOT":      (38.0, 5.0, 0),      # Boot button
        "R_BOOT":       (38.0, 9.0, 0),      # Boot pullup 10k
        "SW_EN":        (10.0, 5.0, 0),      # Reset button
        "R_EN":         (10.0, 9.0, 0),      # Reset pullup 10k
        "C_EN":         (10.0, 12.0, 0),     # Reset filter 100nF
        "J_UART":       (48.0, 5.0, 0),      # Debug UART 3-pin

        # Critical Analog Proximity (<= 3.5mm from ESP32 ADC1 pins)
        # Pin 4: SERVO1_FB at (16.25, 9.55)
        "R_SFB1":       (13.5, 9.55, 0),
        "C_FB1":        (11.5, 9.55, 0),
        "D_CLAMP1":     (13.5, 7.5, 0),
        # Pin 5: SERVO2_FB at (16.25, 10.82)
        "R_SFB2":       (13.5, 11.5, 0),
        "C_FB2":        (11.5, 11.5, 0),
        "D_CLAMP2":     (13.5, 13.5, 0),
        # Pin 6: SERVO3_FB at (16.25, 12.09)
        "R_SFB3":       (13.5, 15.5, 0),
        "C_FB3":        (11.5, 15.5, 0),
        "D_CLAMP3":     (13.5, 17.5, 0),
        # Pin 7: SERVO4_FB at (16.25, 13.36)
        "R_SFB4":       (13.5, 19.5, 0),
        "C_FB4":        (11.5, 19.5, 0),
        "D_CLAMP4":     (13.5, 21.5, 0),
        # Pin 12: SERVO5_FB at (16.25, 19.71)
        "R_SFB5":       (13.5, 23.5, 0),
        "C_FB5":        (11.5, 23.5, 0),
        "D_CLAMP5":     (13.5, 25.5, 0),
        # Pin 17: SERVO6_FB at (20.55, 23.50)
        "R_SFB6":       (20.55, 26.2, 90),
        "C_FB6":        (20.55, 28.2, 90),
        "D_CLAMP6":     (23.5, 27.0, 0),

        # Encoder Noise Suppression (Pins 11, 23, 38, 39)
        # Pin 11: M1_ENC_A at (16.25, 18.44)
        "R_FLT_E1A":    (10.0, 17.5, 0),
        "C_FLT_E1A":    (10.0, 19.5, 0),
        "R_PU_E1A":     (10.0, 15.5, 0),
        # Pin 23: M1_ENC_B at (28.17, 23.50)
        "R_FLT_E1B":    (28.17, 26.2, 90),
        "C_FLT_E1B":    (28.17, 28.2, 90),
        "R_PU_E1B":     (30.5, 27.0, 0),
        # Pin 38: M2_ENC_A at (33.75, 8.28)
        "R_FLT_E2A":    (37.0, 12.0, 0),
        "C_FLT_E2A":    (39.0, 12.0, 0),
        "R_PU_E2A":     (41.0, 12.0, 0),
        # Pin 39: M2_ENC_B at (33.75, 7.01)
        "R_FLT_E2B":    (37.0, 14.0, 0),
        "C_FLT_E2B":    (39.0, 14.0, 0),
        "R_PU_E2B":     (41.0, 14.0, 0),

        # 3.3V Logic Buck (TPS54302 cluster)
        "D_ISO":        (46.0, 14.0, 0),     # Brownout isolation SS14 SMA
        "C_HOLD":       (50.0, 14.0, 90),    # 47uF 1206 hold-up
        "C_VIN_LOG1":   (54.0, 14.0, 0),     # 10uF 0805
        "C_VIN_LOG2":   (57.0, 14.0, 0),     # 100nF 0603
        "U4":           (55.0, 18.0, 0),     # TPS54302 SOT-23-6
        "C_BST":        (51.0, 18.0, 0),     # 100nF 0603
        "C_BOOT_LOG":   (48.0, 18.0, 0),     # 100nF 0603
        "R_EN_LOG":     (51.0, 21.0, 0),     # 100k 0603
        "L_LOGIC":      (61.0, 18.0, 0),     # 10uH SRP5030T
        "C_PRE_LOG1":   (61.0, 13.0, 0),     # 22uF 0805
        "C_PRE_LOG2":   (61.0, 23.0, 0),     # 22uF 0805
        "C_PRE_LOG3":   (64.0, 18.0, 0),     # 100nF 0603
        "R_FB_LOG1":    (55.0, 22.0, 0),     # 100k 0603
        "R_FB_LOG2":    (57.0, 22.0, 0),     # 22.1k 0603
        "FB1":          (66.0, 14.0, 90),    # BLM21PG221 0805
        "C_3V3_1":      (66.0, 18.0, 0),     # 22uF 0805
        "C_3V3_2":      (66.0, 21.0, 0),     # 100nF 0603
        "C_MCU1":       (36.0, 18.0, 0),     # 10uF 0805 near Pin 2
        "C_MCU2":       (36.0, 21.0, 0),     # 100nF 0603 near Pin 2

        # Expansion Headers (Central Logic Corridor)
        "J_SPI1":       (36.0, 32.0, 0),     # 1x06 vertical
        "J_SPI2":       (44.0, 32.0, 0),     # 1x06 vertical
        "J_I2C":        (52.0, 32.0, 0),     # 1x04 vertical
        "R_PU_SCL":     (52.0, 27.0, 0),     # 4.7k 0603
        "R_PU_SDA":     (54.0, 27.0, 0),     # 4.7k 0603
        "J_IMU":        (60.0, 32.0, 0),     # 1x05 vertical

        # --- Zone 1: West Edge - Power Entry & Battery Charging ---
        "J_USB":        (0.5, 20.0, 90),     # USB-C 16-pin (mouth facing West)
        "R_CC1":        (5.0, 17.5, 0),      # 5.1k 0603
        "R_CC2":        (5.0, 22.5, 0),      # 5.1k 0603
        "C_VBUS1":      (8.0, 18.0, 0),      # 10uF 0805
        "C_VBUS2":      (8.0, 22.0, 0),      # 100nF 0603
        "U2":           (16.0, 20.0, 0),     # IP2326 QFN-24 2S boost charger
        "C_CHG_IN1":    (12.0, 16.0, 0),     # 10uF 0805
        "C_CHG_IN2":    (14.0, 16.0, 0),     # 100nF 0603
        "L_CHG":        (22.0, 20.0, 0),     # SRP7028A 2.2uH inductor
        "C_CHG_OUT1":   (16.0, 15.0, 0),     # 22uF 0805
        "C_CHG_OUT2":   (18.0, 15.0, 0),     # 100nF 0603
        "R_VSET":       (12.0, 24.0, 0),     # 100k 0603
        "R_ISET":       (14.0, 24.0, 0),     # 75k 0603
        "R_NTC":        (16.0, 24.0, 0),     # 10k 0603
        "R_NTC_BIAS":   (18.0, 24.0, 0),     # 10k 0603
        "D_CHG":        (3.0, 27.0, 0),      # Red LED 0805
        "R_CHG":        (6.0, 27.0, 0),      # 1k 0603
        "D_STAT":       (3.0, 30.0, 0),      # Green LED 0805
        "R_STAT":       (6.0, 30.0, 0),      # 1k 0603

        # Battery Input & Protection
        "J_BAT":        (4.0, 38.0, 180),    # Phoenix MKDS 5.08mm 2-pin (facing West)
        # NT1 star net tie: J_BAT Pin 2 is at (4.0, 32.92). NT1 at (5.5, 32.92) is 1.5mm away!
        "NT1":          (5.5, 32.92, 0),     # Star ground net tie (<= 2mm from J_BAT pin 2)
        "Q1":           (13.0, 38.0, 0),     # AO4407A P-MOSFET SOIC-8
        "D_Z1":         (10.0, 35.0, 0),     # BZX84C10 SOD-323
        "R_GATE":       (12.0, 35.0, 0),     # 100k 0603
        "D_TVS1":       (19.0, 38.0, 90),    # SMBJ12A SMB TVS diode
        "NT2":          (19.0, 33.0, 0),     # VBAT to VMOT net tie
        "J_BAL":        (4.0, 48.0, 180),    # JST-XH 3-pin (facing West)

        # --- Zone 2: South-West - 6.0V 5A Servo Buck (TPS54560 cluster) ---
        "C_VIN_SRV1":   (14.0, 45.0, 90),    # 10uF 1206
        "C_VIN_SRV2":   (17.0, 45.0, 0),     # 100nF 0603
        "U3":           (21.0, 46.0, 0),     # TPS54560 SOIC-8-EP
        "D_CATCH_SRV":  (18.0, 50.0, 90),    # B540C SMC catch diode (< 2mm to PH)
        "C_BOOT_SRV":   (25.0, 43.0, 0),     # 100nF 0603
        "R_RT_SRV":     (25.0, 45.0, 0),     # 200k 0603
        "R_EN_SRV":     (25.0, 47.0, 0),     # 100k 0603
        "R_FB_SRV1":    (25.0, 49.0, 0),     # 56.2k 0603
        "R_FB_SRV2":    (27.0, 49.0, 0),     # 8.66k 0603
        "R_COMP_SRV":   (25.0, 51.0, 0),     # 10k 0603
        "C_COMP_SRV1":  (27.0, 51.0, 0),     # 3.3nF 0603
        "C_COMP_SRV2":  (29.0, 51.0, 0),     # 47pF 0603
        "L_SERVO":      (35.0, 47.0, 0),     # SRP1038C 7.2uH (10x10mm)
        "C_SRV_BULK1":  (46.0, 47.0, 0),     # 470uF 8x10.5mm electrolytic
        "C_SRV_BULK2":  (46.0, 53.0, 0),     # 22uF 1206
        "C_SRV_BULK3":  (49.0, 53.0, 0),     # 100nF 0603
        "V_SERVO_SEL":  (53.0, 53.0, 0),     # 1x03 vertical jumper
        "NT3":          (57.0, 53.0, 0),     # V_SERVO to +6V net tie
        "J_SERVO_EXT":  (12.0, 64.0, 0),     # Phoenix 5.08mm 2-pin (South perimeter)

        # --- Zone 2: East - Dual DRV8874 Motor Drivers ---
        # Motor 1 (Upper East)
        "U5":           (78.0, 18.0, 0),     # DRV8874 HTSSOP-16-EP
        "C_VM1_1":      (78.0, 10.0, 0),     # 100uF 6.3x5.4mm bulk electrolytic
        "C_VM1_2":      (73.0, 13.0, 0),     # 10uF 0805
        "C_VM1_3":      (73.0, 15.0, 0),     # 100nF 0603
        "C_VCP1":       (83.0, 13.0, 0),     # 1uF 0603
        "C_FLY1":       (83.0, 15.0, 0),     # 22nF 0603
        "R_PROP1":      (73.0, 19.0, 0),     # 1.5k 0603
        "R_SLP1":       (73.0, 21.0, 0),     # 10k 0603
        "R_FLT1":       (73.0, 23.0, 0),     # 10k 0603
        "J_MOT1":       (94.0, 16.0, 270),   # Phoenix MKDS 5.08mm 2-pin (East edge, <10mm)
        "J_ENC1":       (94.0, 26.0, 270),   # 1x04 vertical header (East edge)

        # Motor 2 (Lower East)
        "U6":           (78.0, 40.0, 0),     # DRV8874 HTSSOP-16-EP
        "C_VM2_1":      (78.0, 32.0, 0),     # 100uF 6.3x5.4mm bulk electrolytic
        "C_VM2_2":      (73.0, 35.0, 0),     # 10uF 0805
        "C_VM2_3":      (73.0, 37.0, 0),     # 100nF 0603
        "C_VCP2":       (83.0, 35.0, 0),     # 1uF 0603
        "C_FLY2":       (83.0, 37.0, 0),     # 22nF 0603
        "R_PROP2":      (73.0, 41.0, 0),     # 1.5k 0603
        "R_SLP2":       (73.0, 43.0, 0),     # 10k 0603
        "R_FLT2":       (73.0, 45.0, 0),     # 10k 0603
        "J_MOT2":       (94.0, 38.0, 270),   # Phoenix MKDS 5.08mm 2-pin (East edge, <10mm)
        "J_ENC2":       (94.0, 48.0, 270),   # 1x04 vertical header (East edge)

        # --- Zone 3: South Edge - 6x Servo Headers & Series Resistors ---
        "J_SERVO1":     (24.0, 64.0, 0),     # 1x04 vertical
        "R_PWM1":       (24.0, 59.0, 0),     # 220R 0603
        "J_SERVO2":     (36.0, 64.0, 0),     # 1x04 vertical
        "R_PWM2":       (36.0, 59.0, 0),     # 220R 0603
        "J_SERVO3":     (48.0, 64.0, 0),     # 1x04 vertical
        "R_PWM3":       (48.0, 59.0, 0),     # 220R 0603
        "J_SERVO4":     (60.0, 64.0, 0),     # 1x04 vertical
        "R_PWM4":       (60.0, 59.0, 0),     # 220R 0603
        "J_SERVO5":     (72.0, 64.0, 0),     # 1x04 vertical
        "R_PWM5":       (72.0, 59.0, 0),     # 220R 0603
        "J_SERVO6":     (84.0, 64.0, 0),     # 1x04 vertical
        "R_PWM6":       (84.0, 59.0, 0)      # 220R 0603
    }

    # Verify all 142 components are in placements map
    fps = board.GetFootprints()
    placed_count = 0
    missing_in_map = []
    for fp in fps:
        ref = fp.GetReference()
        if ref in ["H1", "H2", "H3", "H4"]:
            continue
        if ref in placements:
            x, y, rot = placements[ref]
            fp.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
            fp.SetOrientationDegrees(rot)
            placed_count += 1
        else:
            missing_in_map.append(ref)

    print(f"Placed {placed_count} components. Missing from placements map: {missing_in_map}")
    if missing_in_map:
        raise ValueError(f"Components not defined in placement map: {missing_in_map}")

    # -------------------------------------------------------------------------
    # 5. Thermal Via Matrices (0.3mm drill / 0.6mm diameter)
    #    - U3 (TPS54560): 8 vias (2x4 grid, PGND)
    #    - U5 (DRV8874 M1): 12 vias (3x4 grid, PGND)
    #    - U6 (DRV8874 M2): 12 vias (3x4 grid, PGND)
    #    - U2 (IP2326): 4 vias (2x2 grid, PGND)
    #    - U1 (ESP32-S3): 9 vias (3x3 grid, GND)
    # -------------------------------------------------------------------------
    pgnd_net = board.FindNet("PGND")
    if not pgnd_net:
        print("Warning: PGND net not found by name, finding from pad")
        pgnd_net = board.FindFootprintByReference("J_BAT").FindPadByNumber("2").GetNet()

    if not gnd_net:
        gnd_net = board.FindFootprintByReference("U1").FindPadByNumber("1").GetNet()

    via_drill = int(0.30 * 1e6)
    via_size = int(0.60 * 1e6)

    def add_via_grid(cx, cy, rows, cols, pitch_x, pitch_y, net):
        start_x = cx - ((cols - 1) * pitch_x) / 2.0
        start_y = cy - ((rows - 1) * pitch_y) / 2.0
        for r in range(rows):
            for c in range(cols):
                vx = start_x + c * pitch_x
                vy = start_y + r * pitch_y
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pcbnew.VECTOR2I(int(vx * 1e6), int(vy * 1e6)))
                via.SetDrill(via_drill)
                via.SetWidth(via_size)
                via.SetViaType(pcbnew.VIATYPE_THROUGH)
                if net:
                    via.SetNet(net)
                board.Add(via)

    # U3 TPS54560 PowerPAD center at (21.0, 46.0)
    add_via_grid(21.0, 46.0, rows=4, cols=2, pitch_x=1.30, pitch_y=1.10, net=pgnd_net)
    print("Added 8 thermal vias for U3 (TPS54560)")

    # U5 DRV8874 PowerPAD center at (78.0, 18.0)
    add_via_grid(78.0, 18.0, rows=4, cols=3, pitch_x=1.00, pitch_y=1.20, net=pgnd_net)
    print("Added 12 thermal vias for U5 (DRV8874 M1)")

    # U6 DRV8874 PowerPAD center at (78.0, 40.0)
    add_via_grid(78.0, 40.0, rows=4, cols=3, pitch_x=1.00, pitch_y=1.20, net=pgnd_net)
    print("Added 12 thermal vias for U6 (DRV8874 M2)")

    # U2 IP2326 EP center at (16.0, 20.0)
    add_via_grid(16.0, 20.0, rows=2, cols=2, pitch_x=1.20, pitch_y=1.20, net=pgnd_net)
    print("Added 4 thermal vias for U2 (IP2326)")

    # U1 ESP32-S3 EP center at (25.0 - 1.5, 11.0 + 2.5) -> (23.5, 13.5)
    add_via_grid(23.5, 13.5, rows=3, cols=3, pitch_x=1.20, pitch_y=1.20, net=gnd_net)
    print("Added 9 thermal vias for U1 (ESP32-S3 EP)")

    total_vias = len(board.GetTracks())  # in pcbnew vias are in tracks container
    print(f"Total vias on board: {total_vias}")

    # -------------------------------------------------------------------------
    # 6. ESP32-S3 Antenna Keepout Zone (F.Cu & B.Cu)
    # -------------------------------------------------------------------------
    keepout = pcbnew.ZONE(board)
    keepout.SetIsRuleArea(True)
    keepout.SetDoNotAllowTracks(True)
    keepout.SetDoNotAllowVias(True)
    keepout.SetDoNotAllowZoneFills(True)
    lset = pcbnew.LSET()
    lset.AddLayer(pcbnew.F_Cu)
    lset.AddLayer(pcbnew.B_Cu)
    keepout.SetLayerSet(lset)
    outline = keepout.Outline()
    outline.NewOutline()
    # Antenna region X: [15, 35], Y: [0, 6]
    outline.Append(int(15.0 * 1e6), int(0.0 * 1e6))
    outline.Append(int(35.0 * 1e6), int(0.0 * 1e6))
    outline.Append(int(35.0 * 1e6), int(6.0 * 1e6))
    outline.Append(int(15.0 * 1e6), int(6.0 * 1e6))
    board.Add(keepout)
    print("Added ESP32 antenna keepout rule area")

    # -------------------------------------------------------------------------
    # 7. Solid Bottom Ground Copper Zone (B.Cu)
    # -------------------------------------------------------------------------
    gnd_zone = pcbnew.ZONE(board)
    gnd_zone.SetLayer(pcbnew.B_Cu)
    if pgnd_net:
        gnd_zone.SetNet(pgnd_net)
    gnd_outline = gnd_zone.Outline()
    gnd_outline.NewOutline()
    gnd_outline.Append(int(0.5 * 1e6), int(0.5 * 1e6))
    gnd_outline.Append(int(97.5 * 1e6), int(0.5 * 1e6))
    gnd_outline.Append(int(97.5 * 1e6), int(67.5 * 1e6))
    gnd_outline.Append(int(0.5 * 1e6), int(67.5 * 1e6))
    board.Add(gnd_zone)
    print("Added B.Cu ground copper plane")

    # -------------------------------------------------------------------------
    # 8. Rebuild connectivity & Save Board
    # -------------------------------------------------------------------------
    board.BuildConnectivity()
    pcbnew.SaveBoard(pcb_path, board)
    print("Successfully saved board to", pcb_path)

if __name__ == "__main__":
    generate_layout()
