# -*- coding: utf-8 -*-

import json
import datetime
import turbotlib
import requests
import xlrd

turbotlib.log("Starting run...") # Optional debug logging

FINMA_URL = 'https://www.finma.ch/institute/xls_d/dbeh.xlsx'
HEADER_ROW_NUM = 3

def get_rows(file_path=None, content=None):
    if content is not None:
        workbook = xlrd.open_workbook(file_contents=content)
    else:
        workbook = xlrd.open_workbook(file_path)

    worksheet = workbook.sheet_by_index(0)
    # Extract the row headers
    header_row = worksheet.row_values(HEADER_ROW_NUM)
    rows = []
    for row_num in range(HEADER_ROW_NUM + 1, worksheet.nrows):
        rows.append(dict(zip(
            header_row,
            worksheet.row_values(row_num)
        )))
    return rows

r = requests.get(FINMA_URL)
data = get_rows(content=r.content)

for d in data:
    if d['Name'] and len(d['Name']) and not d['Name'].startswith('Total bewilligte Banken und Effekte'):
        d.pop(None)
        d['sample_date'] = datetime.datetime.now().isoformat()
        d['source_url'] = FINMA_URL
        print json.dumps(d)
