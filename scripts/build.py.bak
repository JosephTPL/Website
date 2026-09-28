"""Build the publication from CMS-managed content. No CMS runtime or database required."""
from pathlib import Path
from datetime import date, datetime
from urllib.parse import urlsplit, unquote
import calendar, html, json, os, re, shutil, sys
from bs4 import BeautifulSoup
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
  if top_subscribe:top_subscribe.insert_before(soup(f'<a class="top-link top-discord" href="{E(settings["discord_url"])}" rel="noopener">Join Discord <span aria-hidden="true">↗</span></a>'))
 for panel in s.select('.subscribe-panel'):
  set_text(panel,'h2',settings['subscribe_title']);set_text(panel,'p:not(.eyebrow)',settings['subscribe_text'])
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
 for link in nav.select('a'):
  link.attrs.pop('aria-current',None)
  link['class']=['active'] if link.get('data-view')==active else []

def weekly_markup():
 items=''.join(f'''<article class="weekly-item"><div><span class="weekly-number">{i:02d}</span><span class="weekly-tag">{E(item['tag'])}</span></div><h2>{E(item['company'])}</h2><p>{E(item['text'])}</p><a href="{E(item['source'])}" rel="noopener">Source ↗</a></article>''' for i,item in enumerate(weekly['items'],1))
 return f'''<section class="weekly-brief" aria-labelledby="weekly-title"><header class="weekly-head"><div><p class="overline">THE PRIVATE LEDGER / WEEKLY BRIEF</p><h1 id="weekly-title">{E(weekly['title'])}</h1><p class="subtitle">{E(weekly['intro'])}</p></div><p class="weekly-date">Last week<br/><strong>{E(weekly['period'])}</strong><span>Next update: {E(weekly['next_update'])}</span></p></header><div class="weekly-grid">{items}</div><div class="weekly-footer"><span>Updated every Sunday.</span><a class="text-link" href="/research/">Explore company research →</a></div></section>'''

def ipo_markup():
 """A true month view; undated candidates stay out of arbitrary day cells."""
 month=ipo_calendar['calendar']['month'];year=int(ipo_calendar['calendar']['year']);month_number=int(ipo_calendar['calendar']['month_number'])
 items=[item for period in ipo_calendar['periods'] for item in period['items']]
 events={}
 for item in items:
  if item.get('date'):events.setdefault(str(item['date']),[]).append(item)
 earnings={}
 for item in ipo_calendar.get('earnings',[]):earnings.setdefault(str(item['date']),[]).append(item)
 def event_markup(item):
  return f'<a class="ipo-event" href="{E(item["source"])}"><strong>{E(item["company"])}</strong><span>{E(item["status"])}</span></a>'
 def earnings_markup(item):
  label=f'Open The Ledger view on {item["company"]} earnings'
  return f'<button class="ipo-event earnings-event" type="button" aria-label="{E(label)}" data-company="{E(item["company"])}" data-ticker="{E(item["ticker"])}" data-timing="{E(item["timing"])}" data-confidence="{E(item["confidence"])}" data-impact="{E(item["impact"])}" data-source="{E(item["source"])}"><strong>{E(item["ticker"])}</strong><span>{E(item["timing"])}</span></button>'
 weeks=[]
 for week in calendar.monthcalendar(year,month_number):
  cells=[]
  for day in week:
   if day:
    entries=''.join(event_markup(item) for item in events.get(str(day),[]))+''.join(earnings_markup(item) for item in earnings.get(str(day),[]))
    cells.append(f'<div class="ipo-day"><span>{day}</span>{entries}</div>')
   else:cells.append('<div class="ipo-day is-outside" aria-hidden="true"></div>')
  weeks.append('<div class="ipo-week">'+''.join(cells)+'</div>')
 tbd=''.join(f'''<article class="ipo-tbd"><div><span class="ipo-status {E(item['status'].lower().replace(' ','-'))}">{E(item['status'])}</span><span class="ipo-valuation">{E(item['valuation'])}</span></div><h2>{E(item['company'])}</h2><p>{E(item['note'])}</p><a href="{E(item['source'])}" rel="noopener">Source ↗</a></article>''' for item in items)
 return f'''<section class="ipo-calendar" aria-labelledby="ipo-title"><header class="ipo-head"><div><p class="overline">THE PRIVATE LEDGER / IPO CALENDAR</p><h1 id="ipo-title">{E(ipo_calendar['title'])}</h1><p class="subtitle">{E(ipo_calendar['intro'])}</p></div><p class="ipo-as-of">As of<br/><strong>{E(ipo_calendar['as_of'])}</strong></p></header><div class="ipo-note"><strong>How to read this.</strong> {E(ipo_calendar['disclaimer'])}</div><section class="ipo-month" aria-labelledby="ipo-month-title"><header><div><p class="overline">UPCOMING MONTH</p><h2 id="ipo-month-title">{E(month)}</h2></div><p><strong>Public earnings watch.</strong> Hover a marker for The Ledger's private-market read-through.</p></header><div class="ipo-weekdays"><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span></div><div class="ipo-month-grid">{''.join(weeks)}</div><p class="ipo-empty"><strong>No confirmed $5B+ IPO dates are on the public calendar for {E(month)}.</strong> Public-company earnings markers use confirmed dates where disclosed and labelled estimates otherwise.</p></section><section class="ipo-tbd-section" aria-labelledby="ipo-tbd-title"><header><p class="overline">DATE TO BE ANNOUNCED</p><h2 id="ipo-tbd-title">The $5B+ IPO watchlist.</h2><p>Private-market giants with a reported filing, window, or credible path to market, but no confirmed day to put on the calendar yet.</p></header><div class="ipo-tbd-grid">{tbd}</div></section></section>'''

