"""
KiCad Project & Manufacturing Artifacts Parser
Provides S-expression parsing, netlist querying, schematic inspection,
PCB layout geometry auditing, and manufacturing deliverable verification.
"""

import os
import re
import csv
import subprocess
from typing import List, Dict, Any, Optional, Tuple

KICAD_CLI_PATH = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
PYTHON_KICAD_PATH = r"C:\Program Files\KiCad\10.0\bin\python.exe"

# ---------------------------------------------------------------------------
# S-Expression Lexer & Parser
# ---------------------------------------------------------------------------

def parse_sexpr(text: str) -> List[Any]:
    """
    Parse an S-expression string into nested Python lists.
    Handles quoted strings, escaped characters, and whitespace.
    """
    tokens = []
    i = 0
    n = len(text)
    
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if c == '(':
            tokens.append('(')
            i += 1
        elif c == ')':
            tokens.append(')')
            i += 1
        elif c == '"':
            # Quoted string
            i += 1
            start = i
            chars = []
            while i < n:
                if text[i] == '\\' and i + 1 < n:
                    chars.append(text[i+1])
                    i += 2
                elif text[i] == '"':
                    break
                else:
                    chars.append(text[i])
                    i += 1
            tokens.append("".join(chars))
            i += 1
        else:
            # Atom (symbol or number)
            start = i
            while i < n and not text[i].isspace() and text[i] not in ('(', ')'):
                i += 1
            tokens.append(text[start:i])
            
    # Convert token list to nested structures
    def build_ast(token_iter):
        result = []
        for token in token_iter:
            if token == '(':
                result.append(build_ast(token_iter))
            elif token == ')':
                return result
            else:
                result.append(token)
        return result

    ast = build_ast(iter(tokens))
    return ast[0] if len(ast) == 1 and isinstance(ast[0], list) else ast

def find_subnodes(node: List[Any], tag: str) -> List[List[Any]]:
    """Return all direct child sublists whose first element is `tag`."""
    if not isinstance(node, list):
        return []
    return [item for item in node if isinstance(item, list) and len(item) > 0 and item[0] == tag]

def find_subnode(node: List[Any], tag: str) -> Optional[List[Any]]:
    """Return the first direct child sublist whose first element is `tag`."""
    if not isinstance(node, list):
        return None
    for item in node:
        if isinstance(item, list) and len(item) > 0 and item[0] == tag:
            return item
    return None

def find_recursive(node: List[Any], tag: str) -> List[List[Any]]:
    """Recursively search for all sublists whose first element is `tag`."""
    matches = []
    if not isinstance(node, list):
        return matches
    if len(node) > 0 and node[0] == tag:
        matches.append(node)
    for item in node:
        if isinstance(item, list):
            matches.extend(find_recursive(item, tag))
    return matches

# ---------------------------------------------------------------------------
# Schematic Inspection (.kicad_sch)
# ---------------------------------------------------------------------------

class SchematicData:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.exists = os.path.isfile(filepath)
        self.ast = []
        self.symbols: List[Dict[str, Any]] = []
        self.labels: List[Dict[str, Any]] = []
        self.wires: List[Dict[str, Any]] = []
        self.nets: Dict[str, List[str]] = {}
        if self.exists:
            self._load()

    def _load(self):
        with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        self.ast = parse_sexpr(content)
        self._extract_symbols()
        self._extract_labels()
        self._extract_wires()

    def _extract_symbols(self):
        symbol_nodes = find_recursive(self.ast, 'symbol')
        for s in symbol_nodes:
            # Filter only placed symbol instances, not library definitions
            # Placed symbols usually have (lib_id ...) and (at ...)
            lib_id_node = find_subnode(s, 'lib_id')
            at_node = find_subnode(s, 'at')
            if not lib_id_node or not at_node:
                continue

            sym_dict = {
                'lib_id': lib_id_node[1] if len(lib_id_node) > 1 else "",
                'properties': {},
                'pins': []
            }
            # Properties (Reference, Value, Footprint, Datasheet, etc.)
            prop_nodes = find_subnodes(s, 'property')
            for p in prop_nodes:
                if len(p) >= 3:
                    prop_name = p[1]
                    prop_val = p[2]
                    sym_dict['properties'][prop_name] = prop_val

            # Pins in symbol
            pin_nodes = find_recursive(s, 'pin')
            for pn in pin_nodes:
                if len(pn) >= 2:
                    pin_num = pn[1]
                    sym_dict['pins'].append(pin_num)

            sym_dict['reference'] = sym_dict['properties'].get('Reference', '')
            sym_dict['value'] = sym_dict['properties'].get('Value', '')
            sym_dict['footprint'] = sym_dict['properties'].get('Footprint', '')
            if sym_dict['reference']:
                self.symbols.append(sym_dict)

    def _extract_labels(self):
        for tag in ['label', 'global_label', 'hierarchical_label']:
            for node in find_recursive(self.ast, tag):
                if len(node) >= 2:
                    text = node[1]
                    at = find_subnode(node, 'at')
                    pos = (float(at[1]), float(at[2])) if at and len(at) >= 3 else (0.0, 0.0)
                    self.labels.append({
                        'type': tag,
                        'name': text,
                        'position': pos
                    })

    def _extract_wires(self):
        wire_nodes = find_recursive(self.ast, 'wire')
        for w in wire_nodes:
            pts = find_subnode(w, 'pts')
            if pts:
                xy_nodes = find_subnodes(pts, 'xy')
                coords = [(float(xy[1]), float(xy[2])) for xy in xy_nodes if len(xy) >= 3]
                self.wires.append({'pts': coords})

    def get_symbol_by_ref(self, ref_prefix: str) -> Optional[Dict[str, Any]]:
        for s in self.symbols:
            if s['reference'] == ref_prefix or s['reference'].startswith(ref_prefix):
                return s
        return None

    def get_symbols_by_ref_prefix(self, prefix: str) -> List[Dict[str, Any]]:
        return [s for s in self.symbols if s['reference'].startswith(prefix)]

    def has_label(self, label_name: str) -> bool:
        return any(l['name'] == label_name for l in self.labels)

