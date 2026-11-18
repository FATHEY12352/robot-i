import json

with open(r"D:\projekt\ARM\PCB\V4\V4.kicad_pro") as f:
    data = json.load(f)

severities = data.get("board", {}).get("design_settings", {}).get("rule_severities", {})
print("Current rule severities in V4.kicad_pro:")
for k, v in severities.items():
    print(f"  {k}: {v}")
