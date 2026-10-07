"""Build the publication from CMS-managed content. No CMS runtime or database required."""
from pathlib import Path
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit, unquote
import calendar, csv, hashlib, html, json, math, os, re, shutil, sys
from bs4 import BeautifulSoup, NavigableString
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'_site'
E=html.escape
style_version=hashlib.sha256((ROOT/'assets'/'style.css').read_bytes()).hexdigest()[:12]
enhancements_version=hashlib.sha256((ROOT/'assets'/'enhancements.css').read_bytes()).hexdigest()[:12]
app_version=hashlib.sha256((ROOT/'assets'/'app.js').read_bytes()).hexdigest()[:12]
IVORY_THEME_CSS='''
:root{--bg:#fbfaf7;--paper:#fffefa;--line:#e7e2d9}
.topbar{background:var(--bg)!important;color:var(--text)!important;border-bottom:1px solid var(--line)!important}
.brand small,.top-label{color:#69747a}.top-link,.top-discord{color:#26353e}.top-subscribe{background:#10283a;color:#fff;padding:10px 18px}.top-subscribe:hover{background:#1b3a50;color:#fff}
.weekly-lead-layout,.ipo-calendar{background-image:none!important}
.company-directory .directory-head{max-width:none!important;border:0!important;padding:0!important;text-align:center!important}
.company-directory .directory-head h1{margin:0!important;font-size:clamp(1.65rem,2.7vw,2.45rem)!important;line-height:1!important;text-align:center!important}
.company-directory .directory-tools{display:block!important;max-width:720px!important;margin:24px auto 22px!important}
.company-directory .directory-tools .search{display:block!important;width:auto!important;max-width:none!important}
.company-directory #company-result-count,.ledger-label{border:0!important}
.intelligence-logo{flex-direction:column!important;align-items:flex-end!important}.intelligence-logo-identity{display:flex;align-items:center;gap:13px}.company-report-link{margin-top:11px;border:1px solid #bca978;color:#78521f;padding:8px 10px;font-size:.72rem;font-weight:700;letter-spacing:.02em;text-decoration:none}.company-report-link:hover{background:#f1ece1}
@media(min-width:1000px){.ipo-calendar-layout{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:20px;align-items:stretch}.ipo-calendar-layout .ipo-month{margin:0}.ipo-calendar-layout .ipo-tbd-section{border-top:0;padding-top:0;display:flex;flex-direction:column}.ipo-calendar-layout .ipo-tbd-section>header{display:block;margin:0;padding:5px 0 16px;border-bottom:1px solid #dcd6ca}.ipo-calendar-layout .ipo-tbd-section>header h2{margin:0}.ipo-calendar-layout .ipo-tbd-section>header p{margin:7px 0 0}.ipo-calendar-layout .ipo-tbd-grid{grid-template-columns:1fr;grid-template-rows:repeat(4,minmax(0,1fr));gap:10px;flex:1;padding-top:10px}.ipo-calendar-layout .ipo-tbd{min-height:0;padding:14px}.ipo-calendar-layout .ipo-tbd h2{margin:10px 0 5px;font-size:1.25rem}.ipo-calendar-layout .ipo-tbd p{font-size:.73rem;line-height:1.45}.ipo-calendar-layout .ipo-tbd a{padding-top:8px;font-size:.72rem}}
.ipo-head{display:block!important;padding:0 0 22px!important;border:0!important}.ipo-head h1{margin:0!important;font-size:clamp(1rem,1.75vw,1.75rem)!important;line-height:1!important}
@media(min-width:701px){
 .sidebar{position:fixed!important;inset:0 auto auto 50%!important;transform:translateX(-50%);z-index:21;width:auto!important;height:var(--topbar-height)!important;padding:0!important;background:transparent!important;color:var(--text)!important;display:flex!important;align-items:center}
 .sidebar .nav-label,.sidebar-note,.sidebar-footer{display:none!important}
 .sidebar nav{display:flex!important;align-items:stretch;height:100%;gap:0}
 .sidebar nav a{display:flex!important;align-items:center;height:100%;padding:0 18px!important;border:0!important;border-bottom:2px solid transparent!important;color:#26353e!important;font-size:14px}
 .sidebar nav a svg{display:none!important}.sidebar nav a:hover{background:transparent!important;color:#78521f!important}
 .sidebar nav a.active{background:transparent!important;color:#17222d!important;border-bottom-color:#a87931!important;box-shadow:none!important}
 main{margin-left:auto!important;margin-right:auto!important;max-width:1560px;padding:48px 70px 0!important}
}
@media(max-width:700px){
 .topbar{background:var(--bg)!important;color:var(--text)!important;border-bottom-color:var(--line)!important}
 .topbar .top-link{color:#26353e}.topbar .top-subscribe{background:transparent;color:#78521f;padding:0}
 .menu-toggle{color:#26353e!important;border-color:#c9c2b6!important;background:#fffefa!important}
 html.menu-ready body.menu-open .sidebar{background:var(--bg)!important;color:var(--text)!important;border-bottom:1px solid var(--line)!important}
 html.menu-ready body.menu-open .sidebar nav a{color:#26353e!important}html.menu-ready body.menu-open .sidebar nav a.active{color:#17222d!important;border-bottom-color:#a87931!important}
 .intelligence-logo{align-items:flex-start!important}.company-report-link{margin-top:10px}
}
/* Critical homepage layout lives inline so cached stylesheets cannot break the front page. */
.landing-home{max-width:1380px;margin:0 auto 64px;color:#10283a}.landing-home a{color:inherit;text-decoration:none}.landing-home-hero{display:grid;grid-template-columns:minmax(0,.92fr) minmax(390px,1.08fr);gap:48px;align-items:center;padding:38px 0 44px;border-bottom:1px solid #dcd6ca}.landing-home-copy{max-width:615px;padding:24px 0}.landing-home-copy h1{margin:0;color:#0c2436;font-family:'Newsreader',Georgia,serif;font-size:clamp(3.3rem,6.1vw,6.1rem);font-weight:500;letter-spacing:-.065em;line-height:.88}.landing-home-copy>p{max-width:520px;margin:30px 0 0;color:#52616b;font-family:'Newsreader',Georgia,serif;font-size:clamp(1.2rem,1.8vw,1.58rem);line-height:1.3}.landing-home-actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:28px}.landing-home-primary,.landing-home-secondary{display:inline-flex;align-items:center;gap:16px;min-height:46px;padding:0 20px;border:1px solid #10283a;font-size:.86rem;font-weight:700}.landing-home-primary{background:#10283a!important;color:#fff!important}.landing-home-secondary{background:transparent}.landing-home-art{position:relative;isolation:isolate;min-height:410px}.landing-home-art:before{position:absolute;z-index:-2;inset:8% 10% 11% 8%;background:#e2cf9e;content:''}.landing-home-art:after{position:absolute;z-index:-1;right:0;bottom:0;width:48%;height:43%;background:#d6e0df;content:''}.landing-art-piece{position:absolute;display:block;width:62%;height:63%;border:0;object-fit:cover;box-shadow:0 14px 28px rgba(13,35,51,.14)}.landing-art-piece:nth-child(1){top:0;right:11%;height:83%;width:61%}.landing-art-piece:nth-child(2){top:20%;left:0;width:44%;height:49%}.landing-art-piece:nth-child(3){right:0;bottom:0;width:42%;height:41%}.landing-home-trust{margin:0;padding:18px 0;border-bottom:1px solid #dcd6ca;color:#334a58;font-family:'Newsreader',Georgia,serif;font-size:1.12rem;text-align:right}.landing-section-label{margin:0 0 14px;color:#8d6c32;font-size:.68rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}.landing-research-feature{display:grid;grid-template-columns:minmax(0,1.38fr) minmax(340px,.84fr);gap:36px;padding:50px 0;border-bottom:1px solid #dcd6ca}.landing-feature-card{display:grid;gap:11px}.landing-feature-image{display:block;aspect-ratio:1.63;overflow:hidden;background:#e6e0d5}.landing-feature-image img,.landing-compact-image img,.landing-start-card>a img{display:block;width:100%;height:100%;object-fit:cover}.landing-feature-card>p,.landing-compact-card p,.landing-start-card p{margin:2px 0 0;color:#8d6c32;font-size:.65rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}.landing-feature-card h2{margin:0;font-family:'Newsreader',Georgia,serif;font-size:clamp(2rem,3.4vw,3.4rem);font-weight:500;letter-spacing:-.05em;line-height:.95}.landing-feature-meta{display:flex;justify-content:space-between;gap:18px;color:#5b6870;font-family:'Newsreader',Georgia,serif;font-size:1.05rem;line-height:1.32}.landing-feature-meta span:last-child{flex:0 0 auto;color:#8d6c32;font-family:'Source Sans 3',sans-serif;font-size:.68rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase}.landing-read-link{display:inline-block;width:max-content;margin-top:3px;color:#173a4d!important;font-size:.84rem;font-weight:700}.landing-latest{display:grid;align-content:start;gap:22px}.landing-latest>.landing-section-label{margin-bottom:2px}.landing-compact-card{display:grid;grid-template-columns:145px minmax(0,1fr);gap:17px;padding:0 0 22px;border-bottom:1px solid #dcd6ca}.landing-compact-card:last-child{border-bottom:0;padding-bottom:0}.landing-compact-image{display:block;align-self:start;aspect-ratio:1;overflow:hidden;background:#e6e0d5}.landing-compact-card h3,.landing-start-card h3{margin:6px 0;font-family:'Newsreader',Georgia,serif;font-size:1.5rem;font-weight:500;letter-spacing:-.035em;line-height:1}.landing-compact-card span,.landing-start-card>span{display:block;color:#5b6870;font-family:'Newsreader',Georgia,serif;font-size:.96rem;line-height:1.25}.landing-company-row{padding:46px 0;border-bottom:1px solid #dcd6ca}.landing-company-row header{display:flex;justify-content:space-between;gap:20px;align-items:baseline}.landing-company-row header a{color:#725724;font-size:.76rem;font-weight:700}.landing-company-row>div{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));margin-top:16px;border-left:1px solid #dcd6ca}.landing-company-row>div>a{position:relative;display:grid;min-height:128px;padding:19px 13px 16px;border:1px solid #dcd6ca;border-left:0;align-content:center;justify-items:center;text-align:center}.landing-company-row img{width:72px;height:34px;object-fit:contain}.landing-company-row span{margin-top:11px;font-family:'Newsreader',Georgia,serif;font-size:1.08rem;font-weight:600}.landing-company-row small{margin-top:3px;color:#7d6950;font-size:.56rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase}.landing-company-row b{position:absolute;right:13px;bottom:10px;color:#a3782f;font-weight:500}.landing-start{padding:46px 0}.landing-start>div{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.landing-start-card>a{display:block;aspect-ratio:1.72;overflow:hidden;background:#e6e0d5}.landing-start-card h3{font-size:1.72rem}.landing-newsletter{display:flex;align-items:center;justify-content:space-between;gap:34px;margin:0 -24px;padding:48px;background:#0d2638;color:#fff}.landing-newsletter p{margin:0 0 11px;color:#d7bb7d;font-size:.65rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}.landing-newsletter h2{margin:0;font-family:'Newsreader',Georgia,serif;font-size:clamp(2.2rem,4vw,4.15rem);font-weight:500;letter-spacing:-.055em;line-height:.9}.landing-newsletter span{display:block;margin-top:15px;color:#c6d0d5;font-family:'Newsreader',Georgia,serif;font-size:1.04rem}.landing-newsletter>a{display:inline-flex;align-items:center;gap:18px;flex:0 0 auto;padding:15px 20px;background:#d8b66d;color:#142c3c!important;font-size:.84rem;font-weight:800}
@media(max-width:980px){.landing-home-hero{grid-template-columns:1fr;gap:26px}.landing-home-copy{max-width:670px}.landing-home-art{min-height:360px;max-width:720px}.landing-research-feature{grid-template-columns:1fr}.landing-latest{grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.landing-latest>.landing-section-label{grid-column:1/-1}.landing-compact-card{grid-template-columns:112px minmax(0,1fr);border-bottom:0;padding:0}.landing-company-row>div{grid-template-columns:repeat(3,minmax(0,1fr))}.landing-company-row>div>a:nth-child(n+4){border-top:0}.landing-start>div{gap:16px}}
@media(max-width:700px){.landing-home{margin-bottom:34px}.landing-home-hero{padding:22px 0 30px}.landing-home-copy{padding:0}.landing-home-copy h1{font-size:clamp(3rem,14vw,4.45rem);line-height:.89}.landing-home-copy>p{margin-top:22px;font-size:1.22rem}.landing-home-actions{margin-top:24px}.landing-home-primary,.landing-home-secondary{min-height:43px;padding:0 15px;font-size:.78rem}.landing-home-art{min-height:290px}.landing-home-trust{padding:15px 0;font-size:1rem;text-align:left}.landing-research-feature{gap:30px;padding:34px 0}.landing-feature-card h2{font-size:2.3rem}.landing-feature-meta{display:grid;font-size:1rem}.landing-latest{grid-template-columns:1fr;gap:19px}.landing-compact-card{grid-template-columns:104px minmax(0,1fr);border-bottom:1px solid #dcd6ca;padding-bottom:18px}.landing-compact-card:last-child{padding-bottom:0}.landing-company-row{padding:34px 0}.landing-company-row>div>a{min-height:112px;padding:15px 9px}.landing-company-row img{width:64px;height:29px}.landing-company-row span{font-size:.95rem}.landing-start{padding:34px 0}.landing-start>div{grid-template-columns:1fr;gap:28px}.landing-newsletter{display:grid;margin:0 -20px;padding:37px 24px;gap:26px}.landing-newsletter h2{font-size:2.65rem}.landing-newsletter>a{justify-content:space-between;width:100%}}
.landing-home-hero{grid-template-columns:minmax(0,1.05fr) minmax(390px,.95fr);gap:42px;padding:28px 0 38px}.landing-home-copy{max-width:690px;padding:20px 0}.landing-home-copy>p{max-width:620px;margin:0;color:#52616b;font-size:clamp(1.45rem,2.25vw,2rem);line-height:1.27}.landing-home-actions{margin-top:30px}.landing-home-art{min-height:365px}.landing-home-trust{text-align:center}
.landing-art-piece:nth-child(2){top:52%;left:5.4%;width:46.2%;height:38.5%;object-position:center}
.landing-feature-image{aspect-ratio:1730 / 909}
.landing-popular{padding:38px 0;border-bottom:1px solid #dcd6ca}.landing-popular>div{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.landing-popular-card>a:first-child{display:block;aspect-ratio:1.72;overflow:hidden;background:#e6e0d5}.landing-popular-card>a:first-child img{display:block;width:100%;height:100%;object-fit:cover}.landing-popular-card p{margin:10px 0 0;color:#8d6c32;font-size:.61rem;font-weight:800;letter-spacing:.11em;text-transform:uppercase}.landing-popular-card h3{margin:4px 0 0;font-family:'Newsreader',Georgia,serif;font-size:1.32rem;font-weight:500;letter-spacing:-.035em;line-height:1}.landing-popular-card .landing-read-link{margin-top:9px;font-size:.73rem}
.landing-popular-latest{display:grid;align-content:start;gap:15px}.landing-popular-latest>.landing-section-label{margin:0}.landing-popular-latest>div{display:grid;grid-template-columns:1fr;gap:15px}.landing-popular-latest .landing-popular-card{display:grid;grid-template-columns:112px minmax(0,1fr);grid-template-areas:'image meta' 'image title' 'image summary' 'image link';column-gap:15px;align-content:start;padding:0 0 15px;border-bottom:1px solid #dcd6ca}.landing-popular-latest .landing-popular-card:last-child{padding-bottom:0;border-bottom:0}.landing-popular-latest .landing-popular-card>a:first-child{grid-area:image;aspect-ratio:1;align-self:start}.landing-popular-latest .landing-popular-card p{grid-area:meta;margin:1px 0 0;font-size:.56rem}.landing-popular-latest .landing-popular-card h3{grid-area:title;margin:5px 0 0;font-size:1.25rem}.landing-popular-summary{grid-area:summary;display:-webkit-box;overflow:hidden;margin-top:5px;color:#5b6870;font-family:'Newsreader',Georgia,serif;font-size:.84rem;line-height:1.18;-webkit-box-orient:vertical;-webkit-line-clamp:2}.landing-popular-latest .landing-popular-card .landing-read-link{grid-area:link;margin-top:8px;font-size:.7rem}
.landing-company-row .landing-scroll-rail,.landing-reader-rail{display:flex;gap:0;overflow-x:auto;overscroll-behavior-x:contain;scroll-snap-type:x proximity;scrollbar-width:thin}.landing-company-row .landing-scroll-rail>a,.landing-reader-rail>div{position:relative;display:grid;flex:0 0 calc(16.666% + 1px);min-width:170px;min-height:128px;padding:19px 13px 16px;border:1px solid #dcd6ca;border-left:0;align-content:center;justify-items:center;scroll-snap-align:start;text-align:center}.landing-reader-row{padding:28px 0 46px;border-bottom:1px solid #dcd6ca}.landing-reader-row .landing-section-label{margin-bottom:13px}.landing-reader-rail{border-left:1px solid #dcd6ca}.landing-reader-rail img{width:72px;height:34px;object-fit:contain}.landing-reader-rail span{margin-top:11px;font-family:'Newsreader',Georgia,serif;font-size:1.08rem;font-weight:600}.landing-reader-rail small{margin-top:3px;color:#7d6950;font-size:.56rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase}.landing-reader-rail b{position:absolute;right:13px;bottom:10px;color:#a3782f;font-weight:500}.landing-reader-rail>div:hover{background:#fffefa}
@media(max-width:700px){.landing-home-hero{grid-template-columns:1fr;padding:22px 0 30px}.landing-home-copy{padding:0}.landing-home-copy>p{margin:0;font-size:clamp(1.35rem,6vw,1.65rem);line-height:1.3}.landing-home-art{min-height:290px}.landing-popular-latest .landing-popular-card{grid-template-columns:96px minmax(0,1fr);column-gap:13px}.landing-popular-latest .landing-popular-card h3{font-size:1.12rem}.landing-company-row .landing-scroll-rail>a,.landing-reader-rail>div{flex-basis:46%;min-width:148px}.landing-reader-row{padding:26px 0 34px}}
'''

