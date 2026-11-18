with open(r'D:\projekt\ARM\PCB\V4\test_clean_power_drc.rpt') as f:
    text = f.read()

import re
matches = re.findall(r'(\[items_not_allowed\].*?\n(?:    .*?\n)+)', text)
for m in matches:
    print(m)
