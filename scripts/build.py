"""Build the publication from CMS-managed content. No CMS runtime or database required."""
from pathlib import Path
from datetime import date, datetime
from urllib.parse import urlsplit, unquote
import calendar, html, json, os, re, shutil, sys
from bs4 import BeautifulSoup, NavigableString
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'_site'
E=html.escape

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
  record['slug']=slug
  if record.get('status')=='Published':result[slug]=record
 return result

settings=read('content/settings/site.json');weekly=read('content/settings/weekly.json');ipo_calendar=read('content/settings/ipo-calendar.json');articles=records('articles');companies=records('companies')
base=os.environ.get('URL') or settings['site_url'];base=base.rstrip('/')
if urlsplit(base).scheme not in ('http','https'):raise ValueError('Site URL must start with https://')
for a in articles.values():
 a['date']=a['date'][:10];datetime.strptime(a['date'],'%Y-%m-%d')
 a['minutes']=max(1,round(len(soup(a['body']).get_text(' ',strip=True).split())/220));a['url']='/articles/'+a['slug']+'/'
ordered=sorted(articles.values(),key=lambda a:(a['date'],a['title']),reverse=True)

def date_text(value):return datetime.strptime(value[:10],'%Y-%m-%d').strftime('%b %d, %Y').replace(' 0',' ')
def facts(c):
 rows=''.join(f'<div><dt>{E(f["label"])}</dt><dd>{E(f["value"])}</dd><p>{E(f.get("note",""))}</p>'+ (f'<a href="{E(f["source"])}">Source <span class="sr-only">for {E(f["label"])}</span> ↗</a>' if f.get('source') else '')+'</div>' for f in c.get('facts',[]))
 return f'<div class="facts-inner"><p class="snapshot-note">Figures as of {date_text(c["as_of"])}. Estimates and projections are labelled separately.</p><dl class="facts-grid">{rows}</dl></div>'

def intelligence_profile(c):
 d=c['intelligence']
 metrics=''.join(f'<div><strong>{E(item["value"])}</strong><span>{E(item["label"])}</span><small>{E(item.get("note",""))}</small></div>' for item in d['metrics'])
 history=''.join(f'<li><strong>{E(item["value"])}</strong><span>→</span><small>{E(item["date"])}</small><em>{E(item["round"])}</em></li>' for item in d['valuation_history'])
 changed=''.join(f'<li><time>{E(item["date"])}</time><p>{E(item["text"])}</p></li>' for item in d['changed'])
 takeaways=''.join(f'<li><span>{i:02d}</span><p>{E(item)}</p></li>' for i,item in enumerate(d['takeaways'],1))
 quick=''.join(f'<dt>{E(label)}</dt><dd>{E(value)}</dd>' for label,value in d['quick_facts'])
 sources=''.join(f'<li><a href="{E(item["url"])}">{E(item["label"])} <span>↗</span></a></li>' for item in d['sources'])
 logo=f'<img src="{E(d["logo"])}" alt="{E(c["name"])} logo" loading="lazy">' if d.get('logo') else ''
 return f'''<section class="intelligence-profile">
 <header class="intelligence-header"><div><p class="overline">{E(d["kicker"])}</p><h1>{E(c["name"])}</h1><p class="intelligence-meta">{E(c["sector"])} <span>·</span> {E(d["location"])} <span>·</span> {E(d["status"])}</p><p class="intelligence-description">{E(d["description"])}</p></div><div class="intelligence-logo">{logo}<strong>{E(c["name"])}</strong></div></header>
 <section class="intelligence-metrics">{metrics}</section>
 <div class="intelligence-content"><div class="intelligence-main"><section><h2>The Company</h2>{''.join('<p>'+E(p)+'</p>' for p in d['company'])}</section><section><h2>Why It Matters</h2><p>{E(d["why_it_matters"])}</p></section><section><h2>Valuation History</h2><ol class="valuation-history">{history}</ol></section><section><h2>What Changed</h2><ol class="change-log">{changed}</ol></section></div><aside class="intelligence-aside"><section><h2>Key Takeaways</h2><ol class="takeaways">{takeaways}</ol></section><section><h2>Quick Facts</h2><dl class="quick-facts">{quick}</dl></section><section><h2>Sources</h2><ul class="intelligence-sources">{sources}</ul></section></aside></div>
 </section>'''