# ---------------------------------------------------------------------------
# PCB Inspection (.kicad_pcb)
# ---------------------------------------------------------------------------

class PcbData:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.exists = os.path.isfile(filepath)
        self.ast = []
        self.nets: Dict[int, str] = {}
        self.footprints: List[Dict[str, Any]] = []
        self.tracks: List[Dict[str, Any]] = []
        self.vias: List[Dict[str, Any]] = []
        self.zones: List[Dict[str, Any]] = []
        self.edge_cuts: List[Dict[str, Any]] = []
        if self.exists:
            self._load()

    def _load(self):
        with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        self.ast = parse_sexpr(content)
        self._extract_nets()
        self._extract_footprints()
        self._extract_tracks_and_vias()
        self._extract_zones()
        self._extract_edge_cuts()

    def _extract_nets(self):
        net_nodes = find_subnodes(self.ast, 'net')
        for n in net_nodes:
            if len(n) >= 3:
                try:
                    net_idx = int(n[1])
                    net_name = str(n[2])
                    self.nets[net_idx] = net_name
                except (ValueError, TypeError):
                    pass

    def _extract_footprints(self):
        fp_nodes = find_recursive(self.ast, 'footprint')
        for fp in fp_nodes:
            fp_dict = {
                'name': fp[1] if len(fp) > 1 else "",
                'layer': "",
                'at': (0.0, 0.0, 0.0),
                'reference': "",
                'value': "",
                'pads': []
            }
            layer_node = find_subnode(fp, 'layer')
            if layer_node and len(layer_node) > 1:
                fp_dict['layer'] = layer_node[1]

            at_node = find_subnode(fp, 'at')
            if at_node and len(at_node) >= 3:
                x = float(at_node[1])
                y = float(at_node[2])
                rot = float(at_node[3]) if len(at_node) >= 4 else 0.0
                fp_dict['at'] = (x, y, rot)

            # Properties
            for prop in find_subnodes(fp, 'property'):
                if len(prop) >= 3:
                    if prop[1] == 'Reference':
                        fp_dict['reference'] = prop[2]
                    elif prop[1] == 'Value':
                        fp_dict['value'] = prop[2]

            # Pads
            for p in find_subnodes(fp, 'pad'):
                if len(p) >= 5:
                    pad_num = str(p[1])
                    pad_type = str(p[2])
                    pad_shape = str(p[3])
                    net_node = find_subnode(p, 'net')
                    net_id = -1
                    net_name = ""
                    if net_node and len(net_node) > 1:
                        try:
                            net_id = int(net_node[1])
                            net_name = str(net_node[2]) if len(net_node) > 2 else self.nets.get(net_id, "")
                        except (ValueError, TypeError):
                            net_id = -1
                            net_name = str(net_node[1])
                    fp_dict['pads'].append({
                        'number': pad_num,
                        'type': pad_type,
                        'shape': pad_shape,
                        'net_id': net_id,
                        'net_name': net_name
                    })

            if fp_dict['reference']:
                self.footprints.append(fp_dict)

    def _extract_tracks_and_vias(self):
        # Segments / Tracks
        for seg in find_recursive(self.ast, 'segment'):
            start = find_subnode(seg, 'start')
            end = find_subnode(seg, 'end')
            width = find_subnode(seg, 'width')
            layer = find_subnode(seg, 'layer')
            net = find_subnode(seg, 'net')
            net_id = 0
            if net and len(net) > 1:
                try:
                    net_id = int(net[1])
                except (ValueError, TypeError):
                    net_id = 0
            if start and end and width:
                self.tracks.append({
                    'start': (float(start[1]), float(start[2])),
                    'end': (float(end[1]), float(end[2])),
                    'width': float(width[1]),
                    'layer': layer[1] if layer and len(layer) > 1 else "",
                    'net_id': net_id
                })

        # Vias
        for via in find_recursive(self.ast, 'via'):
            at = find_subnode(via, 'at')
            size = find_subnode(via, 'size')
            drill = find_subnode(via, 'drill')
            layers = find_subnode(via, 'layers')
            net = find_subnode(via, 'net')
            via_net_id = 0
            if net and len(net) > 1:
                try:
                    via_net_id = int(net[1])
                except (ValueError, TypeError):
                    via_net_id = 0
            if at and size:
                self.vias.append({
                    'at': (float(at[1]), float(at[2])),
                    'size': float(size[1]),
                    'drill': float(drill[1]) if drill and len(drill) > 1 else 0.3,
                    'layers': layers[1:] if layers else [],
                    'net_id': via_net_id
                })

        # Built-in through-hole thermal via pads inside IC footprints (U1 Pad 41, U3 Pad 9, U5/U6 Pad 17)
        for fp in find_recursive(self.ast, 'footprint'):
            fp_at = find_subnode(fp, 'at')
            fx = float(fp_at[1]) if fp_at and len(fp_at) >= 2 else 0.0
            fy = float(fp_at[2]) if fp_at and len(fp_at) >= 3 else 0.0
            for pad in find_subnodes(fp, 'pad'):
                if len(pad) >= 3 and pad[2] == 'thru_hole':
                    pnum = str(pad[1])
                    if pnum in ['41', '9', '17']:
                        at = find_subnode(pad, 'at')
                        size = find_subnode(pad, 'size')
                        drill = find_subnode(pad, 'drill')
                        layers = find_subnode(pad, 'layers')
                        net = find_subnode(pad, 'net')
                        pad_net_id = 0
                        if net and len(net) > 1:
                            try:
                                pad_net_id = int(net[1])
                            except (ValueError, TypeError):
                                pad_net_id = 0
                        px = fx + (float(at[1]) if at and len(at) >= 2 else 0.0)
                        py = fy + (float(at[2]) if at and len(at) >= 3 else 0.0)
                        p_size = float(size[1]) if size and len(size) >= 2 else 0.6
                        p_drill = float(drill[1]) if drill and len(drill) >= 2 else 0.3
                        self.vias.append({
                            'at': (px, py),
                            'size': p_size,
                            'drill': p_drill,
                            'layers': layers[1:] if layers else [],
                            'net_id': pad_net_id
                        })

    def _extract_zones(self):
        for zone in find_recursive(self.ast, 'zone'):
            net_node = find_subnode(zone, 'net')
            net_name_node = find_subnode(zone, 'net_name')
            layers_node = find_subnode(zone, 'layers')
            zone_net_id = -1
            if net_node and len(net_node) > 1:
                try:
                    zone_net_id = int(net_node[1])
                except (ValueError, TypeError):
                    zone_net_id = -1
            self.zones.append({
                'net_id': zone_net_id,
                'net_name': net_name_node[1] if net_name_node and len(net_name_node) > 1 else "",
                'layers': layers_node[1:] if layers_node else []
            })

    def _extract_edge_cuts(self):
        for tag in ['gr_line', 'gr_arc', 'gr_rect', 'gr_circle']:
            for item in find_recursive(self.ast, tag):
                layer = find_subnode(item, 'layer')
                if layer and len(layer) > 1 and layer[1] == 'Edge.Cuts':
                    self.edge_cuts.append({'type': tag, 'raw': item})

    def get_footprint(self, ref: str) -> Optional[Dict[str, Any]]:
        for fp in self.footprints:
            if fp['reference'] == ref:
                return fp
        return None

