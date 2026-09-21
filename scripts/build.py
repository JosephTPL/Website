"""Build the publication from CMS-managed content. No CMS runtime or database required."""
from pathlib import Path
from datetime import date, datetime
from urllib.parse import urlsplit, unquote
import html, json, os, re, shutil, sys
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

settings=read('content/settings/site.json');articles=records('articles');companies=records('companies')
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

def shell(kind,title,description,route,image=''):
 s=soup((ROOT/'templates'/f'{kind}.html').read_text());s.title.string=title+' | '+settings['site_name']
 s.select_one('meta[name="description"]')['content']=description
 for name,value in [('og:title',s.title.string),('og:description',description),('og:url',base+route),('og:site_name',settings['site_name'])]:s.select_one(f'meta[property="{name}"]')['content']=value
 s.select_one('link[rel="canonical"]')['href']=base+route
 for x in s.select('script[type="application/ld+json"],meta[property="og:image"],meta[property="og:image:alt"]'):x.decompose()
 if image:put(s.head,f'<meta property="og:image" content="{E(base+image if image.startswith("/") else image)}">')
 for a in s.select('a[href^="https://preipomedia.substack.com/subscribe"]'):a['href']=settings['subscribe_url']
 for panel in s.select('.subscribe-panel'):
  set_text(panel,'h2',settings['subscribe_title']);set_text(panel,'p:not(.eyebrow)',settings['subscribe_text'])
 brand=s.select_one('.brand>span:last-child');brand.clear();brand.append(settings['site_name'].upper());put(brand,'<small>'+E(settings['tagline'])+'</small>')
 if s.select_one('footer'):s.select_one('footer').clear();put(s.select_one('footer'),f'© {date.today().year} {E(settings["site_name"])} <a href="/admin/">Edit website</a>')
 return s

def write(s,route):
 p=OUT/route.strip('/')/'index.html';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(str(s))

if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir()
for f in (ROOT/'assets').iterdir():
 if f.is_file():shutil.copy2(f,OUT/f.name)
shutil.copytree(ROOT/'media',OUT/'media')
# Library and articles share the original design; only their content is rebuilt.
for view in ['library','insights']:
 route='/' if view=='library' else '/insights/'
 s=shell('home',settings[f'{view}_title'],settings[f'{view}_subtitle'],route)
 s.body['data-library-title']=settings['library_title'];s.body['data-library-subtitle']=settings['library_subtitle'];s.body['data-insights-title']=settings['insights_title'];s.body['data-insights-subtitle']=settings['insights_subtitle']
 set_text(s,'#view-title',settings[f'{view}_title']);set_text(s,'#view-subtitle',settings[f'{view}_subtitle']);set_text(s,'#about h2',settings['about_title']);set_text(s,'#about p:last-child',settings['about_text'])
 set_text(s,'.library-count strong',str(sum(a['sector']!='Insights' for a in ordered)))
 for a in s.select('[data-view]'):a['class']=['active'] if a['data-view']==view else []
 feature=s.select_one('#start-here');featured=articles.get(settings.get('featured_article'))
 if featured:
  set_text(feature,'.eyebrow',settings['featured_label']);set_text(feature,'h2',settings['featured_title']);set_text(feature,'p:not(.eyebrow)',settings['featured_text']);set_text(feature,'.feature-mark strong',featured.get('card_title') or featured['title'])
  feature.select_one('.primary-button')['href']=featured['url']+'#brief' if featured.get('brief',{}).get('thesis') else featured['url'];feature.select_one('.text-link')['href']=featured['url']
 else:feature['hidden']='';feature['data-unavailable']='true'
 if view=='insights':feature['hidden']='';s.select_one('.chips')['hidden']=''
 grid=s.select_one('#research-grid');grid.clear()
 for i,a in enumerate(ordered):
  visible=(a['sector']=='Insights')==(view=='insights');name=a.get('card_title') or a['title'];img=f'<img src="{E(a["cover_image"])}" alt="{E(a.get("cover_alt",name))}" loading="lazy" decoding="async">' if a.get('cover_image') else ''
  markup=f'''<article class="card" data-slug="{a['slug']}" data-sector="{E(a['sector'])}" data-order="{i}" data-name="{E(name)}" data-search="{E(name+' '+a['summary']+' '+a['sector'])}" {'' if visible else 'hidden'}><a class="card-cover cover-refined" href="{a['url']}" aria-label="Read {E(name)}">{img}<span class="cover-caption">{E(settings['site_name'].upper())}</span></a><div class="card-content"><span class="sector-inline">{E(a['sector'] if a['sector']!='Insights' else 'General articles')}</span><h3><a href="{a['url']}">{E(name)}</a></h3><p class="description">{E(a['summary'])}</p><div class="card-meta"><span>{date_text(a['date'])}</span><span>{a['minutes']} min</span></div><a class="read-button" href="{a['url']}">Read {'article' if a['sector']=='Insights' else 'research'} →</a><button class="card-save" type="button" data-save="{a['slug']}" aria-pressed="false">Save for later</button></div></article>'''
  put(grid,markup)
 write(s,route)

for a in ordered:
 s=shell('article',a['title'],a['summary'],a['url'],a.get('cover_image',''));s.body['data-article']=a['slug'];s.body['data-title']=a.get('card_title') or a['title'];s.body['data-sector']=a['sector']
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
 destination='/insights/' if a['sector']=='Insights' else '/'
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
 s=shell('about',company['name'],company['summary'],route,company.get('image',''));main=s.select_one('main');footer=main.select_one('footer').extract();subscribe=main.select_one('.subscribe-panel').extract();main.clear()
 put(main,f'<a class="back" href="/">← Research library</a><article class="reading-paper company-profile"><p class="overline">{E(company["sector"])} / COMPANY PROFILE</p><h1>{E(company["name"])}</h1><p class="subtitle">{E(company["summary"])}</p></article>')
 paper=main.select_one('article')
 if company.get('image'):put(paper,f'<img class="profile-image" src="{E(company["image"])}" alt="{E(company.get("image_alt",company["name"]))}" loading="lazy">')
 put(paper,'<div class="article-body">'+str(clean(company.get('overview','')))+'</div><section class="facts">'+facts(company)+'</section>')
 if company.get('report') in articles:put(paper,f'<a class="primary-button" href="{articles[company["report"]]["url"]}">Read the company breakdown →</a>')
 main.append(subscribe);main.append(footer);write(s,route)

about=read('content/settings/about.json');s=shell('about',about['title'],about['description'],'/about/');main=s.select_one('main');footer=main.select_one('footer').extract();subscribe=main.select_one('.subscribe-panel').extract();main.clear();main.append(clean(about['body']));main.append(subscribe);main.append(footer);write(s,'/about/')
# The editor is a separate authenticated service, not a public editing API.
s=shell('about','Edit website','Open the secure content editor.','/admin/');s.select_one('main').clear();put(s.select_one('main'),'<section class="about-hero"><h1>Edit your publication.</h1><p>Sign in with your GitHub account to edit articles, company profiles, images, and homepage text.</p><a class="primary-button" href="https://app.pagescms.org">Open Pages CMS ↗</a></section>');put(s.head,'<meta name="robots" content="noindex">');write(s,'/admin/')
routes=['/','/insights/','/about/']+[a['url'] for a in ordered]+['/companies/'+c['slug']+'/' for c in companies.values()]
(OUT/'sitemap.xml').write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+E(base+r)+'</loc></url>' for r in routes)+'</urlset>')
(OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: '+base+'/sitemap.xml\n')
print(f'Built {len(articles)} published articles, {len(companies)} company profiles, and editable site pages.')