def soup(text):return BeautifulSoup(text,'html.parser')
def read(path):return json.loads((ROOT/path).read_text())
def put(parent,markup):parent.append(soup(markup))
def set_text(s,selector,value):
 el=s.select_one(selector)
 if el:el.clear();el.append(str(value))
def clean(markup):
 s=soup(markup)
 for el in list(s.select('script,style,form,button,input,object,embed')):el.decompose()
 for el in s.find_all(True):
  for attr in list(el.attrs):
   if attr.startswith('on') or attr in ('srcdoc','contenteditable'):del el[attr]
  for attr in ('href','src'):
   value=el.get(attr,'').strip()
   if value and (urlsplit(value).scheme.lower() not in ('','https','http','mailto') or value.startswith('//')):raise ValueError('Unsupported content URL: '+value[:80])
 return s

MENTION_RE=re.compile(r'(?<![\w@])@([A-Za-z0-9][A-Za-z0-9_-]{1,})')
def link_substack_mentions(fragment):
 for mention in list(fragment.select('.mention-wrap[data-component-name="MentionToDOM"]')):
  try: data=json.loads(mention.get('data-attrs','{}'))
  except json.JSONDecodeError: data={}
  name=str(data.get('name','')).strip();user_id=data.get('id')
  if not name or not user_id:continue
  link=fragment.new_tag('a',href=f'https://substack.com/profile/{user_id}')
  link['class']='substack-mention';link['rel']='noopener';link['aria-label']=f'View {name} on Substack';link.string=name
  mention.replace_with(link)
 for text in list(fragment.find_all(string=True)):
  parent=text.parent
  if not parent or parent.name in ('a','code','pre','script','style') or not MENTION_RE.search(str(text)):continue
  value=str(text);last=0
  for match in MENTION_RE.finditer(value):
   if match.start()>last:text.insert_before(NavigableString(value[last:match.start()]))
   handle=match.group(1);link=fragment.new_tag('a',href=f'https://substack.com/@{handle}')
   link['class']='substack-mention';link['rel']='noopener';link.string='@'+handle;text.insert_before(link);last=match.end()
  if last<len(value):text.insert_before(NavigableString(value[last:]))
  text.extract()
 return fragment

def records(folder):
 result={}
 for path in sorted((ROOT/'content'/folder).glob('*.json')):
  record=json.loads(path.read_text());slug=record.get('slug',path.stem)
  if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug):raise ValueError(f'{path.name}: web address must use lowercase letters, numbers, and hyphens.')
  if slug in result:raise ValueError('Duplicate web address: '+slug)
  record['slug']=slug;record['_file_slug']=path.stem
  if record.get('status')=='Published':result[slug]=record
 return result

# TODO: Reports on Oct 4, 2026 say SpaceXAI may be renamed 'SpaceXSI'. Unconfirmed, no formal announcement. Do not publish until confirmed.
# TODO: No official SpaceXAI logo asset is available in the repository; keep the current x.ai favicon until one is added.
# TODO: Re-check x.ai before changing SpaceXAI's website field.

COMPANY_STATUSES={'private','public','acquired','acquisition_pending','subsidiary'}
SECTORS={'AI & Machine Learning','Data, Cloud & Developer Tools','Financial Services & Digital Assets','Enterprise Software & Business Services','Consumer, Commerce & Media','Defense, Aerospace & Space','Hardware, Robotics & Semiconductors','Energy, Climate & Industrial','Healthcare & Life Sciences','Mobility, Transport & Logistics','Telecommunications & Infrastructure','Other / Diversified'}
EVENT_TYPES={'priced_round','secondary','tender','ipo','acquisition','talks'}
company_files={path.stem:json.loads(path.read_text()) for path in (ROOT/'content/companies').glob('*.json')}
for file_slug,company in company_files.items():
 if company.get('company_status') not in COMPANY_STATUSES:raise ValueError(f'Company {file_slug}: invalid company_status {company.get("company_status")!r}.')
 if company.get('sector') not in SECTORS:raise ValueError(f'Company {file_slug}: invalid sector {company.get("sector")!r}.')
 if company.get('human_verified_at'):
  try:datetime.strptime(str(company['human_verified_at']), '%Y-%m-%d')
  except ValueError:raise ValueError(f'Company {file_slug}: human_verified_at must use YYYY-MM-DD.')
