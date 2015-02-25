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
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTFigure, LTImage, LTTextLineHorizontal, LTTextBoxHorizontal, LTChar, LTRect, LTLine, LTAnno
from pdfminer.pdfpage import PDFPage
from cStringIO import StringIO

from pprint import pprint

turbotlib.log("Starting run...") # Optional debug logging

URL_WITH_PDF_LINKS = 'http://www.ocif.gobierno.pr/concesionariosbusqueda_eng.htm'

# Basic idea of the pdf parser is from https://blog.scraperwiki.com/2012/06/pdf-table-extraction-of-a-table/

def get_list_of_pdfs():
    pdf_links = []

    r = requests.get(URL_WITH_PDF_LINKS)
    page = BeautifulSoup(r.text)
    for link in page.findAll('a', href=True):
        if (re.search('documents/.*\.pdf', link['href'])):
            pdf_links.append(urlparse.urljoin(URL_WITH_PDF_LINKS, link['href']))

    return pdf_links

def parse_page(layout):
    xset, yset = set(), set()
    tlines = [ ]
    objstack = list(reversed(layout._objs))
    while objstack:
        b = objstack.pop()
        if type(b) in [LTFigure, LTTextBox, LTTextLine, LTTextBoxHorizontal]:
            objstack.extend(reversed(b._objs))  # put contents of aggregate object into stack
        elif type(b) == LTTextLineHorizontal:
            tlines.append(b)
        elif type(b) == LTLine:
            if b.x0 == b.x1:
                xset.add(b.x0)
            elif b.y0 == b.y1:
                yset.add(b.y0)
            else:
                print "sloped line", b
        elif type(b) == LTRect: 
            if b.x1 - b.x0 < 2.0:
                xset.add(b.y0)
            else:
                yset.add(b.x0)
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
    del boxes[-5:]

    headers = [ "".join(lh.strip() for lh in h).strip()  for h in boxes.pop() ]
    assert headers == [u'NOMBRE INSTITUCI\xd3N', u'DBA', u'DIRECCI\xd3N', u'CIUDAD', u'ZIPCODE', u'TEL.', u'FECHA LIC.', u'NUM. LIC.', ''] 

    # merge entries where needed
    for i, entry in enumerate(boxes):
        if (len(entry[7]) == 0 or entry[7][0].strip() == '' ) and boxes[i+1]:
           if len(entry[0]) > 0 and entry[0][0] != 'GRAN TOTAL:':
                boxes[i+1][0][0] += entry[0][0] 

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

def convert_pdf_to_dict(path=None, fp=None):
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
            boxes.extend(parse_page(layout))
        except UnrecognizedTypeError, e:
           print e
    boxes = [d for d in boxes if d[u'NUM. LIC.'].strip() != '' ]
    boxes = [ { k:v.strip() for k, v in d.iteritems() } for d in boxes ]
    fp.close()
    device.close()
    str = retstr.getvalue()
    retstr.close()
    return boxes

# links = get_list_of_pdfs()
# pprint(links)
# 
# pdf_url = requests.get(links[0])
# pdf_str = convert_pdf_to_txt(fp=StringIO(pdf_url.content))
data = convert_pdf_to_dict('/home/odi/Desktop/RC.pdf')

for d in data:
    d['sample_date'] = datetime.datetime.now().isoformat()
    d['source_url'] = URL_WITH_PDF_LINKS
    print json.dumps(d)
