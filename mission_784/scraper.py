# -*- coding: utf-8 -*-

import json
import datetime
import turbotlib
import requests
import urlparse
import re
from BeautifulSoup import BeautifulSoup

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter, PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTFigure, LTImage, LTTextLineHorizontal, LTTextBoxHorizontal, LTChar, LTRect, LTLine, LTAnno, LTCurve
from pdfminer.pdfpage import PDFPage
from cStringIO import StringIO

from pprint import pprint

turbotlib.log("Starting run...") # Optional debug logging

URL_WITH_PDF_LINKS = 'http://www.ocif.gobierno.pr/concesionariosbusqueda_eng.htm'

# Basic idea of the pdf parser is from https://blog.scraperwiki.com/2012/06/pdf-table-extraction-of-a-table/

config = {
    u'documents/cons/IA.pdf': {
        'enabled': False,
        'unique_column_name': 'LIC.NUM.',
        'name_column_name': u'NAME',
        'merge': False,
        'merge_indexes': [],
        'headers': [u'NAME', '', u'LIC.NUM.', u'CONTACT', u'ADDRESS', u'NEXTRENEWAL', u'CRD. #', u'TELEPHONEAND FAX', ''],
        'total_title': 'GRAND TOTAL:',
    },
    u'documents/cons/BROKERDEALER.pdf': {
        'enabled': True,
        'remove': -1,
        'unique_column_name': u'LIC.NUM.',
        'name_column_name': u'NAME',
        'merge': True,
        'merge_indexes': [],
        'headers': [u'NAME', '', u'LIC.NUM.', u'ADDRESS', u'NEXTRENEWAL', u'CRD. #', u'TELEPHONEAND FAX', u'BRANCHES', u'CONTACT', ''],
        'total_title': 'GRAND TOTAL:',
    },
    'default': {
        'enabled': True,
        'remove': -5,
        'unique_column_name': 'NUM. LIC.',
        'name_column_name': u'NOMBRE INSTITUCI\xd3N',
        'merge': True,
        'merge_indexes': [1],
        'headers': [u'NOMBRE INSTITUCI\xd3N', u'DBA', u'DIRECCI\xd3N', u'CIUDAD', u'ZIPCODE', u'TEL.', u'FECHA LIC.', u'NUM. LIC.', ''],
        'total_title': 'GRAN TOTAL:',
    }
}

def get_list_of_pdfs():
    pdf_links = {}

    r = requests.get(URL_WITH_PDF_LINKS)
    page = BeautifulSoup(r.text)
    for link in page.findAll('a', href=True):
        if (re.search('documents/cons/.*\.pdf', link['href']) and link['href'] not in pdf_links):
            pdf_links[link['href']] = {
                'url': urlparse.urljoin(URL_WITH_PDF_LINKS, link['href']),
                'title': " ".join(link.contents[0].split())
            }
    return pdf_links

