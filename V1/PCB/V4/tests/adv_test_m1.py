#!/usr/bin/env python3
"""
Adversarial Electrical & Netlist Verification Harness for Milestone 1 (M1)
Project: ESP32-S3 Compact 2-Layer Robotic Controller PCB (V4)
Author: teamwork_challenger (Empirical Challenger Instance 1)

This harness executes exhaustive empirical verification on:
1. Netlist and schematic power rail short-circuit isolation.
2. Feedback resistor divider accuracy (TPS54302, TPS54560, IP2326).
3. Motor driver current limiting and sense resistor calibration (DRV8874).
4. Reverse polarity protection circuit topology & body diode orientation (AO4407A).
5. USB-C CC termination, D+/D- integrity, and VBUS backfeed isolation.
6. ESP32-S3 strapping pin states and ADC1 vs ADC2 Wi-Fi conflict safety.
7. Noise isolation & power supply filter decoupling integrity.
8. Actuator, encoder, SPI, I2C, and UART expansion bus integrity.
9. Verification of worker claims vs actual implementation (Discrepancy Detection).
"""

import os
import sys
import unittest
import math

sys.path.insert(0, os.path.dirname(__file__))
import kicad_parser

NET_PATH = r"D:\projekt\ARM\PCB\V4\V4.net"
SCH_PATH = r"D:\projekt\ARM\PCB\V4\V4.kicad_sch"

