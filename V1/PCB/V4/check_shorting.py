with open(r'D:\projekt\ARM\PCB\V4\test_clean_power_drc.rpt') as f:
    text = f.read()

import re
matches = re.findall(r'(\[shorting_items\].*?\n(?:    .*?\n)+)', text)
print(f"Total shorting_items: {len(matches)}")
for m in matches:
    print(m)