def parse_page(layout, config=None):
    xset, yset = set(), set()
    tlines = [ ]
    objstack = list(reversed(layout._objs))
    while objstack:
        b = objstack.pop()
        if type(b) in [LTFigure, LTTextBox, LTTextLine, LTTextBoxHorizontal]:
            objstack.extend(reversed(b._objs))  # put contents of aggregate object into stack
        elif type(b) == LTTextLineHorizontal:
            tlines.append(b)
        elif type(b) in [LTLine]:
            if b.x0 == b.x1:
                xset.add(b.x0)
            elif b.y0 == b.y1:
                yset.add(b.y0)
            else:
                print "sloped line", b
        elif type(b) in [LTRect]: 
            if b.x1 - b.x0 < 2.0:
                xset.add(b.y0)
            else:
                yset.add(b.x0)
        elif type(b) == LTImage:
            continue
        else:
            turbotlib.log('Unregognized type: %s' % type(b))

    xlist = sorted(list(xset))
    ylist = sorted(list(yset))
    
    # initialize the output array of table text boxes
    boxes = [ [ [ ]  for xl in xlist ]  for yl in ylist ]
    
    for lt in tlines:
        y = (lt.y0+lt.y1)/2
        iy = Wposition(ylist, y)
        previx = None
        for lct in lt:
            if type(lct) == LTAnno:
                continue  # a junk element in LTTextLineHorizontal
            x = (lct.x0+lct.x1)/2
            ix = Wposition(xlist, x)
            if previx != ix:
                boxes[iy][ix].append([])  # begin new chain of characters
                previx = ix
            boxes[iy][ix][-1].append(lct.get_text())
    for iy in range(len(ylist)):
        for ix in range(len(xlist)):
            boxes[iy][ix] = [ "".join(s) for s in boxes[iy][ix] ]

    if 'remove' in config:
        del boxes[config['remove']:]
    
    headers = [ "".join(lh.strip() for lh in h).strip()  for h in boxes.pop() ]
    try:
        assert headers == config['headers']
    except AssertionError:
        turbotlib.log('Headers: %s' % headers)
        turbotlib.log('Headers (config): %s' % config['headers'])

    # merge entries where needed
    if config['merge']:
        name_column_index = headers.index(config['name_column_name'])
        unique_column_index = headers.index(config['unique_column_name'])
        for i, entry in enumerate(boxes):
            if headers[name_column_index+1] == '' and entry[name_column_index+1]:
                boxes[i][name_column_index][1:1] = boxes[i][name_column_index+1]

        for i, entry in enumerate(boxes):
            if (len(entry[unique_column_index]) == 0 or entry[unique_column_index][0].strip() == '' ) and boxes[i+1]:
               # if headers[name_column_index+1] == '' and boxes[i+1][name_column_index+1]:
               #      boxes[i+1][name_column_index].extend(boxes[i+1][name_column_index+1])
               if len(entry[name_column_index]) > 0 and entry[name_column_index][0] != config['total_title']:
                    boxes[i+1][name_column_index].extend(entry[name_column_index])
               for idx in config['merge_indexes']:
                   if len(entry[idx]) > 0:
                        boxes[i+1][idx].extend(entry[idx])

    box_list = []
    for row in boxes:
        if (row[0] != ''):
           box_list.append( dict(zip(headers, [ "".join(s) for s in row] )))
        
    return box_list

def Wposition(wlist, w):
    ilo, ihi = 0, len(wlist)
    while ilo < ihi -1:
        imid = (ilo + ihi) / 2
        if w < wlist[imid]:
            ihi = imid
        else:
            ilo = imid
    return ilo

class UnrecognizedTypeError(Exception):
    pass

def convert_pdf_to_dict(path=None, fp=None, config=None):
    if fp is None:
        fp = file(path, 'rb')
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    # device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos=set()
    boxes = []
    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching, check_extractable=True):
        interpreter.process_page(page)
        layout = device.get_result()
        try:
            boxes.extend(parse_page(layout, config))
        except UnrecognizedTypeError, e:
           print e
    boxes = [d for d in boxes if d[config['unique_column_name']].strip() != '' ]
    boxes = [ { k:v.strip() for k, v in d.iteritems() } for d in boxes ]
    fp.close()
    device.close()
    str = retstr.getvalue()
    retstr.close()
    return boxes

links = get_list_of_pdfs()
for k, v in links.iteritems():
    if (k in config):
        pdf_config = config[k]
    else:
       pdf_config = config['default']

    if not pdf_config['enabled']:
        continue
    turbotlib.log("Scrape '%s' from %s" % (v['title'], v['url']))
    pdf = requests.get(v['url'])
    data = convert_pdf_to_dict(fp=StringIO(pdf.content), config=pdf_config)
    for d in data:
        del d['']
        d['sample_date'] = datetime.datetime.now().isoformat()
        d['source_url'] = v['url']
        d['classification'] = v['title']
        d['NUM. LIC.'] = d[pdf_config['unique_column_name']]
        d['NAME'] = d[pdf_config['name_column_name']]
        print json.dumps(d)

turbotlib.log("End of scraping!")