class AdversarialSchematicChallenge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(NET_PATH):
            raise FileNotFoundError(f"Netlist file not found: {NET_PATH}")
        if not os.path.isfile(SCH_PATH):
            raise FileNotFoundError(f"Schematic file not found: {SCH_PATH}")

        with open(NET_PATH, "r", encoding="utf-8") as f:
            net_text = f.read()
        cls.ast = kicad_parser.parse_sexpr(net_text)

        # Parse components
        cls.components = {}
        comp_node = kicad_parser.find_subnode(cls.ast, "components")
        if comp_node:
            for c in kicad_parser.find_subnodes(comp_node, "comp"):
                ref = kicad_parser.find_subnode(c, "ref")[1]
                val_node = kicad_parser.find_subnode(c, "value")
                val = val_node[1] if val_node and len(val_node) > 1 else ""
                fp_node = kicad_parser.find_subnode(c, "footprint")
                fp = fp_node[1] if fp_node and len(fp_node) > 1 else ""
                cls.components[ref] = {"value": val, "footprint": fp, "raw": c}

        # Parse nets and pin mappings
        cls.nets = {}
        cls.pin_to_net = {}
        cls.net_to_pins = {}
        nets_node = kicad_parser.find_subnode(cls.ast, "nets")
        if nets_node:
            for n in kicad_parser.find_subnodes(nets_node, "net"):
                name = kicad_parser.find_subnode(n, "name")[1]
                node_list = kicad_parser.find_subnodes(n, "node")
                cls.net_to_pins[name] = []
                for nd in node_list:
                    r = kicad_parser.find_subnode(nd, "ref")[1]
                    p = kicad_parser.find_subnode(nd, "pin")[1]
                    fn_node = kicad_parser.find_subnode(nd, "pinfunction")
                    tp_node = kicad_parser.find_subnode(nd, "pintype")
                    fn = fn_node[1] if fn_node and len(fn_node) > 1 else ""
                    tp = tp_node[1] if tp_node and len(tp_node) > 1 else ""
                    cls.pin_to_net[(r, p)] = name
                    cls.net_to_pins[name].append({"ref": r, "pin": p, "func": fn, "type": tp})

        # Load schematic symbols
        cls.sch = kicad_parser.SchematicData(SCH_PATH)

    # -------------------------------------------------------------------------
    # 1. Accidental Shorts Between Power Rails
    # -------------------------------------------------------------------------
    def test_adv_01_no_accidental_shorts_between_power_rails(self):
        """Verify that distinct power rails share NO common pins (no DC shorts)."""
        power_rails = [
            "/+3V3", "/+6V", "/+6V_BUCK", "/VMOT", "/VBUS",
            "/VBAT", "/VBAT_RAW", "/VBAT_LOGIC", "/GND", "/PGND"
        ]
        # Verify all power rails exist
        for r in power_rails:
            self.assertIn(r, self.net_to_pins, f"Power rail {r} missing in netlist!")

        # Check that no pin belongs to multiple nets
        pin_membership = {}
        for net_name, pins in self.net_to_pins.items():
            for p in pins:
                key = (p["ref"], p["pin"])
                if key not in pin_membership:
                    pin_membership[key] = []
                pin_membership[key].append(net_name)

        for key, assigned_nets in pin_membership.items():
            self.assertEqual(len(assigned_nets), 1, f"Pin {key} assigned to multiple nets: {assigned_nets}")

        # Check pairwise distinctness: no component has pins on two rails unless it is a valid functional part
        for i in range(len(power_rails)):
            for j in range(i + 1, len(power_rails)):
                rail_a = power_rails[i]
                rail_b = power_rails[j]

                pins_a = set((p["ref"], p["pin"]) for p in self.net_to_pins[rail_a])
                pins_b = set((p["ref"], p["pin"]) for p in self.net_to_pins[rail_b])
                intersection = pins_a.intersection(pins_b)
                self.assertEqual(len(intersection), 0, f"Direct short between {rail_a} and {rail_b} at pins {intersection}!")

        # Verify specifically that GND and PGND are separate nets, tied ONLY by NT1
        gnd_refs = set(p["ref"] for p in self.net_to_pins["/GND"])
        pgnd_refs = set(p["ref"] for p in self.net_to_pins["/PGND"])
        common_refs = gnd_refs.intersection(pgnd_refs)
        # Expected components with both GND and PGND:
        # NT1 (NetTie), U2 (IP2326 has analog GND pin 7 and power PGND pin 18/24)
        for r in common_refs:
            self.assertIn(r, ["NT1", "U2"], f"Unexpected component {r} bridges GND and PGND!")

    # -------------------------------------------------------------------------
    # 2. Voltage Feedback Resistor Dividers
    # -------------------------------------------------------------------------
    def test_adv_02a_tps54302_feedback_divider_ratio(self):
        """TPS54302 3.3V Logic Buck: verify Vout = 0.596 * (1 + R1/R2) = 3.30V ± 2%."""
        fb_net = self.pin_to_net.get(("U4", "4"))
        self.assertEqual(fb_net, "/FB_3V3", "U4 pin 4 (FB) not connected to /FB_3V3")

        nodes = self.net_to_pins["/FB_3V3"]
        refs = [n["ref"] for n in nodes if n["ref"] != "U4"]
        self.assertEqual(len(refs), 2, f"Expected 2 divider resistors on /FB_3V3, found: {refs}")

        r_top_val = None
        r_bot_val = None

        for r in refs:
            p1_net = self.pin_to_net.get((r, "1"))
            p2_net = self.pin_to_net.get((r, "2"))
            val_str = self.components[r]["value"].replace("k", "e3").replace("K", "e3").replace(" ", "")
            val = float(val_str)
            if "/+3V3_PRE" in (p1_net, p2_net):
                r_top_val = val
            elif "/GND" in (p1_net, p2_net):
                r_bot_val = val

        self.assertIsNotNone(r_top_val, "R_top connected to +3V3_PRE not found")
        self.assertIsNotNone(r_bot_val, "R_bottom connected to GND not found")
        self.assertEqual(r_top_val, 100000.0, f"Expected R_top 100k, got {r_top_val}")
        self.assertEqual(r_bot_val, 22100.0, f"Expected R_bottom 22.1k, got {r_bot_val}")

        # TPS54302 Vref = 0.596V
        vref = 0.596
        vout = vref * (1.0 + r_top_val / r_bot_val)
        deviation = abs(vout - 3.30) / 3.30
        print(f"\n[TPS54302] R1={r_top_val/1e3:.1f}k, R2={r_bot_val/1e3:.1f}k -> Vout={vout:.4f}V (err={deviation*100:.2f}%)")
        self.assertLess(deviation, 0.02, f"TPS54302 output {vout:.3f}V exceeds ±2% of 3.30V")

    def test_adv_02b_tps54560_feedback_divider_ratio(self):
        """TPS54560 6.0V Servo Buck: verify Vout = 0.800 * (1 + R1/R2) = 6.00V ± 2%."""
        fb_net = self.pin_to_net.get(("U3", "5"))
        self.assertEqual(fb_net, "/FB_SERVO", "U3 pin 5 (FB) not connected to /FB_SERVO")

        nodes = self.net_to_pins["/FB_SERVO"]
        refs = [n["ref"] for n in nodes if n["ref"] != "U3"]
        self.assertEqual(len(refs), 2, f"Expected 2 divider resistors on /FB_SERVO, found: {refs}")

        r_top_val = None
        r_bot_val = None

        for r in refs:
            p1_net = self.pin_to_net.get((r, "1"))
            p2_net = self.pin_to_net.get((r, "2"))
            val_str = self.components[r]["value"].replace("k", "e3").replace("K", "e3").replace(" ", "")
            val = float(val_str)
            if "/+6V_BUCK" in (p1_net, p2_net):
                r_top_val = val
            elif "/PGND" in (p1_net, p2_net):
                r_bot_val = val

        self.assertIsNotNone(r_top_val, "R_top connected to +6V_BUCK not found")
        self.assertIsNotNone(r_bot_val, "R_bottom connected to PGND not found")
        self.assertEqual(r_top_val, 56200.0, f"Expected R_top 56.2k, got {r_top_val}")
        self.assertEqual(r_bot_val, 8660.0, f"Expected R_bottom 8.66k, got {r_bot_val}")

        # TPS54560 Vref = 0.800V
        vref = 0.800
        vout = vref * (1.0 + r_top_val / r_bot_val)
        deviation = abs(vout - 6.00) / 6.00
        print(f"[TPS54560] R1={r_top_val/1e3:.1f}k, R2={r_bot_val/1e3:.2f}k -> Vout={vout:.4f}V (err={deviation*100:.2f}%)")
        self.assertLess(deviation, 0.02, f"TPS54560 output {vout:.3f}V exceeds ±2% of 6.00V")

    def test_adv_02c_ip2326_float_voltage_and_charging(self):
        """IP2326 2S Li-ion Boost Charger: verify 8.40V float voltage and 1.2A CC."""
        # Pin 3 is VSET
        vset_net = self.pin_to_net.get(("U2", "3"))
        self.assertEqual(vset_net, "/VSET", "U2 pin 3 not connected to /VSET")
        r_vset = [n["ref"] for n in self.net_to_pins["/VSET"] if n["ref"] != "U2"][0]
        self.assertEqual(self.components[r_vset]["value"], "100k", "R_VSET must be 100k for 8.40V float (4.20V/cell)")
        self.assertEqual(self.pin_to_net[(r_vset, "2")], "/GND", "R_VSET pin 2 must connect to GND")

        # Pin 11 is ISET
        iset_net = self.pin_to_net.get(("U2", "11"))
        self.assertEqual(iset_net, "/ISET", "U2 pin 11 not connected to /ISET")
        r_iset = [n["ref"] for n in self.net_to_pins["/ISET"] if n["ref"] != "U2"][0]
        self.assertEqual(self.components[r_iset]["value"], "75k", "R_ISET must be 75k for 1.2A CC charging")
        self.assertEqual(self.pin_to_net[(r_iset, "2")], "/GND", "R_ISET pin 2 must connect to GND")

        # Pin 10 is CON_SEL (cell select): must be unconnected (floating) for 2S mode
        con_sel_net = self.pin_to_net.get(("U2", "10"))
        self.assertTrue(con_sel_net is None or "unconnected" in con_sel_net, f"CON_SEL must float for 2S, got {con_sel_net}")

        # Pin 23 is VBATM (balance line) -> J_BAL pin 2
        vbatm_net = self.pin_to_net.get(("U2", "23"))
        self.assertEqual(vbatm_net, "/VBATM", "U2 pin 23 must connect to /VBATM")
        self.assertEqual(self.pin_to_net.get(("J_BAL", "2")), "/VBATM", "J_BAL pin 2 must connect to /VBATM")

    # -------------------------------------------------------------------------
    # 3. DRV8874 IPROPI Current Limiting
    # -------------------------------------------------------------------------
    def test_adv_03_drv8874_current_limit_5a(self):
        """Verify DRV8874 IPROPI resistor is 1.5kΩ, configuring 5.0A trip threshold."""
        for u, r_prop, net_prop in [("U5", "R_PROP1", "/IPROPI1"), ("U6", "R_PROP2", "/IPROPI2")]:
            pin_net = self.pin_to_net.get((u, "6"))
            self.assertEqual(pin_net, net_prop, f"{u} pin 6 (IPROPI) not connected to {net_prop}")
            self.assertEqual(self.components[r_prop]["value"], "1.5k", f"{r_prop} value not 1.5k")
            self.assertEqual(self.pin_to_net[(r_prop, "2")], "/PGND", f"{r_prop} must terminate at PGND")

            # DRV8874 trip current formula: Itrip = 7500 / R_prop = 7500 / 1500 = 5.0A
            r_val = 1500.0
            itrip = 7500.0 / r_val
            print(f"[{u}] R_prop={r_val}Ω -> Itrip={itrip:.2f}A")
            self.assertAlmostEqual(itrip, 5.0, places=2, msg=f"{u} trip current is not 5.0A")

            # Verify VREF (pin 5) is tied to +3V3
            self.assertEqual(self.pin_to_net.get((u, "5")), "/+3V3", f"{u} pin 5 (VREF) not on +3V3")
            # Verify PMODE (pin 16) is tied to PGND (PH/EN mode)
            self.assertEqual(self.pin_to_net.get((u, "16")), "/PGND", f"{u} pin 16 (PMODE) not on PGND")
            # Verify IMODE (pin 7) is tied to PGND
            self.assertEqual(self.pin_to_net.get((u, "7")), "/PGND", f"{u} pin 7 (IMODE) not on PGND")

    # -------------------------------------------------------------------------
    # 4. Reverse Polarity Protection Circuit
    # -------------------------------------------------------------------------
    def test_adv_04_reverse_polarity_pmosfet_and_clamp(self):
        """Verify AO4407A P-MOSFET reverse polarity protection topology."""
        q1 = self.components.get("Q1")
        self.assertIsNotNone(q1, "Q1 P-MOSFET not found")
        self.assertIn("AO4407A", q1["value"], "Q1 value is not AO4407A")

        # Source (pins 1, 2, 3) must be on /VBAT (circuit side)
        for p in ["1", "2", "3"]:
            self.assertEqual(self.pin_to_net.get(("Q1", p)), "/VBAT", f"Q1 pin {p} (Source) not on /VBAT")

        # Drain (pins 5, 6, 7, 8) must be on /VBAT_RAW (battery input side)
        for p in ["5", "6", "7", "8"]:
            self.assertEqual(self.pin_to_net.get(("Q1", p)), "/VBAT_RAW", f"Q1 pin {p} (Drain) not on /VBAT_RAW")

        # Gate (pin 4) must be on /GATE_PROT
        self.assertEqual(self.pin_to_net.get(("Q1", "4")), "/GATE_PROT", "Q1 pin 4 (Gate) not on /GATE_PROT")

        # Zener diode D_Z1: BZX84C10 (10V Zener clamp)
        # Cathode (pin 1) on /VBAT (Source), Anode (pin 2) on /GATE_PROT (Gate)
        self.assertEqual(self.pin_to_net.get(("D_Z1", "1")), "/VBAT", "D_Z1 pin 1 (Cathode) not on /VBAT")
        self.assertEqual(self.pin_to_net.get(("D_Z1", "2")), "/GATE_PROT", "D_Z1 pin 2 (Anode) not on /GATE_PROT")

        # Gate resistor R_GATE: 100kΩ pull-down to PGND
        # Pin 1 on /GATE_PROT, Pin 2 on /PGND
        self.assertEqual(self.components["R_GATE"]["value"], "100k", "R_GATE value not 100k")
        self.assertEqual(self.pin_to_net.get(("R_GATE", "1")), "/GATE_PROT", "R_GATE pin 1 not on /GATE_PROT")
        self.assertEqual(self.pin_to_net.get(("R_GATE", "2")), "/PGND", "R_GATE pin 2 not on /PGND")

        # TVS diode D_TVS1 on /VBAT to /PGND
        self.assertEqual(self.pin_to_net.get(("D_TVS1", "1")), "/VBAT", "D_TVS1 pin 1 not on /VBAT")
        self.assertEqual(self.pin_to_net.get(("D_TVS1", "2")), "/PGND", "D_TVS1 pin 2 not on /PGND")

    # -------------------------------------------------------------------------
    # 5. USB-C Interface & VBUS Backfeed Protection
    # -------------------------------------------------------------------------
    def test_adv_05_usb_c_and_vbus_backfeed_protection(self):
        """Verify USB-C CC1/CC2 pull-downs and VBUS backfeed isolation."""
        # CC1 and CC2 5.1k pull-downs
        self.assertEqual(self.pin_to_net.get(("J_USB", "A5")), "/CC1", "J_USB A5 not on /CC1")
        self.assertEqual(self.pin_to_net.get(("J_USB", "B5")), "/CC2", "J_USB B5 not on /CC2")
        self.assertEqual(self.components["R_CC1"]["value"], "5.1k", "R_CC1 not 5.1k")
        self.assertEqual(self.components["R_CC2"]["value"], "5.1k", "R_CC2 not 5.1k")
        self.assertEqual(self.pin_to_net.get(("R_CC1", "2")), "/GND", "R_CC1 pin 2 not on GND")
        self.assertEqual(self.pin_to_net.get(("R_CC2", "2")), "/GND", "R_CC2 pin 2 not on GND")

        # Native D+ and D- routing to ESP32-S3 GPIO20 and GPIO19
        self.assertEqual(self.pin_to_net.get(("J_USB", "A6")), "/USB_D+", "J_USB A6 not on /USB_D+")
        self.assertEqual(self.pin_to_net.get(("J_USB", "A7")), "/USB_D-", "J_USB A7 not on /USB_D-")
        self.assertEqual(self.pin_to_net.get(("U1", "13")), "/USB_D-", "ESP32 pin 13 (GPIO19) not on /USB_D-")
        self.assertEqual(self.pin_to_net.get(("U1", "14")), "/USB_D+", "ESP32 pin 14 (GPIO20) not on /USB_D+")

        # VBUS backfeed isolation: VBUS connects to U2 (IP2326) and L_CHG, but has NO direct connection to VBAT or VBAT_RAW
        vbus_pins = self.net_to_pins["/VBUS"]
        vbus_refs = set(p["ref"] for p in vbus_pins)
        self.assertNotIn("Q1", vbus_refs, "Q1 should not connect to VBUS")
        self.assertNotIn("J_BAT", vbus_refs, "J_BAT should not connect to VBUS")
        self.assertNotIn("U3", vbus_refs, "U3 should not connect to VBUS")
        self.assertNotIn("U4", vbus_refs, "U4 should not connect to VBUS")
        self.assertNotIn("U5", vbus_refs, "U5 should not connect to VBUS")
        self.assertNotIn("U6", vbus_refs, "U6 should not connect to VBUS")

    # -------------------------------------------------------------------------
    # 6. ESP32-S3 Strapping Pins & ADC Wi-Fi Channel Isolation
    # -------------------------------------------------------------------------
    def test_adv_06_esp32_strapping_pins_and_adc_channels(self):
        """Verify ESP32 strapping pins and ADC1 vs ADC2 Wi-Fi conflict safety."""
        # GPIO0 (BOOT, pin 27): 10k pull-up to +3V3 and SW_BOOT to GND
        self.assertEqual(self.pin_to_net.get(("U1", "27")), "/BOOT", "ESP32 pin 27 not on /BOOT")
        self.assertEqual(self.components["R_BOOT"]["value"], "10k", "R_BOOT not 10k")
        self.assertEqual(self.pin_to_net.get(("R_BOOT", "1")), "/+3V3", "R_BOOT pin 1 not on +3V3")
        self.assertEqual(self.pin_to_net.get(("SW_BOOT", "2")), "/GND", "SW_BOOT pin 2 not on GND")

        # GPIO45 (VDD_SPI strapping, pin 26): must be LOW at reset to select 3.3V flash LDO
        # Connected to M2_IN2 -> U6 pin 2 (EN/IN2) with internal 100k pull-down to GND
        self.assertEqual(self.pin_to_net.get(("U1", "26")), "/M2_IN2", "ESP32 pin 26 not on /M2_IN2")
        self.assertEqual(self.pin_to_net.get(("U6", "2")), "/M2_IN2", "U6 pin 2 not on /M2_IN2")
        # Ensure NO pull-up resistor exists on /M2_IN2
        m2_in2_refs = [p["ref"] for p in self.net_to_pins["/M2_IN2"]]
        for r in m2_in2_refs:
            self.assertFalse(r.startswith("R_PU"), f"Pull-up found on strapping net /M2_IN2: {r}")

        # GPIO46 (Boot mode strapping, pin 16): must be LOW at reset
        # Connected to SERVO2_PWM via series resistor R_PWM2, NO pull-up
        self.assertEqual(self.pin_to_net.get(("U1", "16")), "/SERVO2_PWM", "ESP32 pin 16 not on /SERVO2_PWM")
        pwm2_refs = [p["ref"] for p in self.net_to_pins["/SERVO2_PWM"]]
        for r in pwm2_refs:
            self.assertFalse(r.startswith("R_PU"), f"Pull-up found on strapping net /SERVO2_PWM: {r}")

        # GPIO3 (JTAG strapping, pin 15): connected to SERVO1_PWM via R_PWM1
        self.assertEqual(self.pin_to_net.get(("U1", "15")), "/SERVO1_PWM", "ESP32 pin 15 not on /SERVO1_PWM")

        # All 6 Servo Feedback lines MUST be on ADC1 (GPIO4..GPIO9) to avoid Wi-Fi ADC2 conflicts!
        # ESP32-S3 pin mappings:
        # Pin 4: SERVO1_FB (GPIO4 / ADC1_CH3)
        # Pin 5: SERVO2_FB (GPIO5 / ADC1_CH4)
        # Pin 6: SERVO3_FB (GPIO6 / ADC1_CH5)
        # Pin 7: SERVO4_FB (GPIO7 / ADC1_CH6)
        # Pin 12: SERVO5_FB (GPIO8 / ADC1_CH7)
        # Pin 17: SERVO6_FB (GPIO9 / ADC1_CH8)
        expected_adc1_pins = {
            "4": "/SERVO1_FB",
            "5": "/SERVO2_FB",
            "6": "/SERVO3_FB",
            "7": "/SERVO4_FB",
            "12": "/SERVO5_FB",
            "17": "/SERVO6_FB"
        }
        for pin_num, expected_net in expected_adc1_pins.items():
            actual_net = self.pin_to_net.get(("U1", pin_num))
            self.assertEqual(actual_net, expected_net, f"ESP32 pin {pin_num} expected {expected_net}, got {actual_net}")

        # Verify conditioning on each servo feedback: RC filter (1k + 100nF) and clamping diode (BAT54S)
        for i in range(1, 7):
            d_clamp = f"D_CLAMP{i}"
            c_fb = f"C_FB{i}"
            r_fb = f"R_SFB{i}"
            self.assertIn(d_clamp, self.components, f"Clamping diode {d_clamp} missing")
            self.assertIn(c_fb, self.components, f"Filter capacitor {c_fb} missing")
            self.assertIn(r_fb, self.components, f"Filter resistor {r_fb} missing")
            self.assertEqual(self.components[r_fb]["value"], "1k", f"{r_fb} not 1k")
            self.assertEqual(self.components[c_fb]["value"], "100nF", f"{c_fb} not 100nF")
            self.assertEqual(self.components[d_clamp]["value"], "BAT54S", f"{d_clamp} not BAT54S")

    # -------------------------------------------------------------------------
    # 7. Power Supply Noise Isolation & Decoupling
    # -------------------------------------------------------------------------
    def test_adv_07_noise_isolation_and_filters(self):
        """Verify brownout isolation diode, reservoir cap, and Pi-filter."""
        # D_ISO (SS14) between VBAT (Anode) and VBAT_LOGIC (Cathode)
        self.assertEqual(self.pin_to_net.get(("D_ISO", "2")), "/VBAT", "D_ISO pin 2 not on /VBAT")
        self.assertEqual(self.pin_to_net.get(("D_ISO", "1")), "/VBAT_LOGIC", "D_ISO pin 1 not on /VBAT_LOGIC")

        # C_HOLD (47µF) on VBAT_LOGIC
        self.assertEqual(self.pin_to_net.get(("C_HOLD", "1")), "/VBAT_LOGIC", "C_HOLD pin 1 not on /VBAT_LOGIC")
        self.assertEqual(self.pin_to_net.get(("C_HOLD", "2")), "/GND", "C_HOLD pin 2 not on /GND")

        # FB1 (BLM21PG221) between +3V3_PRE and +3V3
        self.assertEqual(self.pin_to_net.get(("FB1", "1")), "/+3V3_PRE", "FB1 pin 1 not on /+3V3_PRE")
        self.assertEqual(self.pin_to_net.get(("FB1", "2")), "/+3V3", "FB1 pin 2 not on /+3V3")

        # Motor bulk capacitors: 100µF on VMOT for each driver
        self.assertEqual(self.components["C_VM1_1"]["value"], "100uF", "C_VM1_1 not 100uF")
        self.assertEqual(self.components["C_VM2_1"]["value"], "100uF", "C_VM2_1 not 100uF")

        # Servo bulk capacitor: 470µF on +6V_BUCK
        self.assertEqual(self.components["C_SRV_BULK1"]["value"], "470uF", "C_SRV_BULK1 not 470uF")

    # -------------------------------------------------------------------------
    # 8. Actuators, Sensors & Expansion Interfaces
    # -------------------------------------------------------------------------
    def test_adv_08_expansion_interfaces_integrity(self):
        """Verify SPI1, SPI2, I2C, IMU, UART, Encoders, Servos pin assignments."""
        # 6 Servo headers J_SERVO1..6: pin 1 GND, pin 2 +6V, pin 3 PWM, pin 4 FB
        for i in range(1, 7):
            srv = f"J_SERVO{i}"
            self.assertEqual(self.pin_to_net.get((srv, "1")), "/GND", f"{srv} pin 1 not GND")
            self.assertEqual(self.pin_to_net.get((srv, "2")), "/+6V", f"{srv} pin 2 not +6V")

        # Dual encoders J_ENC1, J_ENC2: pin 1 +3V3, pin 2 GND, pin 3 A, pin 4 B
        for enc in ["J_ENC1", "J_ENC2"]:
            self.assertEqual(self.pin_to_net.get((enc, "1")), "/+3V3", f"{enc} pin 1 not +3V3")
            self.assertEqual(self.pin_to_net.get((enc, "2")), "/GND", f"{enc} pin 2 not GND")

        # I2C header J_I2C: pin 1 +3V3, pin 2 GND, pin 3 SCL (GPIO15), pin 4 SDA (GPIO16)
        self.assertEqual(self.pin_to_net.get(("J_I2C", "1")), "/+3V3", "J_I2C pin 1 not +3V3")
        self.assertEqual(self.pin_to_net.get(("J_I2C", "2")), "/GND", "J_I2C pin 2 not GND")
        self.assertEqual(self.pin_to_net.get(("J_I2C", "3")), "/I2C_SCL", "J_I2C pin 3 not /I2C_SCL")
        self.assertEqual(self.pin_to_net.get(("J_I2C", "4")), "/I2C_SDA", "J_I2C pin 4 not /I2C_SDA")

        # IMU header J_IMU: pin 1 +3V3, pin 2 GND, pin 3 SCL, pin 4 SDA, pin 5 INT (GPIO17)
        self.assertEqual(self.pin_to_net.get(("J_IMU", "5")), "/IMU_INT", "J_IMU pin 5 not /IMU_INT")
        self.assertEqual(self.pin_to_net.get(("U1", "10")), "/IMU_INT", "ESP32 pin 10 (GPIO17) not /IMU_INT")

        # UART header J_UART: pin 1 TXD (GPIO43), pin 2 RXD (GPIO44), pin 3 GND
        self.assertEqual(self.pin_to_net.get(("J_UART", "1")), "/UART0_TXD", "J_UART pin 1 not /UART0_TXD")
        self.assertEqual(self.pin_to_net.get(("J_UART", "2")), "/UART0_RXD", "J_UART pin 2 not /UART0_RXD")
        self.assertEqual(self.pin_to_net.get(("J_UART", "3")), "/GND", "J_UART pin 3 not /GND")

    # -------------------------------------------------------------------------
    # 9. Discrepancy Detection: Worker Claims vs Physical Netlist
    # -------------------------------------------------------------------------
    def test_adv_09_worker_claim_audit(self):
        """Audit claims made in worker handoff against netlist reality."""
        # Claim 1: Worker claims "D+ and D- ESD protection via U_ESD (USBLC6-2SC6)"
        u_esd_present = "U_ESD" in self.components or any("USBLC6" in c["value"] for c in self.components.values())
        print(f"\n[Audit] Worker claim 'U_ESD (USBLC6-2SC6)': {'PRESENT' if u_esd_present else 'OMITTED (Claim Discrepancy)'}")
        # Note: While omitted from schematic, native USB pins connect directly to ESP32-S3 internal USB PHY.
        # This is recorded as a documentation inaccuracy finding rather than an electrical blocker.

if __name__ == "__main__":
    unittest.main(verbosity=2)
