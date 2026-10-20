"""Reproduce one formatted editable Source Data spreadsheet per plotted figure.
Uses artifact_tool; unmodified numerical rows originate from figures.py JSON.
"""
import json
import math
from pathlib import Path
from artifact_tool import Workbook, SpreadsheetFile
D=Path(__file__).resolve().parent/'outputs'/'source_data'

def main():
 for f in sorted(D.glob('*Fig*.json')):
  data=json.load(open(f)); wb=Workbook.create()
  for panel,tab in data.items():
   sh=wb.worksheets.add(panel[:31]);cols=tab['columns'];rows=tab['rows']
   # Some source data have mixed data types and missing entries; normalize NaN and nested values.
   clean=lambda x: (None if isinstance(x,float) and not math.isfinite(x) else (json.dumps(x,ensure_ascii=False) if isinstance(x,(dict,list)) else x))
   matrix=[list(map(clean,cols))]+[[clean(v) for v in row] for row in rows]
   if not matrix[0]:continue
   n=max(len(row) for row in matrix)
   matrix=[row+[None]*(n-len(row)) for row in matrix]
   sh.get_range_by_indexes(0,0,len(matrix),n).values=matrix
   sh.get_range_by_indexes(0,0,1,n).format={"fill":"#183E53","font":{"color":"#FFFFFF","bold":True},"row_height":26,"wrap_text":True}
   sh.get_range_by_indexes(0,0,len(matrix),n).format.column_width=20
   sh.get_range_by_indexes(0,0,len(matrix),n).format.row_height=18
   sh.get_range_by_indexes(0,0,1,n).format.row_height=30
   if tab.get('note'):
    sh.get_range_by_indexes(len(matrix)+1,0,1,1).values=[[str(tab['note'])[:5000]]]
   sh.freeze_panes.freeze_rows(1)
  out=D/f'Source_Data_{f.stem}.xlsx'
  SpreadsheetFile.export_xlsx(wb).save(str(out));print('wrote',out.name)
if __name__=='__main__':main()