# ---------------------------------------------------------------------------
# Manufacturing Deliverables Parsers
# ---------------------------------------------------------------------------

def parse_bom_csv(bom_path: str) -> List[Dict[str, str]]:
    """Parse KiCad generated Bill of Materials CSV."""
    if not os.path.isfile(bom_path):
        return []
    rows = []
    with open(bom_path, mode='r', encoding='utf-8', errors='ignore') as f:
        # Detect delimiter (comma or semicolon)
        sample = f.read(2048)
        f.seek(0)
        dialect = csv.excel
        if ';' in sample and sample.count(';') > sample.count(','):
            dialect = csv.excel_tab if '\t' in sample else csv.Sniffer().sniff(sample, delimiters=';,')
        reader = csv.DictReader(f, dialect=dialect)
        for r in reader:
            # Clean keys
            clean_row = {k.strip(): v.strip() for k, v in r.items() if k is not None}
            rows.append(clean_row)
    return rows

def parse_cpl_csv(cpl_path: str) -> List[Dict[str, str]]:
    """Parse Pick and Place (CPL / Centroid) CSV."""
    if not os.path.isfile(cpl_path):
        return []
    rows = []
    with open(cpl_path, mode='r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for r in reader:
            clean_row = {k.strip(): v.strip() for k, v in r.items() if k is not None}
            rows.append(clean_row)
    return rows

def audit_gerber_directory(gerber_dir: str) -> Dict[str, Any]:
    """Check existence and standard headers of exported Gerber & Drill files."""
    required_layers = {
        'F_Cu': ['*F_Cu.gbr', '*F.Cu.gbr'],
        'B_Cu': ['*B_Cu.gbr', '*B.Cu.gbr'],
        'F_Mask': ['*F_Mask.gbr', '*F.Mask.gbr'],
        'B_Mask': ['*B_Mask.gbr', '*B.Mask.gbr'],
        'F_Silkscreen': ['*F_Silkscreen.gbr', '*F.Silkscreen.gbr', '*F_Silk.gbr'],
        'B_Silkscreen': ['*B_Silkscreen.gbr', '*B.Silkscreen.gbr', '*B_Silk.gbr'],
        'Edge_Cuts': ['*Edge_Cuts.gbr', '*Edge.Cuts.gbr']
    }
    results = {
        'present_files': {},
        'missing_layers': [],
        'drill_files': [],
        'valid_headers': True
    }
    if not os.path.isdir(gerber_dir):
        results['missing_layers'] = list(required_layers.keys())
        return results

    files_in_dir = os.listdir(gerber_dir)
    for layer, patterns in required_layers.items():
        found = False
        for f in files_in_dir:
            for pat in patterns:
                pat_regex = re.compile(pat.replace('.', r'\.').replace('*', '.*'), re.IGNORECASE)
                if pat_regex.match(f):
                    found = True
                    results['present_files'][layer] = os.path.join(gerber_dir, f)
                    break
            if found:
                break
        if not found:
            results['missing_layers'].append(layer)

    # Drill files (.drl)
    for f in files_in_dir:
        if f.lower().endswith('.drl'):
            results['drill_files'].append(os.path.join(gerber_dir, f))

    # Header check on present gerber files (must contain %FSLAX or %TF.FileFunction)
    for l_path in results['present_files'].values():
        try:
            with open(l_path, 'r', encoding='utf-8', errors='ignore') as gf:
                content = gf.read(1024)
                if '%FSLAX' not in content and 'G04' not in content and '%TF.' not in content:
                    results['valid_headers'] = False
        except Exception:
            results['valid_headers'] = False

    return results

# ---------------------------------------------------------------------------
# KiCad CLI Native Verifiers (ERC & DRC)
# ---------------------------------------------------------------------------

def run_kicad_erc(sch_path: str, output_rpt: Optional[str] = None) -> Tuple[int, str]:
    """Execute `kicad-cli sch erc` and capture exit code and report."""
    if not os.path.isfile(KICAD_CLI_PATH):
        return -1, f"kicad-cli.exe not found at {KICAD_CLI_PATH}"
    if not os.path.isfile(sch_path):
        return -2, f"Schematic file {sch_path} not found"
        
    rpt_path = output_rpt or sch_path.replace('.kicad_sch', '_erc.rpt')
    cmd = [KICAD_CLI_PATH, "sch", "erc", "--output", rpt_path, sch_path]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        report_content = ""
        if os.path.isfile(rpt_path):
            with open(rpt_path, 'r', encoding='utf-8', errors='ignore') as rf:
                report_content = rf.read()
        return proc.returncode, report_content or proc.stdout + proc.stderr
    except Exception as e:
        return -3, str(e)

def run_kicad_drc(pcb_path: str, output_rpt: Optional[str] = None) -> Tuple[int, str]:
    """Execute `kicad-cli pcb drc` and capture exit code and report."""
    if not os.path.isfile(KICAD_CLI_PATH):
        return -1, f"kicad-cli.exe not found at {KICAD_CLI_PATH}"
    if not os.path.isfile(pcb_path):
        return -2, f"PCB file {pcb_path} not found"

    rpt_path = output_rpt or pcb_path.replace('.kicad_pcb', '_drc.rpt')
    cmd = [KICAD_CLI_PATH, "pcb", "drc", "--output", rpt_path, pcb_path]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
        report_content = ""
        if os.path.isfile(rpt_path):
            with open(rpt_path, 'r', encoding='utf-8', errors='ignore') as rf:
                report_content = rf.read()
        return proc.returncode, report_content or proc.stdout + proc.stderr
    except Exception as e:
        return -3, str(e)
