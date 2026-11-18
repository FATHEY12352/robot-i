with open(r'D:\projekt\ARM\PCB\V4\test_clean_power_drc2.rpt') as f:
    text = f.read()

part = text.split('Found 146 DRC violations')[1].split('unconnected pads')[0]
from collections import Counter
import re
counts = Counter(re.findall(r'\[[a-zA-Z0-9_]+\]', part))
for k, v in counts.items():
    print(f'{k}: {v}')
