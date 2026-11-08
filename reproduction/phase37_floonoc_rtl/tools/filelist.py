"""Ordered source list from Bender.yml files (read as data), evaluating Bender target expressions."""
import sys, yaml, os, re
ACTIVE = {'rtl', 'verilator'}
def ev(expr):
    expr = expr.strip()
    m = re.match(r'^(all|any|not)\((.*)\)$', expr)
    if not m: return expr in ACTIVE
    op, body = m.group(1), m.group(2)
    parts, depth, cur = [], 0, ''
    for ch in body:
        if ch == ',' and depth == 0: parts.append(cur); cur = ''; continue
        depth += ch == '('; depth -= ch == ')'; cur += ch
    if cur.strip(): parts.append(cur)
    vals = [ev(p) for p in parts]
    return all(vals) if op == 'all' else any(vals) if op == 'any' else not vals[0]
def files(root):
    d = yaml.safe_load(open(os.path.join(root, 'Bender.yml')))
    out = []
    def walk(items, ok=True):
        for it in items or []:
            if isinstance(it, str):
                if ok: out.append(os.path.join(root, it))
            elif isinstance(it, dict):
                t = it.get('target'); walk(it.get('files', []), ok and (t is None or ev(str(t))))
    walk(d.get('sources', []))
    return out, [os.path.join(root, x) for x in d.get('export_include_dirs', [])]
allf, allinc = [], []
for root in sys.argv[1:]:
    f, i = files(root); allf += f; allinc += i
print('INC ' + ' '.join(allinc))
for f in allf: print(f)