def shell(kind,title,description,route,image=''):
 s=soup((ROOT/'templates'/f'{kind}.html').read_text());s.title.string=title+' | '+settings['site_name']
 favicon=s.select_one('link[rel="icon"]');favicon['href']='/favicon.png?v=3';favicon['sizes']='64x64';favicon['type']='image/png'
 for asset in s.select('link[href="/enhancements.css"],script[src="/enhancements.js"]'):
  asset['href' if asset.name=='link' else 'src']=('/enhancements.css?v=2' if asset.name=='link' else '/enhancements.js?v=2')
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
  if top_subscribe:top_subscribe.insert_before(soup(f'<a class="top-link top-discord" href="{E(settings["discord_url"])}" rel="noopener">Join our Discord <span aria-hidden="true">↗</span></a>'))
 for panel in s.select('.subscribe-panel'):
  set_text(panel,'h2',settings['subscribe_title']);set_text(panel,'p:not(.eyebrow)',settings['subscribe_text'])
 brandmark=s.select_one('.brandmark')
 if brandmark:
  brandmark.clear();put(brandmark,'<img src="/compass-logo.png" alt="" aria-hidden="true">')
 brand=s.select_one('.brand>span:last-child');brand.clear();brand.append(settings['site_name'].upper());put(brand,'<small>'+E(settings['tagline'])+'</small>')
 if s.select_one('footer'):s.select_one('footer').clear();put(s.select_one('footer'),f'© {date.today().year} {E(settings["site_name"])}')
 return s

def write(s,route):
 p=OUT/route.strip('/')/'index.html';p.parent.mkdir(parents=True,exist_ok=True)
 rendered=str(s)
 if not route.startswith('/articles/'):
  rendered=rendered.replace(' — ', ', ').replace('—','-')
 p.write_text(rendered)

def configure_nav(s,active):
 """Keep the publication's three editorial destinations distinct in every page shell."""
 nav=s.select_one('nav[aria-label="Primary"]')
 home=nav.select_one('[data-view="library"]')
 home['data-view']='home';home['href']='/';home.clear();put(home,'<svg aria-hidden="true" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" viewBox="0 0 24 24"><path d="M4 4h6v16H4z M14 4h6v16h-6z"></path></svg> This week')
 research=soup('<a data-view="library" href="/research/?type=deep-dives"><svg aria-hidden="true" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" viewBox="0 0 24 24"><path d="M4 4h6v16H4z M14 4h6v16h-6z"></path></svg>Research</a>').a
 home.insert_after(research)
 for old_link in nav.select('a[data-view="insights"]'):old_link.decompose()
 ipo=soup('<a data-view="ipo" href="/ipo-calendar/"><svg aria-hidden="true" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"></rect><path d="M16 3v4M8 3v4M3 10h18"></path></svg>IPO calendar</a>').a
 research.insert_after(ipo)
 valuations=soup('<a data-view="valuations" href="/valuations/"><svg aria-hidden="true" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" viewBox="0 0 24 24"><path d="M4 18V6m0 12h16"></path><path d="m7 15 4-4 3 2 4-6"></path></svg>Valuations</a>').a
 ipo.insert_after(valuations)
 for link in nav.select('a'):
  link.attrs.pop('aria-current',None)
  link['class']=['active'] if link.get('data-view')==active else []