if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir()
for f in (ROOT/'assets').iterdir():
 if f.is_file():shutil.copy2(f,OUT/f.name)
 elif f.is_dir():shutil.copytree(f,OUT/f.name)
shutil.copytree(ROOT/'media',OUT/'media')
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
 kind='General articles' if a['sector']=='Insights' else 'Deep dive'
 markup=f'''<article class="card" data-slug="{a['slug']}" data-sector="{E(a['sector'])}" data-kind="{E(kind)}" data-order="{i}" data-name="{E(name)}" data-search="{E(name+' '+a['summary']+' '+a['sector'])}"><a class="card-cover cover-refined" href="{a['url']}" aria-label="Read {E(name)}">{img}<span class="cover-caption">{E(settings['site_name'].upper())}</span></a><div class="card-content"><span class="sector-inline">{E(kind if kind=='General articles' else a['sector'])}</span><h3><a href="{a['url']}">{E(name)}</a></h3><p class="description">{E(a['summary'])}</p><div class="card-meta"><span>{date_text(a['date'])}</span><span>{a['minutes']} min</span></div><a class="read-button" href="{a['url']}">Read {'article' if kind=='General articles' else 'research'} →</a><button class="card-save" type="button" data-save="{a['slug']}" aria-pressed="false">Save for later</button></div></article>'''
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
 body=s.select_one('.article-body');body.clear();body.append(clean(a['body']))
 mapping={r['title']:r['id'] for r in a.get('section_anchors',[])};used=set(mapping.values());toc=[]
 for i,h in enumerate(body.select('h2,h3')):
  title=h.get_text(' ',strip=True);anchor=mapping.get(title) or h.get('id')
  if not anchor:
   anchor='section-'+str(i)
   while anchor in used:anchor+='-new'
  used.add(anchor);h['id']=anchor;toc.append((anchor,title));put(h,f'<button class="section-copy" type="button" data-copy-section="{E(anchor)}" aria-label="Copy link to {E(title)}">Link</button>')
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
  body.insert_before(soup(f'''<section class="brief" id="brief" aria-labelledby="brief-title"><div class="brief-heading"><p class="eyebrow">THE ESSENTIALS</p><span>ABOUT 1 MINUTE</span></div><h2 id="brief-title">The 60-second brief</h2><p class="brief-thesis">{E(brief['thesis'])}</p><ul>{''.join('<li>'+E(t)+'</li>' for t in brief.get('takeaways',[]))}</ul><div class="brief-bottom"><div><h3>The risk</h3><p>{E(brief.get('risk',''))}</p></div><div><h3>What to watch</h3><p>{E(brief.get('watch',''))}</p></div></div><p class="snapshot-note">A summary of the article published {date_text(a['date'])}. Figures and outlooks reflect that publication context.</p><a class="text-link" href="#article-body">Read the report below ↓</a></section>'''))
 company=companies.get(a.get('company',''))
 if company:
  body.insert_before(soup(f'<details class="facts" id="company-facts"><summary><span>Company snapshot<small>{E(company["name"])} · {date_text(company["as_of"])}</small></span><span class="details-icon" aria-hidden="true">＋</span></summary>{facts(company)}<p class="profile-link"><a href="/companies/{company["slug"]}/">View company profile →</a></p></details>'))
 if a.get('excerpt'):body.insert_before(soup(f'<div class="excerpt-notice"><strong>About this edition</strong><p>This is an excerpt. The remaining sections and complete references are on Substack.</p><a href="{E(a["original_url"])}">Continue to the original article ↗</a></div>'))
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

about=read('content/settings/about.json');s=shell('about',about['title'],about['description'],'/about/');configure_nav(s,'about');main=s.select_one('main');footer=main.select_one('footer').extract();subscribe=main.select_one('.subscribe-panel').extract();about_body=clean(about['body']);hero=about_body.select_one('.about-hero');hero.decompose() if hero else None;main.clear();main.append(about_body);main.append(subscribe);main.append(footer);write(s,'/about/')
# The editor is a separate authenticated service, not a public editing API.
s=shell('about','Edit website','Open the secure content editor.','/admin/');configure_nav(s,'');s.select_one('main').clear();put(s.select_one('main'),'<section class="about-hero"><h1>Edit your publication.</h1><p>Sign in with your GitHub account to edit articles, company profiles, images, and homepage text.</p><a class="primary-button" href="https://app.pagescms.org">Open Pages CMS ↗</a></section>');put(s.head,'<meta name="robots" content="noindex">');write(s,'/admin/')
routes=['/','/research/','/insights/','/companies/','/ipo-calendar/','/about/']+[a['url'] for a in ordered]+['/companies/'+c['slug']+'/' for c in companies.values()]
(OUT/'sitemap.xml').write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+E(base+r)+'</loc></url>' for r in routes)+'</urlset>')
(OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: '+base+'/sitemap.xml\n')
print(f'Built {len(articles)} published articles, {len(companies)} company profiles, and editable site pages.')
