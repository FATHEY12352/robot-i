import sys
import os

sys.path.insert(0, r"D:\projekt\ARM\PCB\V4\tests")
import kicad_parser

with open(r"D:\projekt\ARM\PCB\V4\V4.net", "r", encoding="utf-8") as f:
    ast = kicad_parser.parse_sexpr(f.read())

nets_node = kicad_parser.find_subnode(ast, "nets")
comp_node = kicad_parser.find_subnode(ast, "components")

comps = {}
for c in kicad_parser.find_subnodes(comp_node, "comp"):
    ref = kicad_parser.find_subnode(c, "ref")[1]
    val = kicad_parser.find_subnode(c, "value")[1] if kicad_parser.find_subnode(c, "value") else ""
    comps[ref] = val

target_nets = [
    "/GATE_PROT", "/FB_3V3", "/FB_SERVO", "/VSET", "/ISET", "/NTC",
    "/IPROPI1", "/IPROPI2", "/CC1", "/CC2", "/+3V3", "/+6V", "/+6V_BUCK",
    "/V_SERVO", "/VMOT", "/VBUS", "/VBAT", "/VBAT_RAW", "/VBAT_LOGIC", "/GND", "/PGND"
]

print("=== DETAILED NET CONNECTIONS ===")
for target in target_nets:
    found = False
    for n in kicad_parser.find_subnodes(nets_node, "net"):
        name = kicad_parser.find_subnode(n, "name")[1]
        if name == target:
            found = True
            nodes = kicad_parser.find_subnodes(n, "node")
            print(f"\nNet {target} ({len(nodes)} nodes):")
            for nd in nodes:
                r = kicad_parser.find_subnode(nd, "ref")[1]
                p = kicad_parser.find_subnode(nd, "pin")[1]
                fn = kicad_parser.find_subnode(nd, "pinfunction")
                fn_str = fn[1] if fn else ""
                tp = kicad_parser.find_subnode(nd, "pintype")
                tp_str = tp[1] if tp else ""
                val = comps.get(r, "")
                print(f"   {r:12s} pin {p:4s} val={val:15s} func={fn_str:12s} type={tp_str}")
    if not found:
        print(f"\nNet {target}: NOT FOUND!")
