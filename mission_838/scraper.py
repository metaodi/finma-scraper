# -*- coding: utf-8 -*-

import json
import datetime
import turbotlib
import requests

turbotlib.log("Starting run...") # Optional debug logging


FINMA_URL = 'https://www.finma.ch/institute/xls_d/dbeh.xlsx'

r = requests.get(FINMA_URL)

# for n in range(0,20):
#     data = {"number": n,
#             "company": "Company %s Ltd" % n,
#             "message": "Hello %s" % n,
#             "sample_date": datetime.datetime.now().isoformat(),
#             "source_url": "http://somewhere.com/%s" % n}
#     # The Turbot specification simply requires us to output lines of JSON
#     print json.dumps(data)
