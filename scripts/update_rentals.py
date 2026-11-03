"""Refresh publicly advertised rental listings. Respect robots.txt and use light requests."""
import datetime,json,re,time,urllib.parse,urllib.robotparser,xml.etree.ElementTree as ET
from pathlib import Path
import requests
from bs4 import BeautifulSoup
ROOT='https://www.landestate.co.uk'
UA='NadsRentalExplorer/1.0 (public listing metadata; respectful daily check)'
s=requests.Session();s.headers.update({'User-Agent':UA})
robots=urllib.robotparser.RobotFileParser();robots.set_url(ROOT+'/robots.txt')
try: robots.read()
except Exception as e: raise SystemExit('Could not check robots.txt: '+str(e))
def get(url):
 if not url.startswith(ROOT+'/') or not robots.can_fetch(UA,url):raise ValueError('Robots policy does not permit '+url)
 r=s.get(url,timeout=18);r.raise_for_status();time.sleep(1);return r.text
seen=set();urls=[]
def sitemap(url,depth=0):
 if depth>3 or url in seen:return
 seen.add(url)
 try: raw=get(url);root=ET.fromstring(raw)
 except Exception as e:print('Sitemap unavailable',url,e);return
 for e in root.iter():
  if e.tag.endswith('loc') and e.text:
   u=e.text.strip()
   if u.endswith('.xml') and u.startswith(ROOT):sitemap(u,depth+1)
   elif '/property-to-rent/' in u and u.startswith(ROOT):urls.append(u)
sitemap(ROOT+'/sitemap_index.xml');sitemap(ROOT+'/wp-sitemap.xml')
# Do not infer current inventory from old indexed property pages.
if not urls:raise SystemExit('No rental listing URLs discovered; preserving previous snapshot.')
properties=[]
for u in dict.fromkeys(urls):
 try:
  soup=BeautifulSoup(get(u),'html.parser')
  text=soup.get_text(' ',strip=True)
  if not re.search(r'\bTo Let\b',text,re.I) or re.search(r'\bLet Agreed\b|\bLet By\b',text[:900],re.I):continue
  h=soup.find('h1');title=h.get_text(' ',strip=True) if h else ''
  if not title:continue
  m=re.search(r'£[\d,]+\s*(?:pcm|pw|per month)',text,re.I)
  price=m.group(0) if m else ''
  location=title.replace(',',', ')
  properties.append({'title':title,'price':price,'url':u,'location':location+', Kent, UK'})
 except Exception as e:print('Skipped',u,e)
if not properties:raise SystemExit('No confirmed To Let properties; preserving previous snapshot.')
output={'updated':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),'notice':'Public listings; verify status with Land Estates','properties':properties}
Path('rentals.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('Wrote',len(properties),'rental listings')
