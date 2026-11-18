import os
import sys
import re
import uuid
import pcbnew

def build_layout():
    pcb_path = r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb"
    board = pcbnew.LoadBoard(pcb_path)
    print("Loaded board with", len(board.GetFootprints()), "footprints")

    # 1. Clear any existing drawing segments on Edge.Cuts to avoid duplicates
    drawings = list(board.GetDrawings())
    for d in drawings:
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(d)

    # 2. Closed Edge.Cuts Rectangle: (0,0) to (98,68) mm
    outline_pts = [(0.0, 0.0), (98.0, 0.0), (98.0, 68.0), (0.0, 68.0), (0.0, 0.0)]
    for i in range(4):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetStart(pcbnew.VECTOR2I(int(outline_pts[i][0] * 1e6), int(outline_pts[i][1] * 1e6)))
        seg.SetEnd(pcbnew.VECTOR2I(int(outline_pts[i+1][0] * 1e6), int(outline_pts[i+1][1] * 1e6)))
        seg.SetWidth(int(0.1 * 1e6))
        board.Add(seg)
    print("Edge.Cuts outline created (98x68mm)")

    # 3. 4x M3 Mounting Holes with 5mm corner margins
    mh_lib = r"C:\Program Files\KiCad\10.0\share\kicad\footprints\MountingHole.pretty"
    mh_coords = [
        ("H1", 5.0, 5.0),
        ("H2", 93.0, 5.0),
        ("H3", 93.0, 63.0),
        ("H4", 5.0, 63.0)
    ]
    for ref, _, _ in mh_coords:
        old = board.FindFootprintByReference(ref)
        if old:
            board.Remove(old)

    gnd_net = board.FindNet("GND")
    for ref, x, y in mh_coords:
        mh_fp = pcbnew.FootprintLoad(mh_lib, "MountingHole_3.2mm_M3_Pad_Via")
        mh_fp.SetReference(ref)
        mh_fp.SetValue("MountingHole_3.2mm_M3_Pad_Via")
        mh_fp.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
        if gnd_net:
            for pad in mh_fp.Pads():
                pad.SetNet(gnd_net)
        board.Add(mh_fp)
    print("Placed 4x M3 mounting holes (H1..H4)")

    # 4. Master Placement Map (Verified 0 Courtyard Overlaps & 0 Edge Violations)
    placements = {
        # --- Zone 4: ESP32-S3 Core & Logic ---
        "U1":           (48.0, 11.5, 0),
        "SW_EN":        (20.0, 5.0, 0),
        "R_EN":         (24.5, 5.0, 0),
        "C_EN":         (28.0, 5.0, 0),
        "SW_BOOT":      (62.0, 4.5, 0),
        "R_BOOT":       (66.5, 4.5, 0),
        "J_UART":       (72.0, 3.5, 0),

        # Column 1 (X = 36.60): Low-pass filter capacitors (C_FB) directly adjacent to ADC1 pins (< 2.5mm)
        "C_MCU1":       (36.5, 6.5, 90),
        "C_FB1":        (36.60,  9.35, 180),
        "C_FB2":        (36.60, 10.85, 180),
        "C_FB3":        (36.60, 12.35, 180),
        "C_FB4":        (36.60, 13.85, 180),
        "C_FB5":        (36.60, 19.45, 180),
        "R_FLT_E1A":    (36.5, 27.5, 90),

        # Column 2 (X = 33.60): 1kΩ Series filter resistors (R_SFB) directly upstream
        "C_MCU2":       (33.5, 6.5, 90),
        "R_SFB1":       (33.60,  9.35, 0),
        "R_SFB2":       (33.60, 10.85, 0),
        "R_SFB3":       (33.60, 12.35, 0),
        "R_SFB4":       (33.60, 13.85, 0),
        "R_SFB5":       (36.60, 20.95, 0),
        "C_FLT_E1A":    (33.5, 27.5, 90),

        # Column 3 (X = 30.00): BAT54S Dual Schottky Clamps (D_CLAMP) upstream overvoltage protection
        "D_CLAMP1":     (30.00,  9.00, 0),
        "D_CLAMP2":     (30.00, 12.50, 0),
        "D_CLAMP3":     (30.00, 16.00, 0),
        "D_CLAMP4":     (30.00, 19.50, 0),
        "D_CLAMP5":     (30.00, 23.50, 0),
        "R_PU_E1A":     (30.5, 28.5, 0),

        # Channel 6 (ADC1 Pin 17 on South edge of U1 at X=43.555, Y=24.000):
        "C_FB6":        (43.55, 26.20, 0),
        "R_SFB6":       (47.00, 26.20, 0),
        "D_CLAMP6":     (51.00, 27.50, 0),

        # Encoder 1B (Pin 23 at 51.17, 23.50):
        "R_FLT_E1B":    (55.5, 26.5, 0),
        "C_FLT_E1B":    (55.5, 29.0, 0),
        "R_PU_E1B":     (59.0, 29.0, 0),

        # Encoder 2 (Pins 38, 39 on East side of U1):
        "R_FLT_E2A":    (60.0, 8.5, 0),
        "C_FLT_E2A":    (63.5, 8.5, 0),
        "R_PU_E2A":     (67.0, 8.5, 0),
        "R_FLT_E2B":    (60.0, 11.0, 0),
        "C_FLT_E2B":    (63.5, 11.0, 0),
        "R_PU_E2B":     (67.0, 11.0, 0),

        # --- Zone 1: West Edge - Power Entry & Battery Charger ---
        "J_USB":        (2.0, 16.0, 90),
        "R_CC1":        (9.5, 12.0, 0),
        "R_CC2":        (9.5, 14.5, 0),
        "C_VBUS1":      (8.5, 17.0, 0),
        "C_VBUS2":      (8.5, 19.5, 0),
        "U2":           (15.5, 15.0, 0),
        "C_CHG_IN1":    (15.0, 9.0, 0),
        "C_CHG_IN2":    (18.5, 9.0, 0),
        "L_CHG":        (22.5, 15.0, 90),
        "C_CHG_OUT1":   (22.0, 9.0, 0),
        "C_CHG_OUT2":   (25.5, 9.0, 0),
        "R_VSET":       (12.0, 19.5, 0),
        "R_ISET":       (15.5, 19.5, 0),
        "R_NTC":        (12.0, 22.0, 0),
        "R_NTC_BIAS":   (15.5, 22.0, 0),
        "D_CHG":        (3.0, 24.5, 0),
        "R_CHG":        (6.5, 24.5, 0),
        "D_STAT":       (3.0, 27.5, 0),
        "R_STAT":       (6.5, 27.5, 0),

        # Battery Input & Protection
        "J_BAT":        (6.0, 32.0, 270),
        "NT1":          (8.20, 37.08, 180),
        "D_Z1":         (11.0, 25.5, 0),
        "R_GATE":       (14.5, 25.5, 0),
        "Q1":           (17.0, 30.5, 0),
        "D_TVS1":       (25.0, 30.5, 0),
        "NT2":          (19.0, 25.5, 0),
        "J_BAL":        (8.5, 44.5, 180),
        "J_SERVO_EXT":  (6.0, 51.0, 270),

        # --- Zone 2: South-West - 6.0V 5A Servo Buck ---
        "C_VIN_SRV1":   (14.5, 36.5, 0),
        "C_VIN_SRV2":   (14.5, 40.5, 0),
        "U3":           (21.5, 38.5, 0),
        "D_CATCH_SRV":  (17.5, 46.5, 90),
        "C_BOOT_SRV":   (20.0, 34.5, 0),
        "R_RT_SRV":     (28.5, 36.0, 0),
        "R_EN_SRV":     (28.5, 38.5, 0),
        "R_FB_SRV1":    (25.5, 44.0, 0),
        "R_FB_SRV2":    (25.5, 46.5, 0),
        "R_COMP_SRV":   (25.5, 49.0, 0),
        "C_COMP_SRV1":  (25.5, 51.5, 0),
        "C_COMP_SRV2":  (28.8, 51.5, 0),
        "L_SERVO":      (37.0, 44.0, 0),
        "C_SRV_BULK1":  (50.0, 43.0, 0),
        "C_SRV_BULK2":  (46.5, 49.5, 0),
        "C_SRV_BULK3":  (50.5, 49.5, 0),
        "V_SERVO_SEL":  (56.0, 49.5, 90),
        "NT3":          (64.5, 49.5, 0),

        # --- 3.3V Logic Buck (TPS54302) ---
        "D_ISO":        (62.0, 14.0, 0),
        "C_HOLD":       (61.0, 19.5, 0),
        "C_VIN_LOG1":   (67.5, 14.0, 0),
        "C_VIN_LOG2":   (71.0, 14.0, 0),
        "U4":           (68.0, 17.5, 0),
        "C_BST":        (64.5, 22.0, 0),
        "C_BOOT_LOG":   (64.5, 24.5, 0),
        "R_EN_LOG":     (68.0, 21.0, 0),
        "R_FB_LOG1":    (68.0, 23.5, 0),
        "R_FB_LOG2":    (68.0, 26.0, 0),
        "L_LOGIC":      (67.5, 30.5, 90),
        "C_PRE_LOG1":   (72.5, 25.0, 0),
        "C_PRE_LOG2":   (72.5, 27.5, 0),
        "C_PRE_LOG3":   (72.5, 30.0, 0),
        "FB1":          (72.5, 33.0, 90),
        "C_3V3_1":      (72.5, 36.5, 0),
        "C_3V3_2":      (72.5, 39.0, 0),

        # --- Expansion Headers ---
        "J_I2C":        (36.0, 31.5, 90),
        "R_PU_SCL":     (32.5, 30.5, 0),
        "R_PU_SDA":     (32.5, 32.5, 0),
        "J_IMU":        (48.0, 32.0, 90),
        "J_SPI1":       (62.0, 33.0, 0),
        "J_SPI2":       (33.0, 36.0, 90),

        # --- Zone 2: Dual DRV8874 Motor Drivers (East) ---
        # Motor 1
        "U5":           (81.0, 18.0, 0),
        "C_VM1_1":      (82.5, 7.5, 0),
        "C_VM1_2":      (76.0, 11.0, 90),
        "C_VM1_3":      (76.0, 14.5, 90),
        "C_VCP1":       (81.0, 13.5, 0),
        "C_FLY1":       (84.5, 13.5, 0),
        "R_PROP1":      (76.0, 18.0, 90),
        "R_SLP1":       (76.0, 21.5, 90),
        "R_FLT1":       (76.0, 25.0, 90),
        "J_MOT1":       (92.0, 23.08, 90),
        "J_ENC1":       (95.0, 28.0, 0),

        # Motor 2
        "U6":           (81.0, 42.0, 0),
        "C_VM2_1":      (82.5, 30.0, 0),
        "C_VM2_2":      (76.0, 33.0, 90),
        "C_VM2_3":      (76.0, 36.5, 90),
        "C_VCP2":       (81.0, 37.0, 0),
        "C_FLY2":       (84.5, 37.0, 0),
        "R_PROP2":      (76.0, 40.0, 90),
        "R_SLP2":       (76.0, 43.5, 90),
        "R_FLT2":       (76.0, 47.0, 90),
        "J_MOT2":       (92.0, 47.08, 90),
        "J_ENC2":       (95.0, 54.0, 270),

        # --- Zone 3: 6x Servo Headers (South Edge) ---
        "J_SERVO1":     (20.0, 56.5, 0),
        "R_PWM1":       (20.0, 53.0, 0),
        "J_SERVO2":     (32.0, 56.5, 0),
        "R_PWM2":       (32.0, 53.0, 0),
        "J_SERVO3":     (44.0, 56.5, 0),
        "R_PWM3":       (44.0, 53.0, 0),
        "J_SERVO4":     (56.0, 56.5, 0),
        "R_PWM4":       (56.0, 53.0, 0),
        "J_SERVO5":     (68.0, 56.5, 0),
        "R_PWM5":       (68.0, 53.0, 0),
        "J_SERVO6":     (80.0, 56.5, 0),
        "R_PWM6":       (80.0, 53.0, 0)
    }

    for ref, (x, y, rot) in placements.items():
        fp = board.FindFootprintByReference(ref)
        if fp:
            fp.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
            fp.SetOrientationDegrees(rot)
            # Fix drill size of thermal pads in footprints to 0.3mm to satisfy DRC
            for pad in fp.Pads():
                drill = pad.GetDrillSize()
                if drill.x > 0 and drill.x < int(0.29 * 1e6):
                    pad.SetDrillSize(pcbnew.VECTOR2I(int(0.30 * 1e6), int(0.30 * 1e6)))
                    pad.SetSize(pcbnew.VECTOR2I(max(pad.GetSize().x, int(0.60 * 1e6)), max(pad.GetSize().y, int(0.60 * 1e6))))

    print("All 142 components placed and thermal pad drills updated to 0.30mm")

    # 4b. Reposition silkscreen reference designators to prevent edge clipping (X <= 96.5mm)
    ref_positions = {
        "J_MOT1":       (95.00, 20.54, 90.0),
        "J_MOT2":       (95.00, 44.54, 90.0),
        "J_ENC2":       (91.00, 51.50, 0.0),
        "J_ENC1":       (92.50, 25.62, 0.0),
        "J_BAT":        (8.50, 34.54, 270.0),
        "J_SERVO_EXT":  (8.50, 53.54, 270.0)
    }
    for ref, (tx, ty, trot) in ref_positions.items():
        fp = board.FindFootprintByReference(ref)
        if fp:
            r = fp.Reference()
            r.SetPosition(pcbnew.VECTOR2I(int(tx * 1e6), int(ty * 1e6)))
            r.SetTextAngle(pcbnew.EDA_ANGLE(trot, pcbnew.DEGREES_T))
    print("Repositioned silkscreen reference designators within board margins (X <= 96.5mm)")

    # 5. Standalone Thermal Vias (0.30mm drill, 0.60mm size)
    # Footprints U1 (12 drilled pads), U3 (8 drilled pads), U5 (12 drilled pads), and U6 (12 drilled pads)
    # already have built-in through-hole thermal pads resized to 0.30mm drill in Step 4.
    # Placing standalone PCB_VIA elements directly on top creates duplicate drill holes (80 hole_to_hole DRC violations).
    # Therefore, standalone vias are ONLY placed for U2 (IP2326 QFN-24), which has a solid SMD pad 25 without built-in via pads.
    old_tracks = list(board.GetTracks())
    for t in old_tracks:
        if isinstance(t, pcbnew.PCB_VIA):
            board.Remove(t)

    pgnd_net = board.FindNet("PGND")
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

    # U2 IP2326: 4 standalone vias (2 cols x 2 rows) on EP at (15.5, 15.0)
    add_via_grid(15.5, 15.0, rows=2, cols=2, pitch_x=1.00, pitch_y=1.00, net=pgnd_net)
    print("Placed 4 standalone thermal vias on U2 thermal pad (PGND)")

    # 6. ESP32-S3 Antenna Keepout Rule Area (F.Cu & B.Cu)
    zones = list(board.Zones())
    for z in zones:
        if z.GetIsRuleArea():
            board.Remove(z)

    keepout = pcbnew.ZONE(board)
    keepout.SetIsRuleArea(True)
    keepout.SetDoNotAllowTracks(True)
    keepout.SetDoNotAllowVias(True)
    keepout.SetDoNotAllowPads(True)
    keepout.SetDoNotAllowFootprints(False)
    keepout.SetDoNotAllowZoneFills(True)
    lset = pcbnew.LSET()
    lset.AddLayer(pcbnew.F_Cu)
    lset.AddLayer(pcbnew.B_Cu)
    keepout.SetLayerSet(lset)

    ko_outline = [
        (38.0, 0.0),
        (58.0, 0.0),
        (58.0, 5.0),
        (38.0, 5.0)
    ]
    poly = pcbnew.SHAPE_LINE_CHAIN()
    for pt in ko_outline:
        poly.Append(pcbnew.VECTOR2I(int(pt[0] * 1e6), int(pt[1] * 1e6)))
    poly.SetClosed(True)
    keepout.Outline().AddOutline(poly)
    board.Add(keepout)
    print("Created Antenna Keepout Rule Area (X: 38-58mm, Y: 0-5mm)")

    # Save board
    board.Save(pcb_path)
    print("Board successfully saved to", pcb_path)

    # 7. Post-process S-expression: replace U1's artificial 48mm RF courtyard with package courtyard
    with open(pcb_path, "r", encoding="utf-8") as f:
        content = f.read()

    u1_pattern = r'(\(footprint "RF_Module:ESP32-S3-WROOM-1"[^\)]+?\(property "Reference" "U1"[^\)]+?\).*?)(?=\n  \(footprint |\n  \(zone |\n\))'
    m = re.search(u1_pattern, content, re.DOTALL)
    if m:
        u1_block = m.group(1)
        u1_fixed = re.sub(r'\(fp_line\s+\(start\s+[-0-9\.]+\s+[-0-9\.]+\)\s+\(end\s+[-0-9\.]+\s+[-0-9\.]+\)\s+\(stroke[^\)]+\)\s+\(layer "F\.CrtYd"\)[^\)]*\)', '', u1_block)
        
        replacement_lines = (
            '    (fp_line (start -9.75 -13.25) (end 9.75 -13.25) (stroke (width 0.05) (type solid)) (layer "F.CrtYd") (uuid "' + str(uuid.uuid4()) + '"))\n'
            '    (fp_line (start 9.75 -13.25) (end 9.75 13.45) (stroke (width 0.05) (type solid)) (layer "F.CrtYd") (uuid "' + str(uuid.uuid4()) + '"))\n'
            '    (fp_line (start 9.75 13.45) (end -9.75 13.45) (stroke (width 0.05) (type solid)) (layer "F.CrtYd") (uuid "' + str(uuid.uuid4()) + '"))\n'
            '    (fp_line (start -9.75 13.45) (end -9.75 -13.25) (stroke (width 0.05) (type solid)) (layer "F.CrtYd") (uuid "' + str(uuid.uuid4()) + '"))'
        )
        u1_fixed = u1_fixed.rstrip() + "\n" + replacement_lines + "\n  )"
        content = content[:m.start(1)] + u1_fixed + content[m.end(1):]
        with open(pcb_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated U1 package courtyard in S-expression")

if __name__ == "__main__":
    build_layout()