settings=read('content/settings/site.json');weekly=read('content/settings/weekly.json');weekly_archives=[('2026-09-21',read('content/settings/weekly-2026-09-21.json'))];ipo_calendar=read('content/settings/ipo-calendar.json');articles=records('articles');companies=records('companies')
file_slugs={company['_file_slug']:slug for slug,company in companies.items()}
valuation_rows=[]
with (ROOT/'content/data/valuations.csv').open(newline='',encoding='utf-8') as f:
 reader=csv.DictReader(f)
 required_columns={'company_slug','date','event_type','valuation_usd_b','source_url','source_checked'}
 if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):raise ValueError('valuations.csv is missing required columns: '+', '.join(sorted(required_columns-set(reader.fieldnames or []))))
 for line_number,row in enumerate(reader,2):
  company_ref=row.get('company_slug','').strip() or '<missing company_slug>'
  row_label=f'valuations.csv line {line_number} ({company_ref})'
  if company_ref not in company_files:raise ValueError(f'{row_label}: company_slug does not match a company file.')
  if not row.get('date','').strip():raise ValueError(f'{row_label}: date is required.')
  try:
   if len(row['date'])==4:datetime.strptime(row['date'], '%Y')
   elif len(row['date'])==7:datetime.strptime(row['date'], '%Y-%m')
   else:datetime.strptime(row['date'], '%Y-%m-%d')
  except ValueError:raise ValueError(f'{row_label}: date must use YYYY, YYYY-MM or YYYY-MM-DD.')
  if row.get('event_type') not in EVENT_TYPES:raise ValueError(f'{row_label}: invalid event_type {row.get("event_type")!r}.')
  if not row.get('source_url','').strip():raise ValueError(f'{row_label}: source_url is required.')
  if row.get('source_checked') not in {'yes','no'}:raise ValueError(f'{row_label}: source_checked must be yes or no.')
  slug=file_slugs.get(row['company_slug'])
  if not slug:continue
  try:valuation=float(row['valuation_usd_b']) if row.get('valuation_usd_b') else None
  except ValueError:raise ValueError(f'{row_label}: valuation_usd_b must be a number.')
  if valuation is not None and valuation<=0:raise ValueError(f'{row_label}: valuation_usd_b must be a positive number.')
  try:raised=float(row['amount_raised_usd_b']) if row.get('amount_raised_usd_b') else None
  except ValueError:raise ValueError(f'Invalid amount raised for {row["company_slug"]}: {row["amount_raised_usd_b"]}')
  row.update({'slug':slug,'valuation':valuation,'raised':raised})
  valuation_rows.append(row)
valuations_by_slug={slug:[] for slug in companies}
for row in valuation_rows:valuations_by_slug[row['slug']].append(row)
for rows in valuations_by_slug.values():rows.sort(key=lambda row:(bool(row['date']),row['date']))