def weekly_chart_markup():
 """A single evidence-led chart for the weekly front page, drawn from profile data."""
 company=companies.get('databricks',{})
 events=[]
 for item in company.get('intelligence',{}).get('valuation_history',[]):
  raw=str(item.get('value','')).replace('~','').replace(',','').replace('>','').replace('<','').strip().rstrip('+')
  match=re.fullmatch(r'\$(\d+(?:\.\d+)?)([MBT])',raw)
  if not match:continue
  amount=float(match.group(1))*({'M':.001,'B':1,'T':1000}[match.group(2)])
  events.append({'amount':amount,'value':item['value'],'date':item['date'],'round':item.get('round','')})
 if len(events)<2:return ''
 width,height,left,right,top,bottom=760,274,58,28,26,206
 maximum=max(event['amount'] for event in events)
 ceiling=max(10,((int(maximum)+49)//50)*50)
 step=(width-left-right)/(len(events)-1)
 points=[]
 for index,event in enumerate(events):
  x=left+index*step;y=bottom-(event['amount']/ceiling)*(bottom-top)
  points.append((x,y,event))
 path=' '.join((f'M {x:.1f} {y:.1f}' if index==0 else f'L {x:.1f} {y:.1f}') for index,(x,y,event) in enumerate(points))
 grid=''.join(f'<line x1="{left}" y1="{bottom-(value/ceiling)*(bottom-top):.1f}" x2="{width-right}" y2="{bottom-(value/ceiling)*(bottom-top):.1f}" class="weekly-chart-grid"/><text x="{left-12}" y="{bottom-(value/ceiling)*(bottom-top)+5:.1f}" text-anchor="end" class="weekly-chart-axis">${value:g}B</text>' for value in (0,ceiling/2,ceiling))
 dots=''.join(f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="5" class="weekly-chart-point" data-date="{E(event["date"])}" data-value="{E(event["value"])}" data-round="{E(event["round"])}" tabindex="0" role="button" aria-label="{E(event["date"])}: {E(event["value"])}. {E(event["round"])}."><title>{E(event["date"])}: {E(event["value"])}. {E(event["round"])}.</title></circle><text x="{x:.1f}" y="{bottom+31}" text-anchor="middle" class="weekly-chart-date">{E(event["date"])}</text></g>' for x,y,event in points)
 source=company.get('facts',[{}])[0].get('source','/companies/databricks/')
 return f'''<section class="weekly-chart weekly-chart--sidebar" aria-labelledby="weekly-chart-title"><header class="weekly-chart-head"><div><p class="overline">MOST IMPORTANT CHART THIS WEEK</p><h2 id="weekly-chart-title">Databricks valuation history.</h2><p>Its August financing valued Databricks at $190B.</p></div><div class="weekly-chart-stat"><strong>$190B</strong><span>Latest reported valuation</span></div></header><div class="weekly-chart-plot"><svg viewBox="0 0 {width} {height}" role="img" aria-label="Databricks reported valuation rose from 38 billion dollars in August 2021 to 190 billion dollars in August 2026">{grid}<path d="{path}" class="weekly-chart-line"/>{dots}</svg><div class="weekly-chart-tooltip" hidden aria-live="polite"></div></div><footer><a href="/companies/databricks/">Profile →</a><a href="/valuations/">Valuation desk →</a><a href="{E(source)}" rel="noopener">Funding report ↗</a></footer></section>'''

def weekly_markup():
 def item_markup(item,index,lead=False):
  return f'''<article class="weekly-item{' weekly-item--lead' if lead else ''}"><div><span class="weekly-number">{index:02d}</span><span class="weekly-tag">{E(item['tag'])}</span></div><h2>{E(item['company'])}</h2><p>{E(item['text'])}</p><a href="{E(item['source'])}" rel="noopener">Source ↗</a></article>'''
 lead=item_markup(weekly['items'][0],1,True)
 items=''.join(item_markup(item,index) for index,item in enumerate(weekly['items'][1:],2))
 return f'''<section class="weekly-brief" aria-labelledby="weekly-title"><header class="weekly-head"><div><p class="overline">THE PRIVATE LEDGER / WEEKLY BRIEF</p><h1 id="weekly-title">{E(weekly['title'])}</h1><p class="subtitle">{E(weekly['intro'])}</p></div><p class="weekly-date">Last week<br/><strong>{E(weekly['period'])}</strong><span>Next update: {E(weekly['next_update'])}</span></p></header><div class="weekly-lead-layout">{lead}{weekly_chart_markup()}</div><div class="weekly-grid weekly-grid--secondary">{items}</div><div class="weekly-footer"><span>Updated every Sunday.</span><a class="text-link" href="/research/">Explore company research →</a></div></section>'''

def ipo_markup():
 """A true month view; undated candidates stay out of arbitrary day cells."""
 month=ipo_calendar['calendar']['month'];year=int(ipo_calendar['calendar']['year']);month_number=int(ipo_calendar['calendar']['month_number'])
 items=[item for period in ipo_calendar['periods'] for item in period['items']]
 events={};lead_in_events={}
 for item in items:
  if item.get('date'):
   target=events if int(item.get('month',month_number))==month_number else lead_in_events
   target.setdefault(str(item['date']),[]).append(item)
 earnings={}
 for item in ipo_calendar.get('earnings',[]):earnings.setdefault(str(item['date']),[]).append(item)
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
 tbd=''.join(f'''<article class="ipo-tbd"><div><span class="ipo-status {E(item['status'].lower().replace(' ','-'))}">{E(item['status'])}</span><span class="ipo-valuation">{E(item['valuation'])}</span></div><h2>{E(item['company'])}</h2><p>{E(item['note'])}</p><a href="{E(item['source'])}" rel="noopener">Source ↗</a></article>''' for item in items if not item.get('date'))
 earnings_list=''.join(f'''<article class="ipo-list-item"><header><strong>{E(item['company'])}</strong><span class="ticker">{E(item['ticker'])}</span></header><p class="timing">{E(str(item['date']))} · {E(item['timing'])}</p><p>{E(item['impact'])}</p><a class="earnings-event-mini" href="{E(item['source'])}" rel="noopener">Earnings source ↗</a></article>''' for item in ipo_calendar.get('earnings',[]))
 return f'''<section class="ipo-calendar" aria-labelledby="ipo-title"><header class="ipo-head"><div><p class="overline">THE PRIVATE LEDGER / IPO CALENDAR</p><h1 id="ipo-title">{E(ipo_calendar['title'])}</h1><p class="subtitle">{E(ipo_calendar['intro'])}</p></div><p class="ipo-as-of">As of<br/><strong>{E(ipo_calendar['as_of'])}</strong></p></header><div class="ipo-note"><strong>How to read this.</strong> {E(ipo_calendar['disclaimer'])}</div><div class="ipo-view-toggle" role="group" aria-label="IPO calendar view"><button class="view-toggle active" type="button" data-view="calendar" aria-pressed="true">Calendar</button><button class="view-toggle" type="button" data-view="list" aria-pressed="false">Earnings list</button></div><div class="ipo-view-content" data-view="calendar"><section class="ipo-month" aria-labelledby="ipo-month-title"><header><div><p class="overline">UPCOMING MONTH</p><h2 id="ipo-month-title">{E(month)}</h2></div><p><strong>Public earnings watch.</strong> Hover a marker for The Ledger's private-market read-through.</p></header><div class="ipo-weekdays"><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span></div><div class="ipo-month-grid">{''.join(weeks)}</div><p class="ipo-empty"><strong>No confirmed $5B+ IPO dates are on the public calendar for {E(month)}.</strong> Public-company earnings markers use confirmed dates where disclosed and labelled estimates otherwise.</p></section><section class="ipo-tbd-section" aria-labelledby="ipo-tbd-title"><header><p class="overline">DATE TO BE ANNOUNCED</p><h2 id="ipo-tbd-title">The $5B+ IPO watchlist.</h2><p>Private-market giants with a reported filing, window, or credible path to market, but no confirmed day to put on the calendar yet.</p></header><div class="ipo-tbd-grid">{tbd}</div></section></div><section class="ipo-earnings-list ipo-view-content" data-view="list" hidden><header><p class="overline">PUBLIC EARNINGS WATCH</p><h2>Private-market read-throughs.</h2><p>Confirmed earnings dates and the public-company results most relevant to private-market investors.</p></header><div class="earnings-list-items">{earnings_list}</div></section></section>'''

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
 """A small, evidence-led comparison set, rather than synthetic daily price data."""
 # The ten businesses covered in the publication. Isomorphic Labs remains visible below
 # as a research profile, but has no disclosed valuation event to draw responsibly.
 selected=('saronic','isomorphic-labs','substack','polymarket','spacex','anthropic','openai','stripe','bytedance','anduril',
           'tether','databricks','waymo','reliance-retail','ant-group','revolut','reliance-jio','deepseek','ripple','cognition')
 selected=selected+('ramp','prometheus','figure','canva','safe-superintelligence','crusoe','vast-data','scale-ai','the-boring-company','kalshi')
 selected=selected+('rippling','epic-games','discord','plaid','mistral-ai','kraken','shield-ai','notion','whatnot',
                    'cohere','elevenlabs','mercor','lovable','perplexity','lukoil','citadel-securities','etched','helsing','fireworks-ai')
 selected=selected+('moonshot-ai','figure-ai','jd-digits','authentic-brands-group','vanta','snyk','abnormal-security','chobani','postman','brex')
 selected=selected+('fluidstack','deel','airtable','hugging-face','groq','anysphere','luma-ai','skydio','redwood-materials','hadrian')
 series=[]
 for slug in selected:
  company=companies.get(slug)
  if not company:continue
  events=[]
  for item in company.get('intelligence',{}).get('valuation_history',[]):
   value=str(item.get('value','')).replace('~','').replace(',','').replace('>','').replace('<','').strip().rstrip('+')
   match=re.fullmatch(r'\$(\d+(?:\.\d+)?)([MBT])',value)
   when=chart_date(item.get('date',''))
   if not match or not when:continue
   unit=match.group(2);amount=float(match.group(1))*(1000 if unit=='T' else .001 if unit=='M' else 1)
   if amount<=0:continue
   events.append({'date':when,'label':item['date'],'value':item['value'],'amount':amount,'round':item.get('round','')})
  if len(events)>1:
   series.append({'name':company['name'],'slug':slug,'url':'/companies/'+slug+'/', 'events':events})
 data=json.dumps(series,separators=(',',':')).replace('</','<\\/')
 default_series={'spacex','anthropic','openai'}
 chart_colors=('#ff5c58','#5d9cff','#f3ab39','#58b293','#c87fe8','#56c3bf','#e07a9e','#d8cb70','#9d88e9','#ec8c54','#61a4d9','#a9b75c','#db7690','#b491df','#4eb2a7','#dfbf65','#7697e8','#df6e67','#73bd83','#e69aab','#4f86aa','#a7d2c2','#d99845','#a382bd','#b6c56b','#c56e62','#78aacd','#cba85f','#84a86b')
 return f'''<section class="valuation-page" aria-labelledby="valuation-title"><header class="valuation-head"><div><p class="overline">THE PRIVATE LEDGER / DATA DESK</p><h1 id="valuation-title">Private valuation history.</h1><p>Reported point-in-time valuations at confirmed financings and other disclosed liquidity events.</p></div><a href="/companies/" class="valuation-directory-link">Browse companies <span aria-hidden="true">→</span></a></header><div class="valuation-method"><strong>Not a market-price chart.</strong> Each step marks a disclosed valuation event. A flat line means no newer confirmed value is recorded, not that the company’s value was unchanged.</div><section class="valuation-chart-shell" aria-label="Private valuation comparison"><div class="valuation-toolbar"><div class="valuation-picker"><p class="valuation-control-label">COMPARE COMPANIES</p><label class="valuation-search"><span class="sr-only">Search a company</span><input id="valuation-company-search" type="search" placeholder="Search companies" autocomplete="off"></label><div id="valuation-search-results" class="valuation-search-results" hidden></div><div id="valuation-selected" class="valuation-selected" aria-label="Companies shown"></div></div><div><p class="valuation-control-label">VIEW</p><div class="valuation-range" aria-label="Chart view"><button type="button" data-range="1">1Y</button><button type="button" data-range="3">3Y</button><button type="button" data-range="5">5Y</button><button type="button" data-range="all" class="is-active">All</button><button type="button" class="valuation-index" aria-pressed="false">Index to zero</button></div></div></div><div class="valuation-chart" id="valuation-chart" data-valuation-series='{E(data)}'><div class="valuation-chart-canvas" role="img" aria-label="Reported private valuation history chart"></div><div class="valuation-tooltip" hidden></div></div><div class="valuation-legend" aria-label="Visible companies"></div><p class="valuation-unavailable">Isomorphic Labs is covered by The Ledger, but no valuation was publicly disclosed for its reported funding events. <a href="/companies/isomorphic-labs/">View profile →</a></p></section><p class="valuation-footnote">Figures are reported valuations, not continuous marks or investment advice. Click any company in the legend to read its profile.</p></section>'''

if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir()
for f in (ROOT/'assets').iterdir():
 if f.is_file():shutil.copy2(f,OUT/f.name)
 elif f.is_dir():shutil.copytree(f,OUT/f.name)
shutil.copytree(ROOT/'media',OUT/'media')
profile_slugs={company['name'].lower():company['slug'] for company in companies.values()}
profile_valuations={}
for company in companies.values():
 for metric in company.get('intelligence',{}).get('metrics',[]):
  if 'valuation' in metric.get('label','').lower() and metric.get('value'):
   profile_valuations[company['name'].lower()]=metric['value']
   break
profile_directory=[]
for company in companies.values():
 domain=''
 for fact in company.get('intelligence',{}).get('quick_facts',[]):
  if isinstance(fact,dict):label,value=fact.get('label',''),fact.get('value','')
  else:label,value=fact
  if label.lower()=='website':
   domain=value.replace('https://','').replace('http://','').split('/')[0]
   break
 if not domain:
  logo=company.get('intelligence',{}).get('logo','')
  match=re.search(r'domain=([^&]+)',logo)
  domain=match.group(1) if match else company['slug']+'.com'
 profile_directory.append([company['name'],profile_valuations.get(company['name'].lower(),'Undisclosed'),domain])
directory_script=OUT/'companies.js'
directory_script.write_text(directory_script.read_text().replace('/* PROFILE_SLUGS */',json.dumps(profile_slugs,sort_keys=True)).replace('/* PROFILE_VALUATIONS */',json.dumps(profile_valuations,sort_keys=True)).replace('/* PROFILE_DIRECTORY */',json.dumps(profile_directory,sort_keys=True)))
# The landing page is a concise weekly briefing; the two archives remain separate.
s=shell('home',weekly['title'],weekly['intro'],'/')
s.body['data-page-view']='home';configure_nav(s,'home')
for selector in ['.landing-hero','.page-heading','.start-here','.continue-reading','.controls','#research-grid','.empty']:
 for el in list(s.select(selector)):
  container=el.find_parent('section') if selector in ('#research-grid','.empty') else el
  if container:container.decompose()
main=s.select_one('main');main.insert(0,soup(weekly_markup()))
write(s,'/')

# Company research and general articles live together in one searchable archive.
s=shell('home',settings['library_title'],settings['library_subtitle'],'/research/')
s.body['data-page-view']='library';s.body['data-library-title']=settings['library_title'];s.body['data-library-subtitle']=settings['library_subtitle'];s.body['data-insights-title']=settings['insights_title'];s.body['data-insights-subtitle']=settings['insights_subtitle']
s.body['class']=['research-archive']
configure_nav(s,'library')
for link in s.select('nav[aria-label="Primary"] a[data-view="library"]'):link['href']='/research/'
set_text(s,'#mission-eyebrow',settings.get('mission_eyebrow','PRIVATE MARKETS / INDEPENDENT RESEARCH'));set_text(s,'#mission-title',settings.get('mission_title','Know the business before the ticker.'));set_text(s,'#mission-text',settings.get('mission_text','The Private Ledger exists to make the private markets more legible: one company, one business model, and one hard question at a time.'));set_text(s,'#mission-secondary',settings.get('mission_secondary','See the incentives, economics, and risks beneath the headline before a company reaches the public market.'))
set_text(s,'#view-title','Research');set_text(s,'#view-subtitle','Company deep dives and perspectives on private markets, together in one archive.');set_text(s,'#about h2',settings['about_title']);set_text(s,'#about p:last-child',settings['about_text'])
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
 markup=f'''<article class="card" data-slug="{a['slug']}" data-sector="{E(a['sector'])}" data-kind="{E(kind)}" data-order="{i}" data-name="{E(name)}" data-search="{E(name+' '+a['summary']+' '+a['sector'])}"><a class="card-cover cover-refined" href="{a['url']}" aria-label="Read {E(name)}">{img}<span class="cover-caption">{E(settings['site_name'].upper())}</span></a><div class="card-content"><span class="sector-inline">{E(kind if kind=='General articles' else a['sector'])}</span>{member}<h3><a href="{a['url']}">{E(name)}</a></h3><p class="description">{E(a['summary'])}</p><div class="card-meta"><span>{date_text(a['date'])}</span><span>{a['minutes']} min</span></div><a class="read-button" href="{a['url']}">Read {'article' if kind=='General articles' else 'research'} →</a><button class="card-save" type="button" data-save="{a['slug']}" aria-pressed="false">Save for later</button></div></article>'''
 put(grid,markup)
write(s,'/research/')

# Keep the former archive URL working while directing readers to the unified Research page.
legacy=soup('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>General articles | The Private Ledger</title><meta http-equiv="refresh" content="0; url=/research/?type=articles"><link rel="canonical" href="/research/?type=articles"></head><body><p>General articles are now part of <a href="/research/?type=articles">Research</a>.</p></body></html>')
write(legacy,'/insights/')

for a in ordered:
 s=shell('article',a['title'],a['summary'],a['url'],a.get('cover_image',''));s.body['data-article']=a['slug'];s.body['data-title']=a.get('card_title') or a['title'];s.body['data-sector']=a['sector']
 configure_nav(s,'insights' if a['sector']=='Insights' else 'library')
 head=s.select_one('.article-head');set_text(head,'h1',a['title']);set_text(head,'.subtitle',a['summary']);set_text(head,'.overline',a['sector']+' / '+('PERSPECTIVE' if a['sector']=='Insights' else 'COMPANY RESEARCH'));set_text(head,'.author div span',date_text(a['date'])+' · '+str(a['minutes'])+' min read')
 for x in s.select('.brief,.facts,.excerpt-notice'):x.decompose()
 for button in s.select('[data-save]'):button['data-save']=a['slug'];button['aria-pressed']='false';button.attrs.pop('aria-label',None);button.string='Save for later'
 body=s.select_one('.article-body');body.clear();body.append(link_substack_mentions(clean(a['body'])))
 if a.get('excerpt'):
  headings=body.select('h2,h3')
  if len(headings)>1:
   node=headings[1]
   while node:
    next_node=node.next_sibling;node.decompose();node=next_node
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
  if t.get('class')==['contents']:put(t,'<p class="overline">IN THIS RESEARCH</p>')
  if a.get('brief',{}).get('thesis'):put(t,'<a href="#brief">The 60-second brief</a>')
  for anchor,title in toc:put(t,f'<a href="#{E(anchor)}">{E(title)}</a>')
 brief=a.get('brief') or {}
 if brief.get('thesis'):
  body.insert_before(soup(f'''<details class="brief brief-compact" id="brief"><summary><span>The 60-second brief<small>Thesis, risks, and what to watch</small></span><span class="details-icon" aria-hidden="true">＋</span></summary><div class="brief-content"><div class="brief-heading"><p class="eyebrow">THE ESSENTIALS</p><span>ABOUT 1 MINUTE</span></div><p class="brief-thesis">{E(brief['thesis'])}</p><ul>{''.join('<li>'+E(t)+'</li>' for t in brief.get('takeaways',[]))}</ul><div class="brief-bottom"><div><h3>The risk</h3><p>{E(brief.get('risk',''))}</p></div><div><h3>What to watch</h3><p>{E(brief.get('watch',''))}</p></div></div><p class="snapshot-note">A summary of the article published {date_text(a['date'])}. Figures and outlooks reflect that publication context.</p><a class="text-link" href="#article-body">Read the report below ↓</a></div></details>'''))
 company=companies.get(a.get('company',''))
 if company:
  body.insert_before(soup(f'<a class="snapshot-link brief-compact" id="company-facts" href="/companies/{company["slug"]}/"><span>Company snapshot<small>{E(company["name"])} · {date_text(company["as_of"])}</small></span><span class="details-icon" aria-hidden="true">→</span></a>'))
 if a.get('excerpt'):body.insert_before(soup(f'<section class="member-gate"><p class="eyebrow">MEMBERS-ONLY RESEARCH</p><h2>Continue this report on Substack.</h2><p>The opening section is available here. The complete analysis and references are for paid members on Substack.</p><a class="primary-button" href="{E(a["original_url"])}">Unlock on Substack ↗</a></section>'))
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
  put(main,f'<a class="back" href="/research/">← Research library</a><article class="reading-paper company-profile"><p class="overline">{E(company["sector"])} / COMPANY PROFILE</p><h1>{E(company["name"])}</h1><p class="subtitle">{E(company["summary"])}</p></article>')
  paper=main.select_one('article')
  if company.get('image'):put(paper,f'<img class="profile-image" src="{E(company["image"])}" alt="{E(company.get("image_alt",company["name"]))}" loading="lazy">')
  put(paper,'<div class="article-body">'+str(clean(company.get('overview','')))+'</div><section class="facts">'+facts(company)+'</section>')
  if company.get('report') in articles:put(paper,f'<a class="primary-button" href="{articles[company["report"]]["url"]}">Read the company breakdown →</a>')
 main.append(subscribe);main.append(footer);write(s,route)

# A separate, editorial directory makes the company universe useful even when no long-form report exists yet.
s=shell('home','Companies','A concise directory of notable private companies.','/companies/')
s.body['data-page-view']='companies'
configure_nav(s,'companies')
main=s.select_one('main');main.clear()
put(main,'<section class="company-directory"><header class="directory-head"><p class="overline">THE PRIVATE LEDGER / COMPANY DIRECTORY</p><h1>Companies to know <em>before</em> they go public.</h1><p>A living editorial watchlist of 50 notable private businesses. Each card captures the business, the latest disclosed financing context, and the argument on both sides.</p><div class="directory-disclaimer"><strong>AI-assisted editorial notes.</strong> Bull and bear cases are research prompts, not investment advice. Funding information reflects the latest public disclosure recorded in each profile.</div></header><section class="directory-tools" aria-label="Search companies"><label class="search"><input id="company-search" type="search" placeholder="Search a company or sector…" aria-label="Search companies"></label><span id="company-result-count"></span></section><div class="company-directory-grid" id="company-directory-grid"></div></section>')
grid=s.select_one('#company-directory-grid')
for i,c in enumerate(sorted(companies.values(),key=lambda x:(x.get('directory_rank',999),x['name']))):
 notes=''.join('<li>'+E(note)+'</li>' for note in c.get('directory_notes',[])[:2])
 funding=E(c.get('latest_round') or next((f.get('value','') for f in c.get('facts',[]) if 'fund' in f.get('label','').lower()),'Not yet added'))
 put(grid,f'''<article class="company-directory-card" data-search="{E(c['name']+' '+c.get('sector','')+' '+c.get('summary',''))}"><div class="company-card-kicker"><span>#{int(c.get('directory_rank',i+1)):02d}</span><span>{E(c.get('sector',''))}</span></div><h2><a href="/companies/{c['slug']}/">{E(c['name'])}</a></h2><p class="company-directory-summary">{E(c.get('summary',''))}</p><div class="funding-context"><span>Latest disclosed financing</span><strong>{funding}</strong></div><div class="thesis-columns"><div><span class="thesis-label bull">Bull case</span><p>{E(c.get('bull_case','Editorial note coming soon.'))}</p></div><div><span class="thesis-label bear">Bear case</span><p>{E(c.get('bear_case','Editorial note coming soon.'))}</p></div></div>{'<ul class="company-directory-notes">'+notes+'</ul>' if notes else ''}<a class="company-profile-link" href="/companies/{c['slug']}/">View company profile →</a></article>''')
put(s.head,'<script defer src="/companies.js"></script>')
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

about=read('content/settings/about.json');s=shell('about',about['title'],about['description'],'/about/');configure_nav(s,'about');main=s.select_one('main');footer=main.select_one('footer').extract();subscribe=main.select_one('.subscribe-panel').extract();about_body=clean(about['body']);hero=about_body.select_one('.about-hero');hero.decompose() if hero else None;main.clear();main.append(about_body);main.append(subscribe);main.append(footer);write(s,'/about/')
# The editor is a separate authenticated service, not a public editing API.
s=shell('about','Edit website','Open the secure content editor.','/admin/');configure_nav(s,'');s.select_one('main').clear();put(s.select_one('main'),'<section class="about-hero"><h1>Edit your publication.</h1><p>Sign in with your GitHub account to edit articles, company profiles, images, and homepage text.</p><a class="primary-button" href="https://app.pagescms.org">Open Pages CMS ↗</a></section>');put(s.head,'<meta name="robots" content="noindex">');write(s,'/admin/')
routes=['/','/research/','/insights/','/companies/','/ipo-calendar/','/valuations/','/about/']+[a['url'] for a in ordered]+['/companies/'+c['slug']+'/' for c in companies.values()]
(OUT/'sitemap.xml').write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+E(base+r)+'</loc></url>' for r in routes)+'</urlset>')
(OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: '+base+'/sitemap.xml\n')
print(f'Built {len(articles)} published articles, {len(companies)} company profiles, and editable site pages.')
