"""Bounded Excel/CSV helper so DOST stops writing one-off openpyxl snippets.

  python excel_tools.py info  FILE                      sheets, size, headers
  python excel_tools.py head  FILE [--sheet S] [--n 10] [--cols A,B,Status]
  python excel_tools.py find  FILE TEXT [--sheet S]     rows containing TEXT (case-insensitive), max 30
  python excel_tools.py count FILE COLUMN [--sheet S]   value counts of one column
  python excel_tools.py dupes FILE COLUMN [--sheet S]   duplicate values (normalised: lower, trimmed, no www/http)
  python excel_tools.py append FILE ROWS.json [--sheet S]   append list of {header: value}; makes a backup first
  python excel_tools.py tocsv FILE OUT.csv [--sheet S]

Works on .xlsx/.xlsm (openpyxl), .csv. Long cell text is cut to --width chars (default 60).
"""
import sys, os, csv, json, shutil, argparse, collections, datetime as dt, re


def load(path, sheet=None, read_only=True):
    """Return (sheet names, header list, row iterator of tuples)."""
    if path.lower().endswith('.csv'):
        rows = list(csv.reader(open(path, encoding='utf-8-sig', newline='')))
        return ['csv'], rows[0] if rows else [], iter(rows[1:])
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=read_only, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    hdr = [str(c) if c is not None else '' for c in next(it, [])]
    return wb.sheetnames, hdr, it


def cut(v, w):
    s = '' if v is None else (v.date().isoformat() if isinstance(v, dt.datetime) and not v.time().hour else str(v))
    s = s.replace('\n', ' ')
    return s if len(s) <= w else s[:w - 1] + '~'


def col_idx(hdr, name):
    if name in hdr: return hdr.index(name)
    low = [h.lower() for h in hdr]
    if name.lower() in low: return low.index(name.lower())
    if re.fullmatch(r'[A-Za-z]{1,2}', name):
        from openpyxl.utils import column_index_from_string
        return column_index_from_string(name.upper()) - 1
    sys.exit(f'column {name!r} not found. Headers: {hdr}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['info', 'head', 'find', 'count', 'dupes', 'append', 'tocsv'])
    ap.add_argument('file'); ap.add_argument('arg', nargs='?')
    ap.add_argument('--sheet'); ap.add_argument('--n', type=int, default=10); ap.add_argument('--cols'); ap.add_argument('--width', type=int, default=60)
    a = ap.parse_args()
    if not os.path.exists(a.file): sys.exit(f'not found: {a.file}')

    if a.cmd == 'info':
        if a.file.lower().endswith('.csv'):
            names, hdr, it = load(a.file); print(f'csv rows={sum(1 for _ in it)} cols={len(hdr)}'); print('headers:', hdr); return
        import openpyxl
        wb = openpyxl.load_workbook(a.file, read_only=True)
        for ws in wb.worksheets:
            hdr = [c for c in next(ws.iter_rows(max_row=1, values_only=True), [])]
            print(f'[{ws.title}] rows~{ws.max_row} cols~{ws.max_column} headers: {[h for h in hdr if h is not None][:40]}')
        return

    names, hdr, it = load(a.file, a.sheet)
    if a.cmd == 'head':
        idx = [col_idx(hdr, c.strip()) for c in a.cols.split(',')] if a.cols else list(range(len(hdr)))
        print(' | '.join(cut(hdr[i], a.width) for i in idx))
        for k, r in enumerate(it):
            if k >= a.n: break
            print(' | '.join(cut(r[i] if i < len(r) else '', a.width) for i in idx))
    elif a.cmd == 'find':
        if not a.arg: sys.exit('find needs TEXT')
        t = a.arg.lower(); n = 0
        for k, r in enumerate(it, start=2):
            if any(t in str(v).lower() for v in r if v is not None):
                print(f'row {k}: ' + ' | '.join(f'{hdr[i]}={cut(v, a.width)}' for i, v in enumerate(r) if v not in (None, '') and i < len(hdr)))
                n += 1
                if n >= 30: print('... (30 shown, refine search)'); break
        print(n, 'match(es)')
    elif a.cmd in ('count', 'dupes'):
        if not a.arg: sys.exit(f'{a.cmd} needs COLUMN')
        i = col_idx(hdr, a.arg); vals = [r[i] if i < len(r) else None for r in it]
        if a.cmd == 'count':
            for v, c in collections.Counter(cut(v, a.width) for v in vals).most_common(40): print(f'{c:5}  {v}')
            print('rows', len(vals))
        else:
            norm = lambda v: re.sub(r'^(https?://)?(www\.)?', '', str(v).strip().lower()).rstrip('/')
            groups = collections.defaultdict(list)
            for k, v in enumerate(vals, start=2):
                if v not in (None, ''): groups[norm(v)].append(k)
            d = {k: v for k, v in groups.items() if len(v) > 1}
            for k, rows in list(d.items())[:50]: print(f'{k}  rows {rows}')
            print(len(d), 'duplicated value(s)')
    elif a.cmd == 'append':
        if a.file.lower().endswith('.csv'): sys.exit('append supports xlsx only')
        rows = json.load(open(a.arg, encoding='utf-8'))
        import openpyxl
        shutil.copy(a.file, re.sub(r'(\.xls[xm])$', f'.backup_{dt.date.today()}\\1', a.file))
        wb = openpyxl.load_workbook(a.file); ws = wb[a.sheet] if a.sheet else wb.worksheets[0]
        h = [c.value for c in ws[1]]
        unknown = sorted({k for r in rows for k in r} - set(h))
        if unknown: print('WARNING ignored keys:', unknown)
        for r in rows: ws.append([r.get(x, None) for x in h])
        wb.save(a.file); print(f'appended {len(rows)} to [{ws.title}] (backup made)')
    elif a.cmd == 'tocsv':
        if not a.arg: sys.exit('tocsv needs OUT.csv')
        with open(a.arg, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f); w.writerow(hdr); n = 0
            for r in it: w.writerow(['' if v is None else v for v in r]); n += 1
        print(f'wrote {n} rows to {a.arg}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
