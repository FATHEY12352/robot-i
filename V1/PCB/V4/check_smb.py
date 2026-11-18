with open(r'D:\projekt\ARM\PCB\V4\test_power_drc.rpt') as f:
    text = f.read()

import re
matches = re.findall(r'(\[solder_mask_bridge\].*?\n(?:    .*?\n)+)', text)
print(f"Total solder_mask_bridge: {len(matches)}")
for m in matches[:5]:
    print(m)
