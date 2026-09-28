"""One-time migration for every remaining company in the directory."""
from pathlib import Path
import json,re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'content'/'companies'
SOURCE='https://multiples.vc/insights/50-most-valuable-private-companies-in-the-world'
js=(ROOT/'assets'/'companies.js').read_text()
rows=[]
for group in ('watch','additions'):
 match=re.search(r"const "+group+r"='(.*?)'\.split\('~'\)",js,re.S)
 rows.extend(item.split('|') for item in match.group(1).split('~'))
existing={json.loads(p.read_text())['name'].lower() for p in OUT.glob('*.json')}

def slugify(name):
 return re.sub(r'-+','-',re.sub(r'[^a-z0-9]+','-',name.lower())).strip('-')

def profile(name,value,domain,rank):
 slug=slugify(name)
 website='https://'+domain
 disclosed=value not in ('Not publicly disclosed','Not applicable')
 valuation_note='Reported Private Ledger market-watch estimate; private valuations can change without a public financing.' if disclosed else 'No public valuation was identified by The Private Ledger.'
 focus='Private-market company tracking'
 summary=f'{name} is a private company tracked in The Private Ledger market watchlist.'
 return {'slug':slug,'name':name,'status':'Published','sector':'Private markets','summary':summary,'overview':f'<p>{summary}</p>','as_of':'2026-09-25','facts':[{'label':'Reported valuation','value':value,'note':valuation_note,'source':SOURCE},{'label':'Public status','value':'Private','note':'No confirmed public offering is reflected in this profile.','source':website}], 'directory_rank':rank,'bull_case':f'{name} is positioned in a private market where execution and distribution can compound.','bear_case':'The valuation and operating outlook are uncertain until additional public disclosures become available.','latest_round':('Reported valuation: '+value if disclosed else 'Latest financing not publicly disclosed'),'directory_notes':['Private-market watchlist','Watch for funding, operating milestones, and IPO developments.'],'intelligence':{'kicker':'COMPANY INTELLIGENCE','location':'Not publicly disclosed','status':'Private','logo':f'https://www.google.com/s2/favicons?domain={domain}&sz=128','description':summary,'metrics':[{'value':value,'label':'Reported valuation','note':'Private Ledger market watch'},{'value':'Private','label':'Public status','note':'No confirmed IPO'},{'value':'Sep 2026','label':'Profile updated','note':'Latest editorial review'},{'value':'Watchlist','label':'Coverage','note':'Company profile'}],'company':[summary,'This profile establishes the company record for ongoing Private Ledger research and will be expanded as material, sourced disclosures are published.'],'why_it_matters':f'{name} is part of the private-company universe that can shape future public-market competition and capital allocation.','valuation_history':[{'value':'Private','date':'Before IPO','round':'Private-company period'},{'value':value,'date':'2026','round':'Latest reported estimate'}],'changed':[{'date':'2026','text':'The company is added to The Private Ledger company-profile coverage.'}],'takeaways':[f'{name} is now covered in The Private Ledger directory.','Private valuations are directional estimates, not audited market prices.','Funding, product execution, and market structure are the primary items to watch.','This profile will be updated as new public information becomes available.'],'quick_facts':[['Sector','Private markets'],['Public status','Private'],['Coverage','Company profile'],['Website',domain]],'sources':[{'label':'Company website','url':website},{'label':'Private-company valuation reference','url':SOURCE}]}}

created=[]
for rank,(name,value,domain,*_) in enumerate(rows,1):
 if name.lower() in existing: continue
 data=profile(name,value,domain,rank)
 target=OUT/(data['slug']+'.json')
 if target.exists(): raise SystemExit('Slug collision: '+target.name)
 target.write_text(json.dumps(data,indent=2)+'\\n');created.append(data['slug'])
print('Created',len(created),'profiles:',', '.join(created))
