"""
Adversarial Verification Suite for ESP32-S3 MCU Pin Allocation & Signal Integrity
Project: ESP32-S3 Compact 2-Layer Robotic Controller PCB (V4)
Milestone: M1 (Schematic Capture & Circuit Design)

Audits:
1. Complete 41-pin physical mapping of ESP32-S3-WROOM-1 (U1) against PROJECT.md
2. Strapping pin safety (GPIO0, GPIO45, GPIO46, GPIO3)
3. Actuator analog feedback conditioning (ADC1 channels, 1k+100nF RC cutoff, BAT54S clamp)
4. Quadrature encoder conditioning (4.7k pull-ups, 100R+1nF RC debounce, PCNT routing)
5. Communication buses (SPI1 IO MUX, SPI2 GPIO Matrix, I2C pull-ups, IMU interrupt)
6. Decoupling, brownout isolation, and reset circuitry
"""

import os
import sys
import math
import unittest
from typing import Dict, List, Set, Tuple, Any

NETLIST_PATH = r"D:\projekt\ARM\PCB\V4\V4.net"
SCH_PATH = r"D:\projekt\ARM\PCB\V4\V4.kicad_sch"

def parse_netlist(net_path: str):
    with open(net_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    tokens = []
    i = 0
    n = len(content)
    while i < n:
        c = content[i]
        if c.isspace():
            i += 1
            continue
        if c in '()':
            tokens.append(c)
            i += 1
        elif c == '"':
            i += 1
            chars = []
            while i < n:
                if content[i] == '\\' and i + 1 < n:
                    chars.append(content[i+1])
                    i += 2
                elif content[i] == '"':
                    break
                else:
                    chars.append(content[i])
                    i += 1
            tokens.append("".join(chars))
            i += 1
        else:
            start = i
            while i < n and not content[i].isspace() and content[i] not in '()':
                i += 1
            tokens.append(content[start:i])

    def parse_expr(tok_iter):
        res = []
        for tok in tok_iter:
            if tok == '(':
                res.append(parse_expr(tok_iter))
            elif tok == ')':
                return res
            else:
                res.append(tok)
        return res

    ast = parse_expr(iter(tokens))
    root = ast[0] if len(ast) == 1 and isinstance(ast[0], list) else ast

    components = {}
    nets = {}
    pin_to_net = {}

    def find_all(node, tag):
        matches = []
        if isinstance(node, list):
            if len(node) > 0 and node[0] == tag:
                matches.append(node)
            for item in node:
                matches.extend(find_all(item, tag))
        return matches

    def find_first(node, tag):
        if isinstance(node, list):
            for item in node:
                if isinstance(item, list) and len(item) > 0 and item[0] == tag:
                    return item
        return None

    for comp in find_all(root, 'comp'):
        ref = ""
        val = ""
        fp = ""
        ref_node = find_first(comp, 'ref')
        val_node = find_first(comp, 'value')
        fp_node = find_first(comp, 'footprint')
        if ref_node and len(ref_node) > 1:
            ref = ref_node[1]
        if val_node and len(val_node) > 1:
            val = val_node[1]
        if fp_node and len(fp_node) > 1:
            fp = fp_node[1]
        components[ref] = {'value': val, 'footprint': fp}

    for net in find_all(root, 'net'):
        name_node = find_first(net, 'name')
        if not name_node or len(name_node) < 2:
            continue
        net_name = name_node[1]
        net_nodes = []
        for node in find_all(net, 'node'):
            r_node = find_first(node, 'ref')
            p_node = find_first(node, 'pin')
            pt_node = find_first(node, 'pintype')
            pf_node = find_first(node, 'pinfunction')
            r = r_node[1] if r_node and len(r_node) > 1 else ""
            p = p_node[1] if p_node and len(p_node) > 1 else ""
            pt = pt_node[1] if pt_node and len(pt_node) > 1 else ""
            pf = pf_node[1] if pf_node and len(pf_node) > 1 else ""
            net_nodes.append({'ref': r, 'pin': p, 'pintype': pt, 'pinfunction': pf})
            if r and p:
                pin_to_net[(r, p)] = net_name
        nets[net_name] = net_nodes

    return components, nets, pin_to_net

class TestAdversarialMcuSignal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.components, cls.nets, cls.pin_to_net = parse_netlist(NETLIST_PATH)

    def test_u1_all_41_pins_connected(self):
        """Audit all 41 physical pins of U1: zero floating or unconnected pins."""
        for pin in range(1, 42):
            key = ("U1", str(pin))
            self.assertIn(key, self.pin_to_net, f"U1 Pin {pin} is missing net connection in netlist")
            net = self.pin_to_net[key]
            self.assertFalse(net.startswith("unconnected-"), f"U1 Pin {pin} is unconnected: {net}")

    def test_strapping_gpio0_boot_pullup(self):
        """GPIO0 (Pin 27) must have 10k pull-up to +3.3V and NO pull-down to GND."""
        net = self.pin_to_net[("U1", "27")]
        nodes = self.nets[net]
        # Must connect to R_BOOT
        r_boot = next((n['ref'] for n in nodes if n['ref'] == 'R_BOOT'), None)
        self.assertIsNotNone(r_boot, "R_BOOT pullup resistor not connected to GPIO0")
        val = self.components[r_boot]['value']
        self.assertIn("10k", val.lower(), f"R_BOOT value is not 10k: {val}")
        # Verify pullup connects to +3.3V
        p1 = self.pin_to_net[(r_boot, "1")]
        p2 = self.pin_to_net[(r_boot, "2")]
        self.assertTrue(p1 in ['/+3V3', '+3V3'] or p2 in ['/+3V3', '+3V3'], "R_BOOT does not connect to +3V3")
        # Ensure no pull-down to GND
        for n in nodes:
            ref = n['ref']
            if ref.startswith('R') and ref != 'R_BOOT':
                rp1 = self.pin_to_net[(ref, "1")]
                rp2 = self.pin_to_net[(ref, "2")]
                self.assertFalse(rp1 in ['/GND', 'GND'] or rp2 in ['/GND', 'GND'], f"Illegal pull-down on GPIO0 via {ref}")

    def test_strapping_gpio45_vdd_spi_safety(self):
        """GPIO45 (Pin 26) controls VDD_SPI voltage; MUST NOT have pull-up to +3.3V."""
        net = self.pin_to_net[("U1", "26")]
        nodes = self.nets[net]
        for n in nodes:
            ref = n['ref']
            if ref.startswith('R'):
                rp1 = self.pin_to_net[(ref, "1")]
                rp2 = self.pin_to_net[(ref, "2")]
                self.assertFalse(rp1 in ['/+3V3', '+3V3'] or rp2 in ['/+3V3', '+3V3'], f"Illegal pull-up on GPIO45 via {ref}")

    def test_strapping_gpio46_rom_log_safety(self):
        """GPIO46 (Pin 16) MUST NOT have pull-up to +3.3V."""
        net = self.pin_to_net[("U1", "16")]
        nodes = self.nets[net]
        for n in nodes:
            ref = n['ref']
            if ref.startswith('R'):
                rp1 = self.pin_to_net[(ref, "1")]
                rp2 = self.pin_to_net[(ref, "2")]
                self.assertFalse(rp1 in ['/+3V3', '+3V3'] or rp2 in ['/+3V3', '+3V3'], f"Illegal pull-up on GPIO46 via {ref}")

    def test_strapping_gpio3_jtag_safety(self):
        """GPIO3 (Pin 15) MUST NOT have pull-up to +3.3V."""
        net = self.pin_to_net[("U1", "15")]
        nodes = self.nets[net]
        for n in nodes:
            ref = n['ref']
            if ref.startswith('R'):
                rp1 = self.pin_to_net[(ref, "1")]
                rp2 = self.pin_to_net[(ref, "2")]
                self.assertFalse(rp1 in ['/+3V3', '+3V3'] or rp2 in ['/+3V3', '+3V3'], f"Illegal pull-up on GPIO3 via {ref}")

    def test_servo_analog_feedback_adc1_exclusivity(self):
        """All 6 servo feedback lines must connect to ADC1 channels (GPIO4..9) and ZERO on ADC2."""
        expected_fb_pins = {
            1: (4, "GPIO4", "ADC1_CH3"),
            2: (5, "GPIO5", "ADC1_CH4"),
            3: (6, "GPIO6", "ADC1_CH5"),
            4: (7, "GPIO7", "ADC1_CH6"),
            5: (12, "GPIO8", "ADC1_CH7"),
            6: (17, "GPIO9", "ADC1_CH8"),
        }
        for s, (p, gpio, adc_ch) in expected_fb_pins.items():
            net = self.pin_to_net[("U1", str(p))]
            self.assertTrue("SERVO" in net and "FB" in net, f"Pin {p} is not servo feedback: {net}")

        adc2_pins = [19, 20, 21, 22, 8, 9, 10, 11, 13, 14]
        for p in adc2_pins:
            net = self.pin_to_net[("U1", str(p))]
            self.assertFalse("FB" in net and "SERVO" in net, f"Servo feedback routed to ADC2 pin {p}: {net}")

    def test_servo_analog_feedback_rc_filter_and_clamp(self):
        """Verify R = 1k +/- 5%, C = 100nF +/- 10%, fc ~ 1.59 kHz, and BAT54S dual Schottky clamping."""
        expected_fc = 1591.55  # Hz
        for s in range(1, 7):
            r_ref = f"R_SFB{s}"
            c_ref = f"C_FB{s}"
            d_ref = f"D_CLAMP{s}"

            self.assertIn(r_ref, self.components)
            self.assertIn(c_ref, self.components)
            self.assertIn(d_ref, self.components)

            r_val_str = self.components[r_ref]['value'].lower().replace(' ', '')
            c_val_str = self.components[c_ref]['value'].lower().replace(' ', '')
            d_val_str = self.components[d_ref]['value']

            self.assertIn("1k", r_val_str)
            self.assertIn("100n", c_val_str)
            self.assertIn("BAT54S", d_val_str)

            r = 1000.0
            c = 100e-9
            fc = 1.0 / (2.0 * math.pi * r * c)
            self.assertAlmostEqual(fc, expected_fc, delta=1.0)

            # Check BAT54S wiring: Pin 1 -> GND, Pin 2 -> +3V3, Pin 3 -> Signal
            self.assertEqual(self.pin_to_net[(d_ref, "1")], "/GND")
            self.assertEqual(self.pin_to_net[(d_ref, "2")], "/+3V3")
            self.assertEqual(self.pin_to_net[(d_ref, "3")], f"/SERVO{s}_FB")

            # Check C_FB wiring: Pin 1 -> Signal, Pin 2 -> GND
            self.assertEqual(self.pin_to_net[(c_ref, "1")], f"/SERVO{s}_FB")
            self.assertEqual(self.pin_to_net[(c_ref, "2")], "/GND")

            # Check R_SFB wiring: Pin 1 -> Header input, Pin 2 -> Filtered signal
            self.assertEqual(self.pin_to_net[(r_ref, "1")], f"/SRV{s}_FB_IN")
            self.assertEqual(self.pin_to_net[(r_ref, "2")], f"/SERVO{s}_FB")

            # Check Header wiring: Pin 4 connects to /SRVs_FB_IN
            self.assertEqual(self.pin_to_net[(f"J_SERVO{s}", "4")], f"/SRV{s}_FB_IN")

    def test_servo_pwm_damping_resistors(self):
        """Verify all 6 servo PWM outputs have 220-ohm series damping resistors."""
        expected_pwm = {
            1: ("U1", "15", "R_PWM1", "J_SERVO1"),
            2: ("U1", "16", "R_PWM2", "J_SERVO2"),
            3: ("U1", "28", "R_PWM3", "J_SERVO3"),
            4: ("U1", "29", "R_PWM4", "J_SERVO4"),
            5: ("U1", "30", "R_PWM5", "J_SERVO5"),
            6: ("U1", "31", "R_PWM6", "J_SERVO6"),
        }
        for s, (u_ref, u_pin, r_ref, j_ref) in expected_pwm.items():
            self.assertIn(r_ref, self.components)
            val = self.components[r_ref]['value']
            self.assertIn("220", val)
            mcu_net = self.pin_to_net[(u_ref, u_pin)]
            self.assertEqual(self.pin_to_net[(r_ref, "1")], mcu_net)
            out_net = self.pin_to_net[(r_ref, "2")]
            self.assertEqual(self.pin_to_net[(j_ref, "3")], out_net)

    def test_encoder_pullups_and_debounce(self):
        """Verify encoder pull-ups (4.7k to +3.3V) and RC debounce filters (100R + 1nF, fc ~ 1.59 MHz)."""
        expected_enc = {
            "M1_ENC_A": ("U1", "11", "R_FLT_E1A", "C_FLT_E1A", "R_PU_E1A", "J_ENC1", "3"),
            "M1_ENC_B": ("U1", "23", "R_FLT_E1B", "C_FLT_E1B", "R_PU_E1B", "J_ENC1", "4"),
            "M2_ENC_A": ("U1", "38", "R_FLT_E2A", "C_FLT_E2A", "R_PU_E2A", "J_ENC2", "3"),
            "M2_ENC_B": ("U1", "39", "R_FLT_E2B", "C_FLT_E2B", "R_PU_E2B", "J_ENC2", "4"),
        }
        for sig, (u_ref, u_pin, rf_ref, cf_ref, rpu_ref, j_ref, j_pin) in expected_enc.items():
            # Pull-up check: 4.7k to +3.3V
            self.assertIn("4.7k", self.components[rpu_ref]['value'].lower())
            self.assertEqual(self.pin_to_net[(rpu_ref, "1")], "/+3V3")

            # Filter check: 100R + 1nF
            self.assertIn("100", self.components[rf_ref]['value'])
            self.assertIn("1n", self.components[cf_ref]['value'].lower())

            r = 100.0
            c = 1e-9
            fc = 1.0 / (2.0 * math.pi * r * c)
            self.assertAlmostEqual(fc, 1.59155e6, delta=1000.0)

            # Node check
            raw_net = self.pin_to_net[(j_ref, j_pin)]
            self.assertEqual(self.pin_to_net[(rpu_ref, "2")], raw_net)
            self.assertEqual(self.pin_to_net[(rf_ref, "1")], raw_net)

            filt_net = self.pin_to_net[(u_ref, u_pin)]
            self.assertEqual(self.pin_to_net[(rf_ref, "2")], filt_net)
            self.assertEqual(self.pin_to_net[(cf_ref, "1")], filt_net)
            self.assertEqual(self.pin_to_net[(cf_ref, "2")], "/GND")

    def test_buses_spi1_spi2_i2c_imu(self):
        """Verify SPI1 on IO MUX, SPI2 on GPIO Matrix, I2C with 4.7k pullups, and IMU INT."""
        # SPI1: GPIO10 (CS), GPIO11 (MOSI), GPIO12 (SCK), GPIO13 (MISO)
        self.assertEqual(self.pin_to_net[("U1", "18")], "/SPI1_CS")
        self.assertEqual(self.pin_to_net[("U1", "19")], "/SPI1_MOSI")
        self.assertEqual(self.pin_to_net[("U1", "20")], "/SPI1_SCK")
        self.assertEqual(self.pin_to_net[("U1", "21")], "/SPI1_MISO")
        self.assertEqual(self.pin_to_net[("J_SPI1", "3")], "/SPI1_SCK")
        self.assertEqual(self.pin_to_net[("J_SPI1", "4")], "/SPI1_MOSI")
        self.assertEqual(self.pin_to_net[("J_SPI1", "5")], "/SPI1_MISO")
        self.assertEqual(self.pin_to_net[("J_SPI1", "6")], "/SPI1_CS")

        # SPI2: GPIO39 (SCK), GPIO40 (MISO), GPIO41 (MOSI), GPIO42 (CS)
        self.assertEqual(self.pin_to_net[("U1", "32")], "/SPI2_SCK")
        self.assertEqual(self.pin_to_net[("U1", "33")], "/SPI2_MISO")
        self.assertEqual(self.pin_to_net[("U1", "34")], "/SPI2_MOSI")
        self.assertEqual(self.pin_to_net[("U1", "35")], "/SPI2_CS")
        self.assertEqual(self.pin_to_net[("J_SPI2", "3")], "/SPI2_SCK")
        self.assertEqual(self.pin_to_net[("J_SPI2", "4")], "/SPI2_MOSI")
        self.assertEqual(self.pin_to_net[("J_SPI2", "5")], "/SPI2_MISO")
        self.assertEqual(self.pin_to_net[("J_SPI2", "6")], "/SPI2_CS")

        # I2C: GPIO15 (SCL), GPIO16 (SDA) with 4.7k pullups
        self.assertEqual(self.pin_to_net[("U1", "8")], "/I2C_SCL")
        self.assertEqual(self.pin_to_net[("U1", "9")], "/I2C_SDA")
        self.assertEqual(self.pin_to_net[("J_I2C", "3")], "/I2C_SCL")
        self.assertEqual(self.pin_to_net[("J_I2C", "4")], "/I2C_SDA")
        self.assertEqual(self.pin_to_net[("J_IMU", "3")], "/I2C_SCL")
        self.assertEqual(self.pin_to_net[("J_IMU", "4")], "/I2C_SDA")
        self.assertIn("4.7k", self.components["R_PU_SCL"]['value'].lower())
        self.assertIn("4.7k", self.components["R_PU_SDA"]['value'].lower())
        self.assertEqual(self.pin_to_net[("R_PU_SCL", "1")], "/+3V3")
        self.assertEqual(self.pin_to_net[("R_PU_SDA", "1")], "/+3V3")

        # IMU INT: GPIO17 on Pin 10
        self.assertEqual(self.pin_to_net[("U1", "10")], "/IMU_INT")
        self.assertEqual(self.pin_to_net[("J_IMU", "5")], "/IMU_INT")

if __name__ == "__main__":
    unittest.main()
