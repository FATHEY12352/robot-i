import sys
import pcbnew

pcb_path = r"D:\projekt\ARM\PCB\V4\V4.kicad_pcb"
board = pcbnew.LoadBoard(pcb_path)

def test_kicad_placement():
    p = {
        # 4 Mounting Holes (H1..H4)
        "H1": (5.0, 5.0, 0),
        "H2": (93.0, 5.0, 0),
        "H3": (93.0, 63.0, 0),
        "H4": (5.0, 63.0, 0),

        # --- Zone 4: ESP32-S3 Core & Logic ---
        "U1":           (48.0, 11.5, 0),
        "SW_EN":        (20.0, 5.0, 0),
        "R_EN":         (24.5, 5.0, 0),
        "C_EN":         (28.0, 5.0, 0),
        "SW_BOOT":      (62.0, 4.5, 0),
        "R_BOOT":       (66.5, 4.5, 0),
        "J_UART":       (72.0, 3.5, 0),

        # Column 1 (X = 36.5): Decoupling & R_SFB (<= 3.5mm from ADC1 pins)
        "C_MCU1":       (36.5, 6.5, 90),
        "R_SFB1":       (36.5, 10.0, 90),
        "R_SFB2":       (36.5, 13.5, 90),
        "R_SFB3":       (36.5, 17.0, 90),
        "R_SFB4":       (36.5, 20.5, 90),
        "R_SFB5":       (36.5, 24.0, 90),
        "R_FLT_E1A":    (36.5, 27.5, 90),

        # Column 2 (X = 33.5): C_MCU2 & C_FB
        "C_MCU2":       (33.5, 6.5, 90),
        "C_FB1":        (33.5, 10.0, 90),
        "C_FB2":        (33.5, 13.5, 90),
        "C_FB3":        (33.5, 17.0, 90),
        "C_FB4":        (33.5, 20.5, 90),
        "C_FB5":        (33.5, 24.0, 90),
        "C_FLT_E1A":    (33.5, 27.5, 90),

        # Column 3 (X = 30.0): D_CLAMP & Pullups
        "D_CLAMP1":     (30.0, 9.5, 0),
        "D_CLAMP2":     (30.0, 13.5, 0),
        "D_CLAMP3":     (30.0, 17.5, 0),
        "D_CLAMP4":     (30.0, 21.5, 0),
        "D_CLAMP5":     (30.0, 25.5, 0),
        "R_PU_E1A":     (30.5, 28.5, 0),

        # Channel 6 (ADC1 Pin 17 at 43.55, 23.50):
        "R_SFB6":       (43.55, 26.5, 0),
        "C_FB6":        (47.0, 26.5, 0),
        "D_CLAMP6":     (51.0, 27.5, 0),

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
        "J_BAT":        (9.0, 34.0, 180),
        "NT1":          (5.5, 34.0, 90),
        "D_Z1":         (11.0, 25.5, 0),
        "R_GATE":       (14.5, 25.5, 0),
        "Q1":           (17.0, 30.5, 0),
        "D_TVS1":       (25.0, 30.5, 0),
        "NT2":          (19.0, 25.5, 0),
        "J_BAL":        (8.5, 44.0, 180),
        "J_SERVO_EXT":  (8.5, 52.5, 180),

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
        "NT3":          (61.5, 49.5, 0),

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
        "J_MOT1":       (92.0, 18.0, 270),
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
        "J_MOT2":       (92.0, 42.0, 270),
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

    # Apply to board and evaluate exact bounding boxes
    for ref, (x, y, rot) in p.items():
        fp = board.FindFootprintByReference(ref)
        if fp:
            fp.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
            fp.SetOrientationDegrees(rot)

    bboxes = {}
    for ref in p:
        fp = board.FindFootprintByReference(ref)
        if not fp: continue
        if ref == "U1":
            x, y, _ = p[ref]
            bboxes[ref] = (x - 9.75, y - 13.25, x + 9.75, y + 13.45)
            continue
        box = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        bboxes[ref] = (box.GetX()/1e6, box.GetY()/1e6, box.GetRight()/1e6, box.GetBottom()/1e6)

    overlaps = []
    refs = list(bboxes.keys())
    for i in range(len(refs)):
        r1 = refs[i]
        b1 = bboxes[r1]
        for j in range(i + 1, len(refs)):
            r2 = refs[j]
            b2 = bboxes[r2]
            if "NT" in r1 or "NT" in r2:
                continue
            if not (b1[2] <= b2[0] + 0.01 or b1[0] >= b2[2] - 0.01 or
                    b1[3] <= b2[1] + 0.01 or b1[1] >= b2[3] - 0.01):
                overlaps.append((r1, r2))

    edge_violations = []
    for r, b in bboxes.items():
        if r in ["U1", "J_USB", "NT1", "NT2", "NT3"]:
            continue
        if b[0] < 0.2 or b[2] > 97.8 or b[1] < 0.2 or b[3] > 67.8:
            edge_violations.append((r, b))

    print(f"EXACT KICAD OVERLAPS: {len(overlaps)}")
    for r1, r2 in overlaps:
        print(f"  {r1:12} {bboxes[r1]} <---> {r2:12} {bboxes[r2]}")

    print(f"EXACT EDGE CLEARANCE VIOLATIONS: {len(edge_violations)}")
    for r, b in edge_violations:
        print(f"  {r:12} box={b}")

    return p, len(overlaps) == 0 and len(edge_violations) == 0

if __name__ == "__main__":
    test_kicad_placement()
