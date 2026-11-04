#!/usr/bin/env python3
"""Build lab/ESH27-Lab.xlsx from data/*.csv (one sheet per bank + dashboard).

Usage: python scripts/build_workbook.py
The CSVs are the source of truth; the workbook (and the Google Sheet mirror) are views.
"""
import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SHEETS = [
    ("Goals", "goals.csv"),
    ("CreativeProofs", "creative_proofs.csv"),
    ("Tools", "tools.csv"),
    ("WisdomProjects", "wisdom_projects.csv"),
]
NUMERIC = {"ai_tractability", "formalization_readiness", "progress_pct", "maturity", "feasibility", "year"}


def read(name):
    p = DATA / name
    if not p.exists():
        return None, []
    with p.open(encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]


def main():
    wb = Workbook()
    dash = wb.active
    dash.title = "Dashboard"
    head_fill = PatternFill("solid", fgColor="1F2A44")
    for title, fname in SHEETS:
        header, rows = read(fname)
        if header is None:
            continue
        ws = wb.create_sheet(title)
        ws.sheet_view.rightToLeft = False
        ws.append(header)
        for r in rows:
            out = []
            for h, v in zip(header, r):
                if h in NUMERIC and v.strip().lstrip("-").isdigit():
                    out.append(int(v))
                else:
                    out.append(v)
            ws.append(out)
        for i, h in enumerate(header, 1):
            c = ws.cell(row=1, column=i)
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = head_fill
            width = min(60, max(10, max((len(str(ws.cell(row=j, column=i).value or "")) for j in range(1, min(ws.max_row, 50) + 1)), default=10)))
            ws.column_dimensions[get_column_letter(i)].width = width
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "B2"
        if rows:
            ref = f"A1:{get_column_letter(len(header))}{len(rows) + 1}"
            t = Table(displayName=f"t{title}", ref=ref)
            t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
            ws.add_table(t)

    # Dashboard with live formulas over the Goals table
    dash["A1"] = "ESH27 Lab — Goal Bank Dashboard"
    dash["A1"].font = Font(bold=True, size=16)
    if "Goals" in wb.sheetnames:
        g = wb["Goals"]
        hdr = [c.value for c in g[1]]
        col = lambda name: get_column_letter(hdr.index(name) + 1)
        tier, status, prog = col("tier"), col("status"), col("progress_pct")
        n = g.max_row
        dash.append([])
        dash.append(["Tier", "Count", "Avg progress %"])
        for c in dash[3]:
            c.font = Font(bold=True)
        for t in ["A-Moonshot", "B-Famous-open", "C-Tractable", "D-Formalization", "P-Physics"]:
            r = dash.max_row + 1
            dash.append([t,
                         f'=COUNTIF(Goals!{tier}2:{tier}{n},A{r})',
                         f'=IFERROR(AVERAGEIF(Goals!{tier}2:{tier}{n},A{r},Goals!{prog}2:{prog}{n}),0)'])
        r = dash.max_row + 1
        dash.append(["Total", f"=COUNTA(Goals!A2:A{n})", f"=IFERROR(AVERAGE(Goals!{prog}2:{prog}{n}),0)"])
        dash.append([])
        dash.append(["Status = open (exact)", f'=COUNTIF(Goals!{status}2:{status}{n},"open*")'])
        dash.column_dimensions["A"].width = 22
        dash.column_dimensions["B"].width = 12
        dash.column_dimensions["C"].width = 16

    out = ROOT / "ESH27-Lab.xlsx"
    wb.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
