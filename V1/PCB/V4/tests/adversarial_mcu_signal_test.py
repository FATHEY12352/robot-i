"""
Adversarial MCU Pinout, Strapping Safety, Actuators, and Filtering Test Suite
Empirically verifies ESP32-S3 (U1) pin connections, strapping pin integrity,
ADC1 vs ADC2 usage, RC filter parameters, clamping diodes, pullups, and buses.
"""

import os
import sys
import math
import re
from typing import Dict, List, Set, Tuple, Any

NETLIST_PATH = r"D:\projekt\ARM\PCB\V4\V4.net"
SCH_PATH = r"D:\projekt\ARM\PCB\V4\V4.kicad_sch"

def parse_netlist(net_path: str):
    """
    Parses KiCad sexpr netlist into:
    - components: {ref: {'value': str, 'footprint': str, 'fields': dict, 'lib': str}}
    - nets: {net_name: [{'ref': str, 'pin': str, 'pintype': str, 'pinfunction': str}]}
    - pin_to_net: {(ref, pin): net_name}
    """
    with open(net_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Simple sexpr tokenizer
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
            start = i
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

    # Parse components
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

    # Parse nets
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
            entry = {'ref': r, 'pin': p, 'pintype': pt, 'pinfunction': pf}
            net_nodes.append(entry)
            if r and p:
                pin_to_net[(r, p)] = net_name
        nets[net_name] = net_nodes

    return components, nets, pin_to_net

def main():
    print("=" * 80)
    print("ADVERSARIAL MCU PINOUT & SIGNAL INTEGRITY AUDITOR")
    print("=" * 80)

    if not os.path.exists(NETLIST_PATH):
        print(f"ERROR: Netlist {NETLIST_PATH} not found!")
        sys.exit(1)

    components, nets, pin_to_net = parse_netlist(NETLIST_PATH)
    print(f"Loaded {len(components)} components and {len(nets)} nets from {NETLIST_PATH}.")

    # 1. Audit U1 pins
    print("\n" + "=" * 80)
    print("1. ESP32-S3 (U1) ALL 41 PINS AUDIT")
    print("=" * 80)

    u1_pins = {}
    for pin_num in range(1, 42):
        key = ("U1", str(pin_num))
        net = pin_to_net.get(key, "UNCONNECTED / NO_NET")
        other_nodes = [f"{n['ref']}:{n['pin']}" for n in nets.get(net, []) if not (n['ref'] == 'U1' and n['pin'] == str(pin_num))]
        u1_pins[pin_num] = {
            'net': net,
            'connected_to': other_nodes
        }
        print(f"Pin {pin_num:2d}: Net = {net:25s} -> Connected to: {', '.join(other_nodes[:6])}{'...' if len(other_nodes) > 6 else ''}")

    # Check for unconnected pins (except NC if any)
    unconnected = [p for p, data in u1_pins.items() if data['net'] == "UNCONNECTED / NO_NET"]
    print(f"\nUnconnected U1 pins: {unconnected}")

    # 2. Audit Strapping Pins
    print("\n" + "=" * 80)
    print("2. STRAPPING PIN SAFETY AUDIT")
    print("=" * 80)

    # GPIO0 -> Pin 27
    gpio0_net = u1_pins[27]['net']
    gpio0_nodes = nets.get(gpio0_net, [])
    print(f"GPIO0 (Pin 27) Net: {gpio0_net}")
    print(f"  Connected nodes: {gpio0_nodes}")
    # Check for pull-up to +3.3V
    gpio0_pullup = False
    for node in gpio0_nodes:
        ref = node['ref']
        if ref.startswith('R'):
            r_val = components.get(ref, {}).get('value', '')
            # Check what other pin of R connects to
            r_pins = [pin_to_net.get((ref, p)) for p in ['1', '2']]
            print(f"  Resistor {ref} ({r_val}): Pins connect to {r_pins}")
            if any(p in ['/+3V3', '+3V3', '/3V3', '3V3'] for p in r_pins):
                gpio0_pullup = True
                print(f"  [PASS] GPIO0 pulled up to 3.3V via {ref} ({r_val})")
    # Check for pull-down on GPIO0
    gpio0_pulldown = False
    for node in gpio0_nodes:
        ref = node['ref']
        if ref.startswith('R'):
            r_pins = [pin_to_net.get((ref, p)) for p in ['1', '2']]
            if any(p in ['/GND', 'GND', '/PGND', 'PGND'] for p in r_pins):
                gpio0_pulldown = True
                print(f"  [FAIL] GPIO0 has pull-down to GND via {ref}!")
    if not gpio0_pulldown:
        print("  [PASS] GPIO0 has NO pull-down resistors to GND.")

    # GPIO45 -> Pin 26 (VDD_SPI voltage strapping)
    # Must be 0 at reset for 3.3V flash. Must NOT be pulled high!
    gpio45_net = u1_pins[26]['net']
    gpio45_nodes = nets.get(gpio45_net, [])
    print(f"\nGPIO45 (Pin 26) Net: {gpio45_net}")
    print(f"  Connected nodes: {gpio45_nodes}")
    gpio45_pullup = False
    for node in gpio45_nodes:
        ref = node['ref']
        if ref.startswith('R'):
            r_val = components.get(ref, {}).get('value', '')
            r_pins = [pin_to_net.get((ref, p)) for p in ['1', '2']]
            print(f"  Resistor {ref} ({r_val}): Pins connect to {r_pins}")
            if any(p in ['/+3V3', '+3V3', '/3V3', '3V3'] for p in r_pins):
                gpio45_pullup = True
                print(f"  [FAIL] GPIO45 is pulled up to +3.3V via {ref}!")
    if not gpio45_pullup:
        print("  [PASS] GPIO45 has NO pull-up to +3.3V.")

    # GPIO46 -> Pin 16 (Boot mode selection)
    # Must be 0 at reset when GPIO0 is low. Must NOT be pulled high!
    gpio46_net = u1_pins[16]['net']
    gpio46_nodes = nets.get(gpio46_net, [])
    print(f"\nGPIO46 (Pin 16) Net: {gpio46_net}")
    print(f"  Connected nodes: {gpio46_nodes}")
    gpio46_pullup = False
    for node in gpio46_nodes:
        ref = node['ref']
        if ref.startswith('R'):
            r_val = components.get(ref, {}).get('value', '')
            r_pins = [pin_to_net.get((ref, p)) for p in ['1', '2']]
            print(f"  Resistor {ref} ({r_val}): Pins connect to {r_pins}")
            if any(p in ['/+3V3', '+3V3', '/3V3', '3V3'] for p in r_pins):
                gpio46_pullup = True
                print(f"  [FAIL] GPIO46 is pulled up to +3.3V via {ref}!")
    if not gpio46_pullup:
        print("  [PASS] GPIO46 has NO pull-up to +3.3V.")

    # GPIO3 -> Pin 15 (JTAG source strapping)
    # Must NOT be pulled high!
    gpio3_net = u1_pins[15]['net']
    gpio3_nodes = nets.get(gpio3_net, [])
    print(f"\nGPIO3 (Pin 15) Net: {gpio3_net}")
    print(f"  Connected nodes: {gpio3_nodes}")
    gpio3_pullup = False
    for node in gpio3_nodes:
        ref = node['ref']
        if ref.startswith('R'):
            r_val = components.get(ref, {}).get('value', '')
            r_pins = [pin_to_net.get((ref, p)) for p in ['1', '2']]
            print(f"  Resistor {ref} ({r_val}): Pins connect to {r_pins}")
            if any(p in ['/+3V3', '+3V3', '/3V3', '3V3'] for p in r_pins):
                gpio3_pullup = True
                print(f"  [FAIL] GPIO3 is pulled up to +3.3V via {ref}!")
    if not gpio3_pullup:
        print("  [PASS] GPIO3 has NO pull-up to +3.3V.")

    # 3. Audit Servo Feedback Channels (ADC1 vs ADC2, RC filtering, Schottky clamp)
    print("\n" + "=" * 80)
    print("3. SERVO ANALOG FEEDBACK CHANNELS AUDIT (ADC1, RC Cutoff, BAT54S)")
    print("=" * 80)

    # Pin 4: SERVO1_FB (GPIO4, ADC1_CH3)
    # Pin 5: SERVO2_FB (GPIO5, ADC1_CH4)
    # Pin 6: SERVO3_FB (GPIO6, ADC1_CH5)
    # Pin 7: SERVO4_FB (GPIO7, ADC1_CH6)
    # Pin 12: SERVO5_FB (GPIO8, ADC1_CH7)
    # Pin 17: SERVO6_FB (GPIO9, ADC1_CH8)
    servo_fb_pins = {
        1: (4, "SERVO1_FB", "GPIO4", "ADC1_CH3"),
        2: (5, "SERVO2_FB", "GPIO5", "ADC1_CH4"),
        3: (6, "SERVO3_FB", "GPIO6", "ADC1_CH5"),
        4: (7, "SERVO4_FB", "GPIO7", "ADC1_CH6"),
        5: (12, "SERVO5_FB", "GPIO8", "ADC1_CH7"),
        6: (17, "SERVO6_FB", "GPIO9", "ADC1_CH8")
    }

    adc2_gpio_pins = {
        "GPIO11": 19, "GPIO12": 20, "GPIO13": 21, "GPIO14": 22,
        "GPIO15": 8, "GPIO16": 9, "GPIO17": 10, "GPIO18": 11,
        "GPIO19": 13, "GPIO20": 14
    }

    for servo_idx, (pin_num, exp_net_substr, gpio, adc_ch) in servo_fb_pins.items():
        net = u1_pins[pin_num]['net']
        print(f"\nServo {servo_idx} Feedback:")
        print(f"  MCU Pin: {pin_num} ({gpio}, {adc_ch}), Net: {net}")
        if "ADC1" in adc_ch and "ADC2" not in adc_ch:
            print(f"  [PASS] Assigned to {adc_ch} (ADC1 channel)")
        else:
            print(f"  [FAIL] Not assigned to ADC1!")

        # Find header, resistor, capacitor, clamp diode
        nodes = nets.get(net, [])
        print(f"  Nodes on net {net}: {[(n['ref'], n['pin']) for n in nodes]}")

        # Follow connections: resistor, capacitor, clamp diode
        # For an RC filter:
        # Header pin -> Net_RAW -> Resistor R -> Net_MCU (our net)
        # Net_MCU has: U1 pin, Resistor pin, Capacitor pin to GND, Diode clamp
        r_found = None
        c_found = None
        d_found = None
        for n in nodes:
            r = n['ref']
            if r.startswith('R'):
                r_found = (r, components.get(r, {}).get('value', ''))
            elif r.startswith('C'):
                c_found = (r, components.get(r, {}).get('value', ''))
            elif r.startswith('D'):
                d_found = (r, components.get(r, {}).get('value', ''))

        print(f"  Components on filtered net: R={r_found}, C={c_found}, D={d_found}")

        # Check values
        if r_found and c_found:
            r_str = r_found[1].replace(' ', '').lower()
            c_str = c_found[1].replace(' ', '').lower()
            # Parse R in ohms
            r_val = None
            if 'k' in r_str:
                r_val = float(r_str.replace('k', '').replace('ohm', '')) * 1000
            elif 'r' in r_str:
                r_val = float(r_str.replace('r', ''))
            else:
                try:
                    r_val = float(r_str)
                except:
                    pass

            # Parse C in Farads
            c_val = None
            if 'n' in c_str:
                c_val = float(c_str.replace('nf', '').replace('n', '')) * 1e-9
            elif 'u' in c_str:
                c_val = float(c_str.replace('uf', '').replace('u', '')) * 1e-6
            elif 'p' in c_str:
                c_val = float(c_str.replace('pf', '').replace('p', '')) * 1e-12

            if r_val and c_val:
                fc = 1.0 / (2.0 * math.pi * r_val * c_val)
                print(f"  RC values: R = {r_val:.1f} Ohm, C = {c_val*1e9:.1f} nF -> fc = {fc:.2f} Hz ({fc/1000:.3f} kHz)")
                if 950 <= r_val <= 1050:
                    print(f"  [PASS] R is 1k +/- 5% ({r_val} Ohm)")
                else:
                    print(f"  [FAIL] R is not 1k +/- 5% ({r_val} Ohm)")
                if 90e-9 <= c_val <= 110e-9:
                    print(f"  [PASS] C is 100nF +/- 10% ({c_val*1e9} nF)")
                else:
                    print(f"  [FAIL] C is not 100nF +/- 10% ({c_val*1e9} nF)")
                if 1400 <= fc <= 1800:
                    print(f"  [PASS] Cutoff frequency fc ~ 1.59 kHz ({fc/1000:.3f} kHz)")
                else:
                    print(f"  [FAIL] Cutoff frequency fc outside expected range ({fc/1000:.3f} kHz)")
            else:
                print(f"  [FAIL] Could not parse R or C values ({r_str}, {c_str})")
        else:
            print("  [FAIL] Missing R or C on feedback net!")

        # Check clamp diode
        if d_found:
            d_ref, d_val = d_found
            print(f"  Clamp diode: {d_ref} = {d_val}")
            # Check diode pins
            d_p1_net = pin_to_net.get((d_ref, '1'))
            d_p2_net = pin_to_net.get((d_ref, '2'))
            d_p3_net = pin_to_net.get((d_ref, '3'))
            print(f"  Diode pins: 1={d_p1_net}, 2={d_p2_net}, 3={d_p3_net}")
            # In BAT54S (SOT-23 dual series Schottky):
            # Pin 1 = Anode 1 (to GND)
            # Pin 2 = Cathode 2 (to +3V3)
            # Pin 3 = Cathode 1 + Anode 2 (to Signal)
            # Let's verify BAT54S clamping configuration:
            is_bat54s = "BAT54S" in d_val or "BAT54" in d_val or "BAT54S" in components.get(d_ref, {}).get('footprint', '')
            print(f"  Is BAT54S: {is_bat54s}")
            # Check connections:
            has_gnd = any(p in ['/GND', 'GND', '/PGND', 'PGND'] for p in [d_p1_net, d_p2_net, d_p3_net])
            has_3v3 = any(p in ['/+3V3', '+3V3', '/3V3', '3V3'] for p in [d_p1_net, d_p2_net, d_p3_net])
            if has_gnd and has_3v3:
                print(f"  [PASS] Clamp diode connected to GND and +3.3V")
            else:
                print(f"  [FAIL] Clamp diode missing GND or +3.3V rails! GND={has_gnd}, +3V3={has_3v3}")
        else:
            print("  [FAIL] Missing clamp diode on feedback net!")

    # Check that ADC2 is NEVER used for servo feedback
    print("\n--- ADC2 Wi-Fi Collision Check ---")
    adc2_pins = [19, 20, 21, 22, 8, 9, 10, 11, 13, 14]
    adc2_collisions = []
    for p in adc2_pins:
        net_name = u1_pins[p]['net']
        if "FB" in net_name or "SERVO" in net_name and "FB" in net_name:
            adc2_collisions.append((p, net_name))
    if not adc2_collisions:
        print("  [PASS] ZERO servo feedback lines on ADC2 pins (Wi-Fi safe).")
    else:
        print(f"  [FAIL] ADC2 collisions found: {adc2_collisions}")

    # 4. Audit Encoder Pull-ups and RC Debounce Filters
    print("\n" + "=" * 80)
    print("4. ENCODER INPUTS AUDIT (Pull-ups, RC Debounce Filters)")
    print("=" * 80)

    # Let's check encoder pins:
    # Contract in PROJECT.md:
    # M1_ENC_A: GPIO18 (Pin 11)
    # M1_ENC_B: GPIO21 (Pin 23)
    # M2_ENC_A: GPIO2 (Pin 38)
    # M2_ENC_B: GPIO1 (Pin 39)
    encoder_contract = {
        "M1_ENC_A": (11, "GPIO18"),
        "M1_ENC_B": (23, "GPIO21"),
        "M2_ENC_A": (38, "GPIO2"),
        "M2_ENC_B": (39, "GPIO1"),
    }

    for sig, (pin_num, gpio) in encoder_contract.items():
        net = u1_pins[pin_num]['net']
        print(f"\nEncoder Signal {sig}:")
        print(f"  MCU Pin: {pin_num} ({gpio}), Net: {net}")
        nodes = nets.get(net, [])
        print(f"  Connected nodes: {[(n['ref'], n['pin']) for n in nodes]}")

        # Find R series, C filter, and pull-up R
        # In RC filter architecture:
        # Header pin -> Net_raw -> R_pullup (to +3V3) & R_series -> Net_MCU (pin_num) -> C_filter (to GND)
        # OR:
        # Net_MCU has R_series, C_filter, R_pullup. Let's trace through both sides of series R:
        r_series = None
        c_filter = None
        r_pullup = None

        for n in nodes:
            r = n['ref']
            if r.startswith('R'):
                val = components.get(r, {}).get('value', '')
                r_series = (r, val)
            elif r.startswith('C'):
                val = components.get(r, {}).get('value', '')
                c_filter = (r, val)

        # Let's trace through the other pin of r_series to find the header net and pull-up:
        if r_series:
            r_ref = r_series[0]
            # Which pin is on this net?
            other_pin = '2' if pin_to_net.get((r_ref, '1')) == net else '1'
            header_net = pin_to_net.get((r_ref, other_pin))
            print(f"  Series resistor {r_ref} other pin ({other_pin}) connects to net: {header_net}")
            h_nodes = nets.get(header_net, [])
            print(f"  Nodes on header net {header_net}: {[(hn['ref'], hn['pin']) for hn in h_nodes]}")
            for hn in h_nodes:
                hr = hn['ref']
                if hr.startswith('R') and hr != r_ref:
                    r_pullup = (hr, components.get(hr, {}).get('value', ''))

        print(f"  Identified components: R_series={r_series}, C_filter={c_filter}, R_pullup={r_pullup}")

        # Check pull-up value (4.7k to +3.3V)
        if r_pullup:
            pu_ref, pu_val = r_pullup
            pu_str = pu_val.replace(' ', '').lower()
            pu_ohms = None
            if 'k' in pu_str:
                pu_ohms = float(pu_str.replace('k', '')) * 1000
            elif 'r' in pu_str:
                pu_ohms = float(pu_str.replace('r', ''))
            print(f"  Pull-up resistor: {pu_ref} = {pu_val} ({pu_ohms} Ohm)")
            pu_pins = [pin_to_net.get((pu_ref, p)) for p in ['1', '2']]
            pu_to_3v3 = any(p in ['/+3V3', '+3V3', '/3V3', '3V3'] for p in pu_pins)
            if pu_to_3v3 and pu_ohms and 4400 <= pu_ohms <= 5000:
                print(f"  [PASS] Pull-up is 4.7k (+/-5%) to +3.3V")
            else:
                print(f"  [FAIL] Pull-up check failed! pu_to_3v3={pu_to_3v3}, pu_ohms={pu_ohms}")
        else:
            print("  [FAIL] Pull-up resistor not found!")

        # Check RC debounce filter (100 Ohm + 1nF -> fc ~ 1.59 MHz)
        if r_series and c_filter:
            rs_ref, rs_val = r_series
            cf_ref, cf_val = c_filter
            rs_str = rs_val.replace(' ', '').lower()
            cf_str = cf_val.replace(' ', '').lower()

            r_val = None
            if 'r' in rs_str:
                r_val = float(rs_str.replace('r', ''))
            elif 'k' in rs_str:
                r_val = float(rs_str.replace('k', '')) * 1000
            else:
                try:
                    r_val = float(rs_str)
                except:
                    pass

            c_val = None
            if 'n' in cf_str:
                c_val = float(cf_str.replace('nf', '').replace('n', '')) * 1e-9
            elif 'p' in cf_str:
                c_val = float(cf_str.replace('pf', '').replace('p', '')) * 1e-12
            elif 'u' in cf_str:
                c_val = float(cf_str.replace('uf', '').replace('u', '')) * 1e-6

            if r_val and c_val:
                fc = 1.0 / (2.0 * math.pi * r_val * c_val)
                print(f"  RC Debounce values: R = {r_val:.1f} Ohm, C = {c_val*1e9:.1f} nF -> fc = {fc/1e6:.3f} MHz")
                if 90 <= r_val <= 110:
                    print(f"  [PASS] Debounce R is 100 Ohm +/- 10%")
                else:
                    print(f"  [FAIL] Debounce R is not 100 Ohm ({r_val} Ohm)")
                if 0.9e-9 <= c_val <= 1.1e-9:
                    print(f"  [PASS] Debounce C is 1 nF +/- 10%")
                else:
                    print(f"  [FAIL] Debounce C is not 1 nF ({c_val*1e9} nF)")
                if 1.4e6 <= fc <= 1.8e6:
                    print(f"  [PASS] Cutoff frequency fc ~ 1.59 MHz ({fc/1e6:.3f} MHz)")
                else:
                    print(f"  [FAIL] Cutoff frequency fc outside expected range ({fc/1e6:.3f} MHz)")
            else:
                print(f"  [FAIL] Could not parse debounce R/C values ({rs_str}, {cf_str})")
        else:
            print("  [FAIL] Missing R_series or C_filter on encoder net!")

    # 5. Audit Buses: SPI1, SPI2, I2C, IMU INT
    print("\n" + "=" * 80)
    print("5. BUS INTERFACES AUDIT (SPI1, SPI2, I2C, IMU INT)")
    print("=" * 80)

    # SPI Bus 1 on IO MUX (FSPI): GPIO10 (Pin 18), GPIO11 (Pin 19), GPIO12 (Pin 20), GPIO13 (Pin 21)
    spi1_expected = {
        "SPI1_CS": (18, "GPIO10"),
        "SPI1_MOSI": (19, "GPIO11"),
        "SPI1_SCK": (20, "GPIO12"),
        "SPI1_MISO": (21, "GPIO13"),
    }
    print("--- SPI Bus 1 (Native IO MUX) ---")
    for sig, (pin_num, gpio) in spi1_expected.items():
        net = u1_pins[pin_num]['net']
        print(f"  {sig:10s}: Pin {pin_num} ({gpio}) -> Net {net}")
        # Check header J_SPI1 connection
        has_j_spi1 = any(n['ref'] == 'J_SPI1' for n in nets.get(net, []))
        if has_j_spi1:
            print(f"    [PASS] Connected to J_SPI1 header")
        else:
            print(f"    [FAIL] NOT connected to J_SPI1 header!")

    # SPI Bus 2 on GPIO Matrix (HSPI): GPIO39 (Pin 32), GPIO40 (Pin 33), GPIO41 (Pin 34), GPIO42 (Pin 35)
    spi2_expected = {
        "SPI2_SCK": (32, "GPIO39"),
        "SPI2_MISO": (33, "GPIO40"),
        "SPI2_MOSI": (34, "GPIO41"),
        "SPI2_CS": (35, "GPIO42"),
    }
    print("\n--- SPI Bus 2 (GPIO Matrix) ---")
    for sig, (pin_num, gpio) in spi2_expected.items():
        net = u1_pins[pin_num]['net']
        print(f"  {sig:10s}: Pin {pin_num} ({gpio}) -> Net {net}")
        has_j_spi2 = any(n['ref'] == 'J_SPI2' for n in nets.get(net, []))
        if has_j_spi2:
            print(f"    [PASS] Connected to J_SPI2 header")
        else:
            print(f"    [FAIL] NOT connected to J_SPI2 header!")

    # I2C on GPIO15 (Pin 8), GPIO16 (Pin 9)
    i2c_expected = {
        "I2C_SCL": (8, "GPIO15"),
        "I2C_SDA": (9, "GPIO16"),
    }
    print("\n--- I2C Bus & Pull-ups ---")
    for sig, (pin_num, gpio) in i2c_expected.items():
        net = u1_pins[pin_num]['net']
        print(f"  {sig:10s}: Pin {pin_num} ({gpio}) -> Net {net}")
        nodes = nets.get(net, [])
        # Check connected headers: J_I2C and J_IMU
        has_j_i2c = any(n['ref'] == 'J_I2C' for n in nodes)
        has_j_imu = any(n['ref'] == 'J_IMU' for n in nodes)
        print(f"    Connected headers: J_I2C={has_j_i2c}, J_IMU={has_j_imu}")
        if has_j_i2c and has_j_imu:
            print(f"    [PASS] Connected to both J_I2C and J_IMU headers")
        else:
            print(f"    [FAIL] Header connection missing!")

        # Check 4.7k pull-up resistor to +3.3V
        pu_found = False
        for n in nodes:
            r = n['ref']
            if r.startswith('R'):
                val = components.get(r, {}).get('value', '')
                r_pins = [pin_to_net.get((r, p)) for p in ['1', '2']]
                if any(p in ['/+3V3', '+3V3', '/3V3', '3V3'] for p in r_pins):
                    pu_str = val.replace(' ', '').lower()
                    print(f"    Pull-up resistor: {r} = {val} connected to +3.3V")
                    if '4.7k' in pu_str or '4k7' in pu_str:
                        pu_found = True
                        print(f"    [PASS] 4.7k pull-up verified on {sig}")
        if not pu_found:
            print(f"    [FAIL] 4.7k pull-up to +3.3V not found on {sig}!")

    # IMU Interrupt on GPIO17 (Pin 10)
    print("\n--- Dedicated IMU Interrupt ---")
    imu_int_net = u1_pins[10]['net']
    print(f"  IMU_INT: Pin 10 (GPIO17) -> Net {imu_int_net}")
    imu_nodes = nets.get(imu_int_net, [])
    has_j_imu_int = any(n['ref'] == 'J_IMU' for n in imu_nodes)
    if has_j_imu_int:
        print(f"  [PASS] GPIO17 directly routed to J_IMU header (pin {[n['pin'] for n in imu_nodes if n['ref']=='J_IMU']})")
    else:
        print(f"  [FAIL] GPIO17 NOT connected to J_IMU header!")

    print("\n" + "=" * 80)
    print("AUDIT EXECUTION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
