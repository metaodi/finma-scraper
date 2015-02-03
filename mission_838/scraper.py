# -*- coding: utf-8 -*-

import json
import datetime
import turbotlib
import requests
import xlrd
import pprint

turbotlib.log("Starting run...") # Optional debug logging

def get_rows(content):
    workbook = xlrd.open_workbook(file_contents=content)
    worksheet = workbook.sheet_by_index(0)
    # Extract the row headers
    header_row = worksheet.row_values(3)
    print header_row
    rows = []
    for row_num in range(worksheet.nrows):
        # Data columns begin at row count 7 (8 in Excel)
        if row_num >= 3:
            rows.append(dict(zip(
                header_row,
                worksheet.row_values(row_num)
            )))
    return rows

FINMA_URL = 'https://www.finma.ch/institute/xls_d/dbeh.xlsx'
r = requests.get(FINMA_URL)
pprint.pprint(get_rows(r.content))

# for n in range(0,20):
#     data = {"number": n,
#             "company": "Company %s Ltd" % n,
#             "message": "Hello %s" % n,
#             "sample_date": datetime.datetime.now().isoformat(),
#             "source_url": "http://somewhere.com/%s" % n}
#     # The Turbot specification simply requires us to output lines of JSON
#     print json.dumps(data)