SPV_COLUMNS={'company_slug','issuer_cik','vehicle_name','family','platform','manager','latest_accession','latest_form','latest_filed','first_filed','filings','first_sale','offering_usd','sold_usd','investors','min_investment_usd','commissions_usd','finders_fees_usd','exemption','notes'}
SPV_REQUIRED={'company_slug','issuer_cik','vehicle_name','latest_accession','latest_form','latest_filed','first_filed','filings'}
SPV_INTEGER_COLUMNS={'filings','offering_usd','sold_usd','investors','min_investment_usd','commissions_usd','finders_fees_usd'}
spv_rows=[];spv_keys=set()
with (ROOT/'content/data/spvs.csv').open(newline='',encoding='utf-8') as f:
 reader=csv.DictReader(f)
 if not reader.fieldnames or not SPV_COLUMNS.issubset(reader.fieldnames):raise ValueError('spvs.csv is missing required columns: '+', '.join(sorted(SPV_COLUMNS-set(reader.fieldnames or []))))
 for line_number,row in enumerate(reader,2):
  company_ref=row.get('company_slug','').strip() or '<missing company_slug>'
  row_label=f'spvs.csv line {line_number} ({company_ref})'
  if any(not row.get(field,'').strip() for field in SPV_REQUIRED):raise ValueError(f'{row_label}: required field is empty.')
  if company_ref not in company_files:raise ValueError(f'{row_label}: company_slug does not match a company file.')
  if not re.fullmatch(r'\d+',row['issuer_cik']):raise ValueError(f'{row_label}: issuer_cik must contain digits only.')
  if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',row['latest_accession']):raise ValueError(f'{row_label}: latest_accession must use ##########-##-######.')
  if row['latest_form'] not in {'D','D/A'}:raise ValueError(f'{row_label}: latest_form must be D or D/A.')
  parsed_dates={}
  for field in ('latest_filed','first_filed','first_sale'):
   if row.get(field,'').strip():
    try:parsed_dates[field]=datetime.strptime(row[field],'%Y-%m-%d').date()
    except ValueError:raise ValueError(f'{row_label}: {field} must use YYYY-MM-DD.')
  if parsed_dates['first_filed']>parsed_dates['latest_filed']:raise ValueError(f'{row_label}: first_filed must not be after latest_filed.')
  for field in SPV_INTEGER_COLUMNS:
   value=row.get(field,'').strip()
   if value:
    if not re.fullmatch(r'\d+',value):raise ValueError(f'{row_label}: {field} must be a non-negative integer.')
    row[field]=int(value)
   else:row[field]=None
  if row['filings'] is None or row['filings']<1:raise ValueError(f'{row_label}: filings must be an integer of at least 1.')
  if row.get('exemption','') not in {'','506(b)','506(c)'}:raise ValueError(f'{row_label}: exemption must be 506(b), 506(c), or blank.')
  key=(company_ref,row['issuer_cik'],row['vehicle_name'])
  if key in spv_keys:raise ValueError(f'{row_label}: duplicate company_slug, issuer_cik, and vehicle_name.')
  spv_keys.add(key)
  slug=file_slugs.get(company_ref)
  if not slug:continue
  row.update({'slug':slug,'first_filed_date':parsed_dates['first_filed'],'latest_filed_date':parsed_dates['latest_filed'],'filing_url':f"https://www.sec.gov/Archives/edgar/data/{int(row['issuer_cik'])}/{row['latest_accession'].replace('-', '')}/xslFormDX01/primary_doc.xml",'issuer_url':f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={row['issuer_cik']}&type=D&dateb=&owner=include&count=40",'backer':row.get('platform') or row.get('manager') or 'Standalone'})
  spv_rows.append(row)
spvs_by_slug={slug:[] for slug in companies}
for row in spv_rows:spvs_by_slug[row['slug']].append(row)
for rows in spvs_by_slug.values():rows.sort(key=lambda row:row['first_filed_date'],reverse=True)
spv_as_of=max((row['latest_filed_date'] for row in spv_rows),default=None)

def money_b(value):
 if value is None:return ''
 return f'${value/1000:g}T' if value>=1000 else (f'${value*1000:g}M' if value<1 else f'${value:g}B')

def spv_usd(amount):
 if amount is None:return '—'
 if amount>=1_000_000_000:return '$'+f'{amount/1_000_000_000:.2f}'.rstrip('0').rstrip('.')+'B'
 if amount>=1_000_000:return '$'+f'{amount/1_000_000:.1f}'+'M'
 if amount>=1_000:return '$'+f'{amount/1_000:.1f}'.rstrip('0').rstrip('.')+'K'
 return '$'+str(amount)

def valuation_date_label(value):
 value=str(value)
 if re.fullmatch(r'\d{4}',value):return value
 try:return datetime.strptime(value[:7],'%Y-%m').strftime('%b %Y')
 except ValueError:return value

def latest_valuation(slug):
 """Return the latest confirmed valuation for headline and directory displays.

 Reported fundraising talks and IPO targets remain in the history/chart, but are
 not completed transactions and must never become a company's headline value.
 """
 rows=[row for row in valuations_by_slug.get(slug,[]) if row['valuation'] is not None and row['event_type']!='talks']
 return rows[-1] if rows else None
for company in companies.values():
 profile_text=' '.join((str(company.get('summary','')),str(company.get('intelligence',{}).get('description','')))).casefold()
 if 'is a private company tracked by the private ledger' in profile_text or 'placeholder' in profile_text:
  raise ValueError(f'Published company profile {company["name"]} contains placeholder research text.')
 if 'logo.clearbit.com' in str(company.get('intelligence',{}).get('logo','')).casefold():
  raise ValueError(f'Published company profile {company["name"]} uses the retired Clearbit logo service.')
base=os.environ.get('URL') or settings['site_url'];base=base.rstrip('/')
if urlsplit(base).scheme not in ('http','https'):raise ValueError('Site URL must start with https://')
for a in articles.values():
 a['date']=a['date'][:10];datetime.strptime(a['date'],'%Y-%m-%d')
 if a.get('excerpt'):
  preview_end=str(a.get('preview_end','')).strip()
  body_text=soup(a['body']).get_text(' ',strip=True)
  if not preview_end or not body_text.endswith(preview_end):
   raise ValueError(f'Members-only article {a["title"]} contains paid content; trim it to the approved free preview boundary.')
 a['minutes']=int(a.get('minutes') or max(1,round(len(soup(a['body']).get_text(' ',strip=True).split())/220)));a['url']='/articles/'+a['slug']+'/'
ordered=sorted(articles.values(),key=lambda a:(a['date'],a['title']),reverse=True)

def date_text(value):return datetime.strptime(value[:10],'%Y-%m-%d').strftime('%b %d, %Y').replace(' 0',' ')
def human_verification(c):
 value=str(c.get('human_verified_at','')).strip()
 display=f'<time datetime="{E(value)}">{E(date_text(value))}</time>' if value else '<span aria-label="No human verification date">____</span>'
 return f'<p class="profile-verification">Last verified by human: {display}</p>'
def facts(c):
 rows=''.join(f'<div><dt>{E(f["label"])}</dt><dd>{E(f["value"])}</dd><p>{E(f.get("note",""))}</p>'+ (f'<a href="{E(f["source"])}">Source <span class="sr-only">for {E(f["label"])}</span> ↗</a>' if f.get('source') else '')+'</div>' for f in c.get('facts',[]))
 return f'<div class="facts-inner"><p class="snapshot-note">Figures as of {date_text(c["as_of"])}. Estimates and projections are labelled separately.</p><dl class="facts-grid">{rows}</dl></div>'

def intelligence_profile(c):
 d=c['intelligence']
 verified=human_verification(c)
 metrics=''.join(f'<div><strong>{E(item["value"])}</strong><span>{E(item["label"])}</span><small>{E(item.get("note",""))}</small></div>' for item in d['metrics'])
 history=''.join(f'<li><strong>{E(money_b(item["valuation"]) if item["valuation"] is not None else ("Raised "+money_b(item["raised"])+" · valuation undisclosed" if item["raised"] is not None else "Valuation undisclosed"))}</strong><span>→</span><small>{E(valuation_date_label(item["date"]) if item["date"] else "Date undisclosed")}</small><em>{E(("Reported, unconfirmed: " if item["event_type"]=="talks" else "")+(item["round_label"] or item["event_type"].replace("_"," ").title()))}</em><a href="{E(item["source_url"])}" rel="noopener">Source ↗</a></li>' for item in valuations_by_slug.get(c['slug'],[])) or '<li><strong>No disclosed valuation events</strong></li>'
 spv_link=''
 changed=''.join(f'<li><time>{E(item["date"])}</time><p>{E(item["text"])}</p></li>' for item in d['changed'])
 takeaways=''.join(f'<li><span>{i:02d}</span><p>{E(item)}</p></li>' for i,item in enumerate(d['takeaways'],1))
 quick=''.join(f'<dt>{E(item.get("label", ""))}</dt><dd>{E(item.get("value", ""))}</dd>' if isinstance(item,dict) else f'<dt>{E(item[0])}</dt><dd>{E(item[1])}</dd>' for item in d['quick_facts'])
 sources=''.join(f'<li><a href="{E(item["url"])}">{E(item["label"])} <span>↗</span></a></li>' for item in d['sources'])
 logo=f'<img src="{E(d["logo"])}" alt="{E(c["name"])} logo" loading="lazy">' if d.get('logo') else ''
 logo_class=' intelligence-logo-dark' if c['name'].casefold() in ('long lake','neros','revel','ricursive') else ''
 report_link=f'<a class="company-report-link" href="{E(articles[c["report"]]["url"])}">Go to full article <span aria-hidden="true">→</span></a>' if c.get('report') in articles else ''
 return f'''<section class="intelligence-profile">
 <header class="intelligence-header"><div><h1>{E(c["name"])}</h1><p class="intelligence-meta">{E(c["sector"])} <span>·</span> {E(d["location"])} <span>·</span> {E(c.get("company_status", d["status"]).replace("_", " ").title())}</p><p class="intelligence-description">{E(d["description"])}</p></div><div class="intelligence-logo{logo_class}"><div class="intelligence-logo-identity">{logo}<strong>{E(c["name"])}</strong></div>{report_link}</div></header>
 <section class="intelligence-metrics">{metrics}</section>
 <div class="intelligence-content"><div class="intelligence-main"><section><h2>The Company</h2>{''.join('<p>'+E(p)+'</p>' for p in d['company'])}</section><section><h2>Why It Matters</h2><p>{E(d["why_it_matters"])}</p></section><section><h2>Valuation History</h2><ol class="valuation-history">{history}</ol>{spv_link}</section><section><h2>What Changed</h2><ol class="change-log">{changed}</ol></section></div><aside class="intelligence-aside"><section><h2>Key Takeaways</h2><ol class="takeaways">{takeaways}</ol></section><section><h2>Quick Facts</h2><dl class="quick-facts">{quick}</dl></section><section><h2>Sources</h2><ul class="intelligence-sources">{sources}</ul></section></aside></div>
 </section>{verified}</section>'''

def shell(kind,title,description,route,image=''):
 s=soup((ROOT/'templates'/f'{kind}.html').read_text());s.title.string=title+' | '+settings['site_name']
 for label in s.select('.top-label'):label.decompose()
 for link in s.select('a'):
  if any(word in link.get_text(' ',strip=True).casefold() for word in ('subscribe','discord')):
   for icon in link.select('span[aria-hidden="true"]'):
    if icon.get_text(strip=True) in ('↗','→'):icon.decompose()
 for link in s.select('.top-subscribe,.top-discord'):
  for icon in link.select('[aria-hidden="true"]'):icon.decompose()
 put(s.head,f'<style>{IVORY_THEME_CSS}</style>')
 for stylesheet in s.select('link[href="/style.css"]'):
  stylesheet['href']=f'/style.css?v={style_version}'
 favicon=s.select_one('link[rel="icon"]');favicon['href']='/favicon.png?v=3';favicon['sizes']='64x64';favicon['type']='image/png'
 for asset in s.select('link[href="/enhancements.css"],script[src="/enhancements.js"]'):
  asset['href' if asset.name=='link' else 'src']=(f'/enhancements-{enhancements_version}.css' if asset.name=='link' else '/enhancements.js?v=2')
 for script in s.select('script[src="/app.js"]'):script['src']=f'/app.js?v={app_version}'
 for font_link in s.select('link[href*="fonts.googleapis.com"]'):
  font_link['href']='https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=Source+Sans+3:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&display=swap'
 s.select_one('meta[name="description"]')['content']=description
 for name,value in [('og:title',s.title.string),('og:description',description),('og:url',base+route),('og:site_name',settings['site_name'])]:s.select_one(f'meta[property="{name}"]')['content']=value
 s.select_one('link[rel="canonical"]')['href']=base+route
 if route=='/research/':
  s.title.string='Research | '+settings['site_name']
  description='Company deep dives and general articles on private markets.'
  s.select_one('meta[name="description"]')['content']=description
  s.select_one('meta[property="og:title"]')['content']=s.title.string
  s.select_one('meta[property="og:description"]')['content']=description
 for x in s.select('script[type="application/ld+json"],meta[property="og:image"],meta[property="og:image:alt"]'):x.decompose()
 if image:put(s.head,f'<meta property="og:image" content="{E(base+image if image.startswith("/") else image)}">')
 for a in s.select('a[href^="https://preipomedia.substack.com/subscribe"]'):a['href']=settings['subscribe_url']
 if settings.get('discord_url'):
  top_subscribe=s.select_one('.top-subscribe')
  if top_subscribe:top_subscribe.insert_before(soup(f'<a class="top-link top-discord" href="{E(settings["discord_url"])}" rel="noopener">Join our Discord</a>'))
 for panel in s.select('.subscribe-panel'):
  set_text(panel,'h2',settings['subscribe_title']);set_text(panel,'p:not(.eyebrow)',settings['subscribe_text'])
 brandmark=s.select_one('.brandmark')
 if brandmark:
  brandmark.clear();put(brandmark,'<img src="/compass-logo.png" alt="" aria-hidden="true">')
 brand=s.select_one('.brand>span:last-child');brand.clear();brand.append(settings['site_name'].upper());put(brand,'<small>'+E(settings['tagline'])+'</small>')
 if s.select_one('footer'):
  s.select_one('footer').clear()
  put(s.select_one('footer'),f'<div class="footer-about"><strong>About {E(settings["site_name"])}</strong><span>{E(settings["about_text"])}</span><a href="/about/">Read our editorial approach →</a></div><span class="footer-copyright">© {date.today().year} {E(settings["site_name"])}</span>')
 return s

def write(s,route):
 p=OUT/route.strip('/')/'index.html';p.parent.mkdir(parents=True,exist_ok=True)
 rendered=str(s)
 if not route.startswith('/articles/'):
  rendered=rendered.replace(' — ', ', ').replace('—','-')
 p.write_text(rendered)

def configure_nav(s,active):
 """Keep the publication's primary discovery destinations consistent in every page shell."""
 nav=s.select_one('nav[aria-label="Primary"]')
 home=nav.select_one('[data-view="library"]')
 home['data-view']='home';home['href']='/';home.clear();put(home,'<svg aria-hidden="true" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" viewBox="0 0 24 24"><path d="M4 4h6v16H4z M14 4h6v16h-6z"></path></svg> This week')
 companies_link=nav.select_one('[data-view="companies"]')
 if companies_link:companies_link.extract()
 research=soup('<a data-view="library" href="/research/?type=deep-dives"><svg aria-hidden="true" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" viewBox="0 0 24 24"><path d="M4 4h6v16H4z M14 4h6v16h-6z"></path></svg>Research</a>').a
 home.insert_before(research)
 if companies_link:research.insert_after(companies_link)
 for old_link in nav.select('a[data-view="insights"]'):old_link.decompose()
 for about_link in nav.select('a[href="/about/"]'):about_link.decompose()
 ipo=soup('<a data-view="ipo" href="/ipo-calendar/"><svg aria-hidden="true" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"></rect><path d="M16 3v4M8 3v4M3 10h18"></path></svg>IPO calendar</a>').a
 (companies_link or research).insert_after(ipo)
 home.decompose()
 for link in nav.select('a'):
  link.attrs.pop('aria-current',None)
  link['class']=['active'] if link.get('data-view')==active else []

def weekly_chart_markup(lead_item):
 """Render the lead story's documented valuation history, never another company's chart."""
 company_name=str(lead_item.get('company','')).casefold()
 company=next((record for record in companies.values() if str(record.get('name','')).casefold()==company_name),None)
 if not company:return ''
 event_rows=[row for row in valuations_by_slug.get(company['slug'],[]) if row['valuation'] is not None and row['date']]
 chart_dates=set(lead_item.get('chart_dates',[]))
 if chart_dates:event_rows=[row for row in event_rows if row['date'] in chart_dates]
 events=[{'amount':row['valuation'],'value':('>'+money_b(row['valuation']) if 'ipo target' in row['round_label'].casefold() else money_b(row['valuation'])),'date':date_text(row['date']),'round':row['round_label'],'source':row['source_url'],'reported':row['event_type']=='talks','target':'ipo target' in row['round_label'].casefold()} for row in event_rows]
 if len(events)<2:return ''
 width,height,left,right,top,bottom=760,274,58,28,26,206
 maximum=max(event['amount'] for event in events)
 step_size=1 if maximum<=10 else 10 if maximum<=50 else 50
 ceiling=max(step_size,math.ceil(maximum/step_size)*step_size)
 step=(width-left-right)/(len(events)-1)
 points=[]
 for index,event in enumerate(events):
  x=left+index*step;y=bottom-(event['amount']/ceiling)*(bottom-top)
  points.append((x,y,event))
 grid=''.join(f'<line x1="{left}" y1="{bottom-(value/ceiling)*(bottom-top):.1f}" x2="{width-right}" y2="{bottom-(value/ceiling)*(bottom-top):.1f}" class="weekly-chart-grid"/><text x="{left-12}" y="{bottom-(value/ceiling)*(bottom-top)+5:.1f}" text-anchor="end" class="weekly-chart-axis">{E(money_b(value))}</text>' for value in (0,ceiling/2,ceiling))
 segments=''.join(f'<path d="M {points[index-1][0]:.1f} {points[index-1][1]:.1f} L {x:.1f} {y:.1f}" class="weekly-chart-line{" weekly-chart-line--reported" if event["reported"] else ""}"/>' for index,(x,y,event) in enumerate(points) if index)
 dots=''.join(f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="5" class="weekly-chart-point{" weekly-chart-point--reported" if event["reported"] else ""}" data-date="{E(event["date"])}" data-value="{E(event["value"])}" data-round="{E(event["round"])}" tabindex="0" role="button" aria-label="{E(event["date"])}: {E(event["value"])}. {E(event["round"])}."><title>{E(event["date"])}: {E(event["value"])}. {E(event["round"])}.</title></circle><text x="{x:.1f}" y="{bottom+31}" text-anchor="middle" class="weekly-chart-date">{E(event["date"])}</text></g>' for x,y,event in points)
 latest=events[-1]
 source=latest.get('source') or lead_item.get('source') or company.get('facts',[{}])[0].get('source',f'/companies/{company["slug"]}/')
 latest_label='Reported IPO target' if latest['target'] else 'Latest reported value'
 chart_description=f'{company["name"]} valuation history, including a reported IPO target' if latest['target'] else f'{company["name"]} reported valuation history'
 return f'''<section class="weekly-chart weekly-chart--sidebar" aria-labelledby="weekly-chart-title"><header class="weekly-chart-head"><div><h2 id="weekly-chart-title">{E(company['name'])} valuation history.</h2><p>{E(latest['round'] or latest_label)} at {E(latest['value'])}.</p></div><div class="weekly-chart-stat"><strong>{E(latest['value'])}</strong><span>{latest_label}</span></div></header><div class="weekly-chart-plot"><svg viewBox="0 0 {width} {height}" role="img" aria-label="{E(chart_description)}">{grid}{segments}{dots}</svg><div class="weekly-chart-tooltip" hidden aria-live="polite"></div></div><footer><a href="/companies/{E(company['slug'])}/">Profile →</a><a href="/valuations/">Valuation desk →</a><a href="{E(source)}" rel="noopener">Source ↗</a></footer></section>'''

def weekly_markup(data=weekly):
 def amount(item):
  value=item.get('amount_usd')
  if value is None:return None
  if not isinstance(value,(int,float)):raise ValueError(f'Weekly amount_usd for {item.get("company", "an item")} must be a number or null.')
  return float(value)
 def profile_url(item):
  company_name=str(item.get('company','')).casefold()
  for slug,company in companies.items():
   if str(company.get('name','')).casefold()==company_name:return f'/companies/{slug}/'
  return ''
 def item_markup(item,index,lead=False):
  profile=profile_url(item)
  links=f'<a href="{E(item["source"])}" rel="noopener">Source ↗</a>'
  if profile:links+=f'<a href="{profile}">Profile →</a>'
  return f'''<article class="weekly-item{' weekly-item--lead' if lead else ''}"><div><span class="weekly-number">{index:02d}</span><span class="weekly-tag">{E(item['tag'])}</span></div><h2>{E(item['company'])}</h2><p>{E(item['text'])}</p><div class="weekly-item-links">{links}</div></article>'''
 def scoreboard_markup():
  scoreboard=data.get('scoreboard',[])
  if not isinstance(scoreboard,list) or not scoreboard:return ''
  figures=[]
  for entry in scoreboard:
   if not isinstance(entry,dict) or not all(entry.get(key) for key in ('value','label','note')):return ''
   sources=entry.get('sources',[])
   if not isinstance(sources,list) or not all(isinstance(source,dict) and source.get('label') and source.get('url') for source in sources):return ''
   source_links=''.join(f'<li><a href="{E(source["url"])}" rel="noopener">{E(source["label"])} ↗</a></li>' for source in sources)
   source_markup=f'<details><summary>Sources</summary><ul>{source_links}</ul></details>' if source_links else ''
   figures.append(f'''<article class="weekly-scoreboard-figure"><strong>{E(str(entry['value']))}</strong><span>{E(str(entry['label']))}</span><p>{E(str(entry['note']))}</p>{source_markup}</article>''')
  if len(figures)!=4:return ''
  return f'''<section class="weekly-scoreboard" aria-labelledby="weekly-scoreboard-title"><header><p class="weekly-scoreboard-kicker">WEEKLY SCOREBOARD</p><h2 id="weekly-scoreboard-title">Private-market activity, counted.</h2></header><div class="weekly-scoreboard-grid">{''.join(figures)}</div><a class="weekly-scoreboard-method" href="#weekly-scoreboard-method">How we count ↓</a><p class="weekly-scoreboard-method-copy" id="weekly-scoreboard-method">We count disclosed private financings of $100M or more, newly reported $1B-plus valuations, and confirmed IPO filings, pricings, and exits. Every count links to a source.</p></section>'''
 weekly_items=data['items']
 for item in weekly_items:
  if 'policy' in str(item.get('tag','')).casefold():print(f'Warning: policy-tagged weekly item: {item.get("company", "unknown")}',file=sys.stderr)
 lead=item_markup(weekly_items[0],1,True)
 items=''.join(item_markup(item,index) for index,item in enumerate(weekly_items[1:],2))
 previous=f'<a class="text-link" href="{E(data["previous_url"])}">Previous week →</a>' if data.get('previous_url') else ''
 return f'''<section class="weekly-brief" aria-labelledby="weekly-title"><header class="weekly-head"><div><h1 id="weekly-title">{E(data['title'])}</h1><p class="subtitle">{E(data['intro'])}</p></div><p class="weekly-date">Last week<br/><strong>{E(data['period'])}</strong><span>Next update: {E(data['next_update'])}</span></p></header>{scoreboard_markup()}<div class="weekly-lead-layout">{lead}{weekly_chart_markup(weekly_items[0])}</div><div class="weekly-grid weekly-grid--secondary">{items}</div><div class="weekly-footer"><span>Updated every Sunday.</span><a class="text-link" href="/research/">Explore company research →</a>{previous}</div></section>'''

def landing_markup():
 """The permanent editorial front page, assembled from published research."""
 def article(slug):
  return articles.get(slug)
 def image(record,classes=''):
  if not record or not record.get('cover_image'):return ''
  name=record.get('card_title') or record['title']
  return f'<img class="{classes}" src="{E(record["cover_image"])}" alt="{E(record.get("cover_alt",name))}" loading="lazy">'
 def title(record):return record.get('card_title') or record['title']
 def link(record,label='Read the research →'):
  return f'<a class="landing-read-link" href="{E(record["url"])}">{E(label)}</a>'
 def feature(record):
  return f'''<article class="landing-feature-card"><a class="landing-feature-image" href="{E(record['url'])}" aria-label="Read {E(title(record))}">{image(record)}</a><p>{E(record['sector'])}</p><h2><a href="{E(record['url'])}">{E(title(record))}</a></h2><div class="landing-feature-meta"><span>{E(record['summary'])}</span><span>{record['minutes']} min read</span></div>{link(record)}</article>'''
 def compact(record):
  return f'''<article class="landing-compact-card"><a class="landing-compact-image" href="{E(record['url'])}" aria-label="Read {E(title(record))}">{image(record)}</a><div><p>{E(record['sector'])}</p><h3><a href="{E(record['url'])}">{E(title(record))}</a></h3><span>{E(record['summary'])}</span>{link(record, 'Read the research →')}</div></article>'''
 def popular(record):
  return f'''<article class="landing-popular-card"><a href="{E(record['url'])}" aria-label="Read {E(title(record))}">{image(record)}</a><p>{E(record['sector'])}</p><h3><a href="{E(record['url'])}">{E(title(record))}</a></h3><span class="landing-popular-summary">{E(record['summary'])}</span>{link(record, 'Read →')}</article>'''
 spacex=article('the-breakdown-spacex')
 databricks=article('the-breakdown-databricks')
 anduril=article('the-breakdown-anduril')
 openai=article('the-breakdown-openai')
 saronic=article('the-breakdown-saronic')
 stripe=article('the-breakdown-stripe')
 # Published records are expected, but retain a useful front page if one is ever removed.
 primary=article('the-breakdown-anthropic') or spacex or next(iter(ordered))
 secondary=[record for record in (databricks,anduril,openai) if record and record is not primary][:2]
 if len(secondary)<2:secondary.extend(record for record in ordered if record is not primary and record not in secondary)
 popular_reads=[record for record in (spacex,article('the-breakdown-substack'),stripe,openai) if record]
 company_slugs=['spacex','openai','anthropic','stripe','anduril','databricks','bytedance','isomorphic-labs','polymarket','saronic','substack']
 company_cards=[]
 for slug in company_slugs:
  company=companies.get(slug)
  if not company:continue
  logo=company.get('intelligence',{}).get('logo','')
  logo_markup=f'<img src="{E(logo)}" alt="{E(company["name"])} logo" loading="lazy">' if logo else ''
  company_cards.append(f'<a href="/companies/{E(slug)}/">{logo_markup}<span>{E(company["name"])}</span><small>{E(company.get("sector", ""))}</small></a>')
 hero_images=''.join(image(record,'landing-art-piece') for record in (spacex,databricks,saronic) if record)
 readers=[
  ('Harvard','harvard.edu'),('Citi','citi.com'),('UofT','utoronto.ca'),('Intel','intel.com'),
  ('Princeton','princeton.edu'),('HSBC','hsbc.com'),('Cornell','cornell.edu'),
  ('Schonfeld','schonfeld.com'),('Stanford','stanford.edu'),('Freddie Mac','freddiemac.com'),('Penn','upenn.edu'),
  ('NYU Stern','stern.nyu.edu'),('Sacra','sacra.com'),('Crusoe','crusoe.ai')
 ]
 reader_cards=''.join(f'<div><img src="https://www.google.com/s2/favicons?domain={E(domain)}&amp;sz=128" alt="{E(name)} logo" loading="lazy"><span>{E(name)}</span></div>' for name,domain in readers)
 return f'''<section class="landing-home" aria-label="The Private Ledger">
 <section class="landing-home-hero"><div class="landing-home-copy"><p>Independent research on the world’s most important private companies, before they reach the public markets.</p><div class="landing-home-actions"><a class="landing-home-primary" href="/research/">Explore the research</a><a class="landing-home-secondary" href="{E(settings['subscribe_url'])}" rel="noopener">Subscribe</a></div></div><div class="landing-home-art" aria-hidden="true">{hero_images}</div></section>
 <p class="landing-home-trust">Independent. In-depth. Before the IPO.</p>
 <section class="landing-research-feature" aria-labelledby="landing-feature-title"><div><p class="landing-section-label">Featured research</p>{feature(primary)}</div><div class="landing-popular-latest"><p class="landing-section-label" id="landing-feature-title">Most Popular Research</p><div>{''.join(popular(record) for record in popular_reads)}</div></div></section>
 <section class="landing-company-row" aria-labelledby="landing-company-title"><header><p class="landing-section-label" id="landing-company-title">Research by company</p><a href="/companies/">View the company index →</a></header><div class="landing-scroll-rail" data-reader-loop data-reader-count="{len(company_cards)}">{''.join(company_cards)}{''.join(company_cards)}</div></section>
 <section class="landing-reader-row" aria-labelledby="landing-reader-title"><p class="landing-section-label" id="landing-reader-title">Read by:</p><div class="landing-reader-rail" data-reader-loop data-reader-count="{len(readers)}">{reader_cards}{reader_cards}</div></section>
 <section class="landing-newsletter"><div><p>The Private Ledger newsletter</p><h2>See the next chapter<br>before the market does.</h2><span>New research delivered directly to your inbox.</span></div><a href="{E(settings['subscribe_url'])}" rel="noopener">Subscribe</a></section>
 </section>'''

def ipo_markup():
 """A true month view; undated candidates stay out of arbitrary day cells."""
 month=ipo_calendar['calendar']['month'];year=int(ipo_calendar['calendar']['year']);month_number=int(ipo_calendar['calendar']['month_number'])
 items=[item for period in ipo_calendar['periods'] for item in period['items']]
 def profile_status(company):
  return str(company.get('company_status','private')).casefold()
 def profile_valuation(company):
  row=latest_valuation(company['slug'])
  return money_b(row['valuation']) if row else 'No disclosed valuation'
 for item in items:
  slug=str(item.get('company_slug','')).strip()
  if not slug:raise ValueError(f'IPO calendar entry {item.get("company", "unknown")} is missing company_slug.')
  company=companies.get(slug)
  if not company:raise ValueError(f'IPO calendar entry {item.get("company", "unknown")} points to missing published profile: {slug}.')
  if profile_status(company) in ('public','acquired','acquisition_pending'):
   profile_label=company.get('company_status','private')
   raise ValueError(f'IPO calendar entry {item["company"]} points to a non-private profile ({profile_label}). Remove it from the watchlist.')
  override=item.get('valuation_override')
  if override and not str(item.get('valuation_override_note','')).strip():
   raise ValueError(f'IPO calendar entry {item["company"]} has valuation_override without valuation_override_note.')
  item['display_valuation']=str(override).strip() if override else profile_valuation(company)
 events={};lead_in_events={}
 for item in items:
  if item.get('date'):
   target=events if int(item.get('month',month_number))==month_number else lead_in_events
   target.setdefault(str(item['date']),[]).append(item)
 # The IPO calendar intentionally excludes public-company earnings dates.
 earnings={}
 def event_markup(item):
  href='/companies/'+item['company_slug']+'/' if item.get('company_slug') else item['source']
  return f'<a class="ipo-event" href="{E(href)}"><strong>{E(item["company"])}</strong><span>{E(item["status"])}</span></a>'
 def earnings_markup(item):
  label=f'Open The Ledger view on {item["company"]} earnings'
  return f'<button class="ipo-event earnings-event" type="button" aria-label="{E(label)}" data-company="{E(item["company"])}" data-ticker="{E(item["ticker"])}" data-timing="{E(item["timing"])}" data-confidence="{E(item["confidence"])}" data-impact="{E(item["impact"])}" data-source="{E(item["source"])}"><strong>{E(item["ticker"])}</strong><span>{E(item["timing"])}</span></button>'
 # Calendar headings begin on Monday. Build the cells from the date's explicit
 # Monday-based weekday index instead of relying on calendar.monthcalendar's
 # process-wide first-weekday setting.
 first_weekday=calendar.weekday(year,month_number,1)
 days_in_month=calendar.monthrange(year,month_number)[1]
 calendar_days=[0]*first_weekday+list(range(1,days_in_month+1))
 calendar_days.extend([0]*((-len(calendar_days))%7))
 weeks=[]
 for week_index,start in enumerate(range(0,len(calendar_days),7)):
  week=calendar_days[start:start+7]
  cells=[]
  for day in week:
   if day:
    entries=''.join(event_markup(item) for item in events.get(str(day),[]))+''.join(earnings_markup(item) for item in earnings.get(str(day),[]))
    cells.append(f'<div class="ipo-day"><span>{day}</span>{entries}</div>')
   else:
    prior_day=calendar.monthrange(year if month_number>1 else year-1,month_number-1 or 12)[1]-week.count(0)+cells.__len__()+1
    entries=''.join(event_markup(item) for item in lead_in_events.get(str(prior_day),[])) if week_index==0 else ''
    cells.append(f'<div class="ipo-day is-outside"{"" if entries else " aria-hidden=\\\"true\\\""}>{f"<span>Sep {prior_day}</span>{entries}" if entries else ""}</div>')
  weeks.append('<div class="ipo-week">'+''.join(cells)+'</div>')
 tbd=''.join(f'''<a class="ipo-tbd" href="/companies/{E(item['company_slug'])}/" aria-label="Open {E(item['company'])} company profile"><div><span class="ipo-status {E(item['status'].lower().replace(' ','-'))}">{E(item['status'])}</span><span class="ipo-valuation">{E(item['display_valuation'])}</span></div><h2>{E(item['company'])}</h2><p>{E(item['note'])}</p><span class="ipo-tbd-open">Open company profile →</span></a>''' for item in items)
 earnings_list=''.join(f'''<article class="ipo-list-item"><header><strong>{E(item['company'])}</strong><span class="ticker">{E(item['ticker'])}</span></header><p class="timing">{E(str(item['date']))} · {E(item['timing'])}</p><p>{E(item['impact'])}</p><a class="earnings-event-mini" href="{E(item['source'])}" rel="noopener">Earnings source ↗</a></article>''' for item in ipo_calendar.get('earnings',[]))
 return f'''<section class="ipo-calendar" aria-labelledby="ipo-title"><header class="ipo-head"><h1 id="ipo-title">{E(ipo_calendar['title'])}</h1></header><div class="ipo-view-toggle" role="group" aria-label="IPO calendar view"><button class="view-toggle active" type="button" data-view="calendar" aria-pressed="true">Calendar</button><button class="view-toggle" type="button" data-view="list" aria-pressed="false">Earnings list</button></div><div class="ipo-view-content ipo-calendar-layout" data-view="calendar"><section class="ipo-month" aria-labelledby="ipo-month-title"><header><div><h2 id="ipo-month-title">{E(month)}</h2></div><p><strong>Public earnings &amp; IPO watch.</strong> Reported IPO targets are labelled as unconfirmed.</p></header><div class="ipo-weekdays"><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span></div><div class="ipo-month-grid">{''.join(weeks)}</div><p class="ipo-empty"><strong>No confirmed $5B+ IPO dates are on the public calendar for {E(month)}.</strong> Reported IPO targets are marked separately; public-company earnings markers use confirmed dates where disclosed and labelled estimates otherwise.</p></section><section class="ipo-tbd-section" aria-labelledby="ipo-tbd-title"><header><h2 id="ipo-tbd-title">Watchlist:</h2><p>Private-market giants with a reported filing, timing window, or credible path to market.</p></header><div class="ipo-tbd-grid">{tbd}</div></section></div><section class="ipo-earnings-list ipo-view-content" data-view="list" hidden><header><h2>Private-market read-throughs.</h2><p>Confirmed earnings dates and the public-company results most relevant to private-market investors.</p></header><div class="earnings-list-items">{earnings_list}</div></section></section>'''

def chart_date(value):
 """Turn the deliberately human-readable profile dates into stable chart dates."""
 value=str(value).strip()
 for fmt in ('%b %Y','%B %Y','%Y'):
  try:
   parsed=datetime.strptime(value,fmt)
   return parsed.strftime('%Y-%m-%d') if fmt!='%Y' else f'{parsed.year}-07-01'
  except ValueError:pass
 year=re.search(r'\b(\d{4})\b',value)
 if year:return f'{year.group(1)}-07-01'
 return ''

def valuation_chart_markup():
 """Render every company whose CSV history supports a meaningful comparison."""
 series=[]
 for slug,company in companies.items():
  events=[{'date':row['date']+'-07-01' if len(row['date'])==4 else row['date']+'-01' if len(row['date'])==7 else row['date'],'label':valuation_date_label(row['date']),'value':('>'+money_b(row['valuation']) if 'ipo target' in row['round_label'].casefold() else money_b(row['valuation'])),'amount':row['valuation'],'round':row['round_label'],'event_type':row['event_type'],'source':row['source_url']} for row in valuations_by_slug.get(slug,[]) if row['valuation'] is not None and row['valuation']>0 and row['date']]
  if len(events)>1:
   series.append({'name':company['name'],'slug':slug,'url':'/companies/'+slug+'/', 'events':events})
 series.sort(key=lambda item:item['name'].casefold())
 data=json.dumps(series,separators=(',',':')).replace('</','<\\/')
 return f'''<section class="valuation-page" aria-labelledby="valuation-title"><header class="valuation-head"><div><h1 id="valuation-title">Private valuation history.</h1><p>Reported point-in-time valuations at disclosed financings and liquidity events.</p></div><a href="/companies/" class="valuation-directory-link">Browse companies <span aria-hidden="true">→</span></a></header><div class="valuation-method"><strong>Not a market-price chart.</strong> The logarithmic view makes different-sized companies readable. Hollow points are reported talks, not closed transactions.</div><section class="valuation-chart-shell" aria-label="Private valuation comparison"><div class="valuation-toolbar"><div class="valuation-picker"><p class="valuation-control-label">COMPARE COMPANIES</p><label class="valuation-search"><span class="sr-only">Search a company</span><input id="valuation-company-search" type="search" placeholder="Search companies" autocomplete="off"></label><div id="valuation-search-results" class="valuation-search-results" hidden></div><div id="valuation-selected" class="valuation-selected" aria-label="Companies shown"></div></div><div><p class="valuation-control-label">VIEW</p><div class="valuation-range" aria-label="Chart view"><button type="button" data-range="1">1Y</button><button type="button" data-range="3">3Y</button><button type="button" data-range="5">5Y</button><button type="button" data-range="all" class="is-active">All</button><button type="button" class="valuation-index" aria-pressed="false">Index to zero</button></div></div></div><div class="valuation-chart" id="valuation-chart" data-valuation-series='{E(data)}'><div class="valuation-chart-canvas" role="img" aria-label="Reported private valuation history chart"></div><div class="valuation-tooltip" hidden></div></div><div class="valuation-legend" aria-label="Visible companies"></div></section><p class="valuation-footnote">Each point has a direct source link on hover or focus. Figures are reported valuations, not investment advice.</p></section>'''

def spv_tracker_markup():
 """Render a reproducible, filing-backed view of company SPV activity."""
 cutoff=spv_as_of-timedelta(days=365)
 def median(values):
  values=sorted(values);middle=len(values)//2
  return values[middle] if len(values)%2 else (values[middle-1]+values[middle])//2
 def latest_priced(slug):
  rows=[row for row in valuations_by_slug.get(slug,[]) if row['event_type']=='priced_round' and row['valuation'] is not None]
  return rows[-1] if rows else None
 def card(slug,rows):
  company=companies[slug];sold=sum(row['sold_usd'] or 0 for row in rows);investors=sum(row['investors'] or 0 for row in rows)
  new=[row for row in rows if row['first_filed_date']>=cutoff];new_sold=sum(row['sold_usd'] or 0 for row in new)
  minimums=[row['min_investment_usd'] for row in rows if row['min_investment_usd']]
  marketed=round(100*sum(row['exemption']=='506(c)' for row in rows)/len(rows))
  backers={}
  for row in rows:backers[row['backer']]=backers.get(row['backer'],0)+1
  top=', '.join(f'{E(name)} ({count})' for name,count in sorted(backers.items(),key=lambda item:(-item[1],item[0]))[:3])
  years=range(min(row['first_filed_date'].year for row in rows),spv_as_of.year+1);year_counts={year:sum(row['first_filed_date'].year==year for row in rows) for year in years};maximum=max(year_counts.values())
  bars=''.join(f'<g><rect class="spv-bar{" spv-bar-as-of" if year==spv_as_of.year else ""}" x="{index*48+7}" y="{66-(count/maximum)*48:.1f}" width="31" height="{(count/maximum)*48:.1f}"><title>{year}: {count} vehicles</title></rect><text x="{index*48+22}" y="80" text-anchor="middle">{year}</text></g>' for index,(year,count) in enumerate(year_counts.items()))
  priced=latest_priced(slug);context=f'<p class="spv-context">Last priced round: {E(money_b(priced["valuation"]))} · {E(priced["round_label"])} · {E(valuation_date_label(priced["date"]))}</p>' if priced else ''
  table_rows=''.join(f'<tr{" data-recent=\"true\"" if row["first_filed_date"]>=cutoff else ""}><td data-label="First filed">{E(row["first_filed"])}</td><td data-label="Vehicle"><a href="{E(row["issuer_url"])}" rel="noopener">{E(row["vehicle_name"])}</a><small>{E(row["platform"] or row["manager"] or "Standalone")}{(" · "+E(row["notes"])) if row["notes"] else ""}</small></td><td data-label="Reported sold">{E(spv_usd(row["sold_usd"]))}{(" of "+E(spv_usd(row["offering_usd"]))) if row["offering_usd"] is not None else ""}</td><td data-label="Investors">{("{:,}".format(row["investors"])) if row["investors"] is not None else "—"}</td><td data-label="Minimum">{E("Not stated" if not row["min_investment_usd"] else spv_usd(row["min_investment_usd"]))}</td><td data-label="Sales comp">{E(spv_usd((row["commissions_usd"] or 0)+(row["finders_fees_usd"] or 0)) if (row["commissions_usd"] or 0)+(row["finders_fees_usd"] or 0) else "—")}</td><td data-label="Exemption">{E(row["exemption"] or "—")}</td><td data-label="Filing"><a href="{E(row["filing_url"])}" rel="noopener">Form {E(row["latest_form"])} ↗</a></td></tr>' for row in rows)
  search=' '.join([company['name']]+[f'{row["vehicle_name"]} {row["platform"]} {row["manager"]}' for row in rows])
  return f'''<article class="spv-card" id="{E(slug)}" data-name="{E(company['name'])}" data-search="{E(search)}" data-sold="{sold}" data-vehicles="{len(rows)}" data-newest="{max(row['latest_filed'] for row in rows)}"><header><div><p class="spv-kicker">{E(company.get('sector',''))}</p><h2><a href="/companies/{E(slug)}/">{E(company['name'])}</a></h2></div></header><dl class="spv-summary"><div><dt>Vehicles</dt><dd>{len(rows)}</dd></div><div><dt>Reported sold</dt><dd>{E(spv_usd(sold))}</dd></div><div><dt>Investors</dt><dd>{investors:,}</dd></div><div><dt>New in last 12 months</dt><dd>{len(new)} · {E(spv_usd(new_sold))}</dd></div><div><dt>Median minimum</dt><dd>{E(spv_usd(median(minimums)) if minimums else 'Not stated')}</dd></div><div><dt>Share marketed under 506(c)</dt><dd>{marketed}%</dd></div></dl>{context}<p class="spv-platforms"><strong>Top platforms:</strong> {top}</p><svg class="spv-chart" viewBox="0 0 {len(year_counts)*48} 88" role="img" aria-label="{E(company['name'])} vehicles by first filing year">{bars}</svg><details><summary>Show {len(rows)} vehicles</summary><div class="spv-table-wrap"><table><thead><tr><th>First filed</th><th>Vehicle</th><th>Reported sold</th><th>Investors</th><th>Minimum</th><th>Sales comp</th><th>Exemption</th><th>Filing</th></tr></thead><tbody>{table_rows}</tbody></table></div></details></article>'''
 cards=[(slug,rows) for slug,rows in spvs_by_slug.items() if rows];cards.sort(key=lambda item:-sum(row['sold_usd'] or 0 for row in item[1]))
 total_sold=sum(row['sold_usd'] or 0 for row in spv_rows);total_investors=sum(row['investors'] or 0 for row in spv_rows);new_total=sum(row['first_filed_date']>=cutoff for row in spv_rows)
 return f'''<section class="spv-page" id="spv-tracker" aria-labelledby="spv-title"><header class="valuation-head"><div><h1 id="spv-title">SPV tracker.</h1><p>Special purpose vehicles filing with the SEC to invest in the most-watched private companies.</p></div><a href="/valuations/" class="valuation-directory-link">Valuation history <span aria-hidden="true">→</span></a></header><div class="valuation-method"><strong>Straight from SEC filings.</strong> Every vehicle below filed a Form D, the notice required when a private fund sells securities. Amounts are cumulative and self-reported as of each vehicle's latest filing. Form D does not disclose price, valuation or fees. Vehicles are found by name, so counts are a floor. <a href="https://github.com/JosephTPL/Website/blob/main/content/data/spvs_method.md" rel="noopener">How we built this ↗</a></div><section class="spv-stats"><div><strong>{len(spv_rows)}</strong><span>Vehicles tracked</span></div><div><strong>{E(spv_usd(total_sold))}</strong><span>Reported sold</span></div><div><strong>{total_investors:,}</strong><span>Investors</span></div><div><strong>{new_total}</strong><span>New vehicles, last 12 months</span></div></section><p class="spv-as-of">Filings through {spv_as_of.strftime('%b %d, %Y').replace(' 0',' ')}.</p><section class="spv-controls" aria-label="SPV tracker controls"><label>Search <input type="search" id="spv-search" placeholder="Company, vehicle, platform or manager"></label><button type="button" id="spv-recent" aria-pressed="false">Last 12 months only</button><label>Sort <select id="spv-sort"><option value="sold">Reported sold</option><option value="vehicles">Vehicles</option><option value="newest">Newest filing</option><option value="name">Name</option></select></label><span id="spv-count" aria-live="polite">{len(cards)} of {len(cards)} companies</span></section><div class="spv-cards">{''.join(card(slug,rows) for slug,rows in cards)}</div><p class="valuation-footnote">Source: SEC EDGAR Form D filings. Not an offer, solicitation or investment advice.</p></section>'''

if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir()
for f in (ROOT/'assets').iterdir():
 if f.is_file():shutil.copy2(f,OUT/f.name)
 elif f.is_dir():shutil.copytree(f,OUT/f.name)
shutil.copy2(ROOT/'assets'/'enhancements.css',OUT/f'enhancements-{enhancements_version}.css')
shutil.copytree(ROOT/'media',OUT/'media')
profile_directory=[]
for company in companies.values():
 row=latest_valuation(company['slug'])
 profile_directory.append({'name':company['name'],'slug':company['slug'],'sector':company.get('sector','Other / Diversified'),'status':company.get('company_status','private'),'parent':company.get('parent',''),'deal_value':company.get('deal_value',''),'website':company.get('website',''),'logo':company.get('intelligence',{}).get('logo',''),'valuation':row['valuation'] if row else None,'valuation_label':money_b(row['valuation']) if row else 'No disclosed valuation','valuation_date':row['date'] if row else ''})
directory_script=OUT/'companies.js'
directory_script.write_text(directory_script.read_text().replace('/* PROFILE_DIRECTORY */',json.dumps(profile_directory,separators=(',',':')).replace('</','<\\/')))
companies_script_version=hashlib.sha256(directory_script.read_bytes()).hexdigest()[:12]
spvs_script_version=hashlib.sha256((OUT/'spvs.js').read_bytes()).hexdigest()[:12]
# The landing page is the publication's evergreen editorial entrance. Weekly briefs
# remain available at their own stable archive URLs.
s=shell('home','The companies you can’t buy. The research you can.','Independent research on the private companies shaping public markets.','/')
s.body['data-page-view']='home';configure_nav(s,'home')
for selector in ['.landing-hero','.page-heading','.start-here','.continue-reading','.controls','#research-grid','.empty','.subscribe-panel','#about']:
 for el in list(s.select(selector)):
  container=el.find_parent('section') if selector in ('#research-grid','.empty') else el
  if container:container.decompose()
main=s.select_one('main');main.insert(0,soup(landing_markup()))
write(s,'/')
for archive_slug,archive in weekly_archives:
 s=shell('home',archive['title'],archive['intro'],f'/weekly/{archive_slug}/')
 s.body['data-page-view']='home';configure_nav(s,'home')
 for selector in ['.landing-hero','.page-heading','.start-here','.continue-reading','.controls','#research-grid','.empty','#about']:
  for el in list(s.select(selector)):
   container=el.find_parent('section') if selector in ('#research-grid','.empty') else el
   if container:container.decompose()
 s.select_one('main').insert(0,soup(weekly_markup(archive)))
 write(s,f'/weekly/{archive_slug}/')

# Company research and general articles live together in one searchable archive.
s=shell('home',settings['library_title'],settings['library_subtitle'],'/research/')
s.body['data-page-view']='library';s.body['data-library-title']=settings['library_title'];s.body['data-library-subtitle']=settings['library_subtitle'];s.body['data-insights-title']=settings['insights_title'];s.body['data-insights-subtitle']=settings['insights_subtitle']
s.body['class']=['research-archive']
configure_nav(s,'library')
for link in s.select('nav[aria-label="Primary"] a[data-view="library"]'):link['href']='/research/'
set_text(s,'#mission-eyebrow',settings.get('mission_eyebrow','PRIVATE MARKETS / INDEPENDENT RESEARCH'));set_text(s,'#mission-title',settings.get('mission_title','Know the business before the ticker.'));set_text(s,'#mission-text',settings.get('mission_text','The Private Ledger exists to make the private markets more legible: one company, one business model, and one hard question at a time.'));set_text(s,'#mission-secondary',settings.get('mission_secondary','See the incentives, economics, and risks beneath the headline before a company reaches the public market.'))
set_text(s,'#view-title','In Depth Articles');set_text(s,'#view-subtitle','Companies shaping the future. Essential Reads');set_text(s,'#about h2',settings['about_title']);set_text(s,'#about p:last-child',settings['about_text']);s.select_one('.page-heading .overline').decompose()
about_section=s.select_one('#about')
if about_section:about_section.decompose()
count=s.select_one('.library-count')
if count:count.decompose()
for selector in ['.landing-hero','#start-here','#continue-reading']:
 el=s.select_one(selector)
 if el:el.decompose()
tabs=soup('<div class="archive-tabs" role="group" aria-label="Research type"><button class="archive-tab active" type="button" data-type="deep-dives" aria-pressed="true">Deep dives</button><button class="archive-tab" type="button" data-type="articles" aria-pressed="false">Articles</button></div>')
s.select_one('.page-heading').insert_after(tabs)
grid=s.select_one('#research-grid');grid.clear()
for i,a in enumerate(ordered):
 name=a.get('card_title') or a['title'];img=f'<img src="{E(a["cover_image"])}" alt="{E(a.get("cover_alt",name))}" loading="lazy" decoding="async">' if a.get('cover_image') else ''
 kind='General articles' if a['sector']=='Insights' else 'Deep dive';member='<span class="member-label">Members only</span>' if a.get('excerpt') else ''
 cta='Read article →' if kind=='General articles' else 'Begin with the breakdown →'
 markup=f'''<article class="card" data-slug="{a['slug']}" data-sector="{E(a['sector'])}" data-kind="{E(kind)}" data-order="{i}" data-name="{E(name)}" data-search="{E(name+' '+a['summary']+' '+a['sector'])}"><a class="card-cover cover-refined" href="{a['url']}" aria-label="Read {E(name)}">{img}<span class="cover-caption">{E(settings['site_name'].upper())}</span></a><div class="card-content"><div class="research-labels"><span class="sector-inline">{E(kind if kind=='General articles' else a['sector'])}</span>{member}</div><h3><a href="{a['url']}">{E(name)}</a></h3><p class="description">{E(a['summary'])}</p><div class="card-meta"><span>{date_text(a['date'])}</span><span>{a['minutes']} min</span></div><a class="read-button" href="{a['url']}">{cta}</a><button class="card-save" type="button" data-save="{a['slug']}" aria-pressed="false">Save for later</button></div></article>'''
 put(grid,markup)
write(s,'/research/')

# Keep the former archive URL working while directing readers to the unified Research page.
legacy=soup('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>General articles | The Private Ledger</title><meta http-equiv="refresh" content="0; url=/research/?type=articles"><link rel="canonical" href="/research/?type=articles"></head><body><p>General articles are now part of <a href="/research/?type=articles">Research</a>.</p></body></html>')
write(legacy,'/insights/')

for a in ordered:
 s=shell('article',a['title'],a['summary'],a['url'],a.get('cover_image',''));s.body['data-article']=a['slug'];s.body['data-title']=a.get('card_title') or a['title'];s.body['data-sector']=a['sector']
 configure_nav(s,'insights' if a['sector']=='Insights' else 'library')
 head=s.select_one('.article-head');set_text(head,'h1',a['title']);set_text(head,'.subtitle',a['summary']);head.select_one('.overline').decompose();set_text(head,'.author div span',date_text(a['date'])+' · '+str(a['minutes'])+' min read')
 for x in s.select('.brief,.facts,.excerpt-notice'):x.decompose()
 for button in s.select('[data-save]'):button['data-save']=a['slug'];button['aria-pressed']='false';button.attrs.pop('aria-label',None);button.string='Save for later'
 body=s.select_one('.article-body');body.clear();body.append(link_substack_mentions(clean(a['body'])))
 mapping={r['title']:r['id'] for r in a.get('section_anchors',[])};used=set(mapping.values());toc=[]
 for i,h in enumerate(body.select('h2,h3')):
  title=h.get_text(' ',strip=True);anchor=mapping.get(title) or h.get('id')
  if not anchor:
   anchor='section-'+str(i)
   while anchor in used:anchor+='-new'
  used.add(anchor);h['id']=anchor;toc.append((anchor,title))
 for r in a.get('references',[]):
  num=int(r['number']);back=body.find(id=f'footnote-anchor-{num}');backlink=f'#footnote-anchor-{num}' if back else '#article-body'
  put(body,f'<div class="footnote"><a class="footnote-number" id="footnote-{num}" href="{backlink}" aria-label="Return to reference {num}">{num}</a><div class="footnote-content">{clean(r["text"])}</div></div>')
 for img in body.select('img'):img['loading']='lazy';img['decoding']='async'
 for link in body.select('a[href^="#footnote-"]'):
  if not s.find(id=link['href'][1:]):link['href']=a.get('original_url') or '#article-body'
 for t in s.select('.contents,#mobile-contents'):
  t.clear()
  if t.get('class')==['contents']:pass
  if a.get('brief',{}).get('thesis'):put(t,'<a href="#brief">The 60-second brief</a>')
  for anchor,title in toc:put(t,f'<a href="#{E(anchor)}">{E(title)}</a>')
 brief=a.get('brief') or {}
 if brief.get('thesis'):
  body.insert_before(soup(f'''<details class="brief brief-compact" id="brief"><summary><span>The 60-second brief<small>Thesis, risks, and what to watch</small></span><span class="details-icon" aria-hidden="true">＋</span></summary><div class="brief-content"><div class="brief-heading"><span>ABOUT 1 MINUTE</span></div><p class="brief-thesis">{E(brief['thesis'])}</p><ul>{''.join('<li>'+E(t)+'</li>' for t in brief.get('takeaways',[]))}</ul><div class="brief-bottom"><div><h3>The risk</h3><p>{E(brief.get('risk',''))}</p></div><div><h3>What to watch</h3><p>{E(brief.get('watch',''))}</p></div></div><p class="snapshot-note">A summary of the article published {date_text(a['date'])}. Figures and outlooks reflect that publication context.</p><a class="text-link" href="#article-body">Read the report below ↓</a></div></details>'''))
 company=companies.get(a.get('company',''))
 if company:
  body.insert_before(soup(f'<a class="snapshot-link brief-compact" id="company-facts" href="/companies/{company["slug"]}/"><span>Company snapshot<small>{E(company["name"])} · {date_text(company["as_of"])}</small></span><span class="details-icon" aria-hidden="true">→</span></a>'))
 if a.get('excerpt'):put(body,f'<section class="member-gate"><h2>Continue this report on Substack.</h2><p>The preview above is available here. The complete analysis and references are for paid members on Substack.</p><a class="primary-button" href="{E(a["original_url"])}">Unlock on Substack ↗</a></section>')
 if a.get('original_url'):put(body,f'<div class="original">Originally published in {E(settings["site_name"])}. <a href="{E(a["original_url"])}">View original post</a>.</div>')
 destination='/insights/' if a['sector']=='Insights' else '/research/'
 s.select_one('.back')['href']=destination;s.select_one('.back').string='← '+('General articles' if a['sector']=='Insights' else 'Research library')
 related=s.select_one('.related-grid');related.clear()
 picks=[articles[k] for k in a.get('related',[]) if k in articles and k!=a['slug']]
 if not picks:picks=[other for other in ordered if other['slug']!=a['slug'] and other['sector']==a['sector']][:3]
 for other in picks:put(related,f'<a class="related-card" href="{other["url"]}"><span>{E(other["sector"])}</span><h3>{E(other.get("card_title") or other["title"])}</h3><p>{E(other["summary"])}</p></a>')
 if not picks:s.select_one('.related')['hidden']=''
 schema={'@context':'https://schema.org','@type':'Article','headline':a['title'],'description':a['summary'],'datePublished':a['date'],'mainEntityOfPage':base+a['url'],'author':{'@type':'Organization','name':settings['site_name']}}
 put(s.head,'<script type="application/ld+json">'+json.dumps(schema).replace('<','\\u003c')+'</script>');write(s,a['url'])

for company in companies.values():
 route='/companies/'+company['slug']+'/'
 s=shell('about',company['name'],company['summary'],route,company.get('image',''));
 configure_nav(s,'companies')
 main=s.select_one('main');footer=main.select_one('footer').extract();subscribe=main.select_one('.subscribe-panel').extract();main.clear()
 if company.get('intelligence'):
  put(main,f'<a class="back" href="/companies/">← All companies</a>'+intelligence_profile(company))
 else:
  put(main,f'<a class="back" href="/research/">← Research library</a><article class="reading-paper company-profile"><h1>{E(company["name"])}</h1><p class="subtitle">{E(company["summary"])}</p></article>')
  paper=main.select_one('article')
  if company.get('image'):put(paper,f'<img class="profile-image" src="{E(company["image"])}" alt="{E(company.get("image_alt",company["name"]))}" loading="lazy">')
  put(paper,'<div class="article-body">'+str(clean(company.get('overview','')))+'</div><section class="facts">'+facts(company)+'</section>')
  if company.get('report') in articles:put(paper,f'<a class="primary-button" href="{articles[company["report"]]["url"]}">Read the company breakdown →</a>')
  put(paper,human_verification(company))
 main.append(subscribe);main.append(footer);write(s,route)

# A separate, editorial directory makes the company universe useful even when no long-form report exists yet.
s=shell('home','Companies','A concise directory of notable private companies and former private companies covered by The Private Ledger.','/companies/')
s.body['data-page-view']='companies'
configure_nav(s,'companies')
main=s.select_one('main');main.clear()
put(main,'<section class="company-directory"><header class="directory-head"><h1>Briefs:</h1></header><section class="directory-tools" aria-label="Search companies"><label class="search"><input id="company-search" type="search" placeholder="Search companies" aria-label="Search companies"></label><span id="company-result-count"></span></section><div class="company-directory-grid" id="company-directory-grid"></div></section>')
grid=s.select_one('#company-directory-grid')
for i,c in enumerate(sorted(companies.values(),key=lambda x:(x.get('directory_rank',999),x['name']))):
 notes=''.join('<li>'+E(note)+'</li>' for note in c.get('directory_notes',[])[:2])
 funding=E(c.get('latest_round') or next((f.get('value','') for f in c.get('facts',[]) if 'fund' in f.get('label','').lower()),'Not yet added'))
 aliases=' '.join(c.get('aliases',[]))
 put(grid,f'''<article class="company-directory-card" data-search="{E(c['name']+' '+aliases+' '+c.get('sector','')+' '+c.get('summary',''))}"><div class="company-card-kicker"><span>#{int(c.get('directory_rank',i+1)):02d}</span><span>{E(c.get('sector',''))}</span></div><h2><a href="/companies/{c['slug']}/">{E(c['name'])}</a></h2><p class="company-directory-summary">{E(c.get('summary',''))}</p><div class="funding-context"><span>Latest disclosed financing</span><strong>{funding}</strong></div><div class="thesis-columns"><div><span class="thesis-label bull">Bull case</span><p>{E(c.get('bull_case','Editorial note coming soon.'))}</p></div><div><span class="thesis-label bear">Bear case</span><p>{E(c.get('bear_case','Editorial note coming soon.'))}</p></div></div>{'<ul class="company-directory-notes">'+notes+'</ul>' if notes else ''}<a class="company-profile-link" href="/companies/{c['slug']}/">View company profile →</a></article>''')
put(s.head,f'<script defer src="/companies.js?v={companies_script_version}"></script>')
write(s,'/companies/')

# The calendar separates filed transactions from market watchlist names so timing stays honest.
s=shell('home',ipo_calendar['title'],ipo_calendar['intro'],'/ipo-calendar/')
s.body['data-page-view']='ipo';configure_nav(s,'ipo')
main=s.select_one('main');footer=main.select_one('footer').extract();subscribe=main.select_one('.subscribe-panel').extract();main.clear();put(main,ipo_markup());main.append(subscribe);main.append(footer)
write(s,'/ipo-calendar/')

# The chart is intentionally limited to profiles with multiple dated valuation events.
s=shell('home','Private valuation history','Reported private-company valuation histories at confirmed events.','/valuations/')
s.body['data-page-view']='valuations';configure_nav(s,'valuations')
main=s.select_one('main');footer=main.select_one('footer').extract();subscribe=main.select_one('.subscribe-panel').extract();main.clear();put(main,valuation_chart_markup());main.append(subscribe);main.append(footer)
put(s.head,'<script defer src="/valuations.js"></script>')
write(s,'/valuations/')

s=shell('home','SPV tracker','SEC Form D filings for special purpose vehicles targeting covered private companies.','/spv-tracker/')
s.body['data-page-view']='spvs';configure_nav(s,'spvs')
main=s.select_one('main');footer=main.select_one('footer').extract();subscribe=main.select_one('.subscribe-panel').extract();main.clear();put(main,spv_tracker_markup());main.append(subscribe);main.append(footer)
put(s.head,f'<script defer src="/spvs.js?v={spvs_script_version}"></script>')
write(s,'/spv-tracker/')

about=read('content/settings/about.json');s=shell('about',about['title'],about['description'],'/about/');configure_nav(s,'about');main=s.select_one('main');footer=main.select_one('footer').extract();subscribe=main.select_one('.subscribe-panel').extract();about_body=clean(about['body']);hero=about_body.select_one('.about-hero');hero.decompose() if hero else None;main.clear();main.append(about_body);main.append(subscribe);main.append(footer);write(s,'/about/')
# The editor is a separate authenticated service, not a public editing API.
s=shell('about','Edit website','Open the secure content editor.','/admin/');configure_nav(s,'');s.select_one('main').clear();put(s.select_one('main'),'<section class="about-hero"><h1>Edit your publication.</h1><p>Sign in with your GitHub account to edit articles, company profiles, images, and homepage text.</p><a class="primary-button" href="https://app.pagescms.org">Open Pages CMS ↗</a></section>');put(s.head,'<meta name="robots" content="noindex">');write(s,'/admin/')
routes=['/','/research/','/insights/','/companies/','/ipo-calendar/','/valuations/','/spv-tracker/','/about/']+[a['url'] for a in ordered]+['/companies/'+c['slug']+'/' for c in companies.values()]
(OUT/'sitemap.xml').write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+E(base+r)+'</loc></url>' for r in routes)+'</urlset>')
(OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: '+base+'/sitemap.xml\n')
print(f'Built {len(articles)} published articles, {len(companies)} company profiles, and editable site pages.')
