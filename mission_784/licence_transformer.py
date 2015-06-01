import sys
import json

while True:
    line = sys.stdin.readline()
    if not line:
        break

    raw_record = json.loads(line)

    licence_record = {
        "company_name": raw_record['NAME'],
        "license_number": raw_record['NUM. LIC.'],
        "company_jurisdiction": 'Puerto Rico',
        "licence_jurisdiction": 'Puerto Rico',
        "source_url": raw_record['source_url'],
        "sample_date": raw_record['sample_date'],
        "jurisdiction_classification": raw_record['classification'],
        "category": 'Financial',
        "confidence": 'HIGH',
        "regulator": 'Oficina del Comisionado de Instituciones Financieras',
    }

    print json.dumps(licence_record)
