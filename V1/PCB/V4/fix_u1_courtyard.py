with open(r'D:\projekt\ARM\PCB\V4\V4.kicad_pcb', encoding='utf-8') as f:
    text = f.read()

import re
m = re.search(r'\(property\s+"Reference"\s+"U1"', text)
idx = m.start()
start_fp = text.rfind('(footprint ', 0, idx)
# find matching closing parenthesis for this footprint
count = 0
end_fp = start_fp
for i in range(start_fp, len(text)):
    if text[i] == '(':
        count += 1
    elif text[i] == ')':
        count -= 1
        if count == 0:
            end_fp = i + 1
            break

print(f"U1 footprint block from {start_fp} to {end_fp}")
u1_block = text[start_fp:end_fp]
print("Length:", len(u1_block))

# Find all fp_line on F.CrtYd
lines = re.findall(r'\(fp_line\s+.*?\(layer\s+"F\.CrtYd"\)\s+\(uuid\s+"[^"]+"\)\s+\)', u1_block, re.DOTALL)
print(f"Found {len(lines)} F.CrtYd lines")

# Remove them
new_block = u1_block
for l in lines:
    new_block = new_block.replace(l, "")

# Add 4 clean boundary lines
import uuid
pts = [(-9.75, -13.25), (9.75, -13.25), (9.75, 13.45), (-9.75, 13.45), (-9.75, -13.25)]
new_crtyd = ""
for i in range(4):
    new_crtyd += f"""\t\t(fp_line
\t\t\t(start {pts[i][0]} {pts[i][1]})
\t\t\t(end {pts[i+1][0]} {pts[i+1][1]})
\t\t\t(stroke
\t\t\t\t(width 0.05)
\t\t\t\t(type solid)
\t\t\t)
\t\t\t(layer "F.CrtYd")
\t\t\t(uuid "{uuid.uuid4()}")
\t\t)\n"""

last_paren = new_block.rfind(')')
new_block = new_block[:last_paren] + new_crtyd + '\t)'

new_text = text[:start_fp] + new_block + text[end_fp:]
with open(r'D:\projekt\ARM\PCB\V4\V4.kicad_pcb', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("U1 courtyard updated successfully!")
