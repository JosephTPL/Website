(()=>{
  const grid=document.querySelector('#company-directory-grid'),search=document.querySelector('#company-search'),count=document.querySelector('#company-result-count');
  if(!grid||!search||!count)return;
  const companies=/* PROFILE_DIRECTORY */;
  let activeCategory='all',activeValuation='all';
  const controls=document.createElement('div');controls.className='ledger-filters';controls.setAttribute('aria-label','Filter companies');
  const makeButton=(value,label)=>{const button=document.createElement('button');button.type='button';button.className='ledger-filter';button.dataset.value=value;button.setAttribute('aria-pressed',String(value==='all'));button.textContent=label;controls.append(button)};
  // Keep the public directory deliberately editorial: these are reader-facing lenses,
  // not a mirror of every internal data taxonomy.
  [['all','All'],['ai','AI'],['fintech','Fintech'],['defense','Defense'],['hardware','Robotics, hardware & semiconductors'],['social','Social'],['ownership','Acquired & subsidiaries'],['former','Former private companies']].forEach(([value,label])=>makeButton(value,label));
  const valuationLabel=document.createElement('label'),valuation=document.createElement('select');valuationLabel.className='ledger-valuation-filter';valuationLabel.textContent='Valuation ';
  [['all','Any value'],['100','$100B+'],['10','$10B–$99.9B'],['1','$1B–$9.9B'],['under-1','Under $1B'],['undisclosed','No disclosed valuation']].forEach(([value,label])=>{const option=document.createElement('option');option.value=value;option.textContent=label;valuation.append(option)});
  valuation.setAttribute('aria-label','Filter by reported valuation');valuationLabel.append(valuation);controls.append(valuationLabel);document.querySelector('.directory-tools').after(controls);
  const matchesValuation=company=>activeValuation==='all'||(activeValuation==='undisclosed'?company.valuation===null:activeValuation==='under-1'?company.valuation!==null&&company.valuation<1:company.valuation!==null&&company.valuation>=Number(activeValuation)&&(activeValuation==='100'||company.valuation<Number(activeValuation)*10));
  const categoryMatches=company=>{
    if(activeCategory==='all')return true;
    if(activeCategory==='former')return ['public','acquired'].includes(company.status);
    if(activeCategory==='ownership')return ['acquired','acquisition_pending','subsidiary'].includes(company.status);
    const sectors={
      ai:['AI & Machine Learning','Data, Cloud & Developer Tools'],
      fintech:['Financial Services & Digital Assets'],
      defense:['Defense, Aerospace & Space'],
      hardware:['Hardware, Robotics & Semiconductors'],
      social:['Consumer, Commerce & Media']
    };
    return sectors[activeCategory]?.includes(company.sector)??false;
  };
  const matches=company=>{
    const haystack=[company.name,company.aliases?.join(' '),company.sector,company.summary,company.parent,company.website,company.status].join(' ').toLowerCase();
    return (!search.value.trim()||haystack.includes(search.value.trim().toLowerCase()))&&categoryMatches(company)&&matchesValuation(company);
  };
  const text=(value,fallback='')=>value||fallback;
  const card=company=>{
    const article=document.createElement('article'),kicker=document.createElement('div'),rank=document.createElement('span'),sector=document.createElement('span'),title=document.createElement('h2'),titleLink=document.createElement('a'),summary=document.createElement('p'),funding=document.createElement('div'),fundingLabel=document.createElement('span'),fundingValue=document.createElement('strong'),theses=document.createElement('div'),profileLink=document.createElement('a');
    article.className='company-directory-card';article.dataset.search=[company.name,company.aliases?.join(' '),company.sector,company.summary].join(' ');
    kicker.className='company-card-kicker';rank.textContent=`#${String(company.rank).padStart(2,'0')}`;sector.textContent=company.sector;kicker.append(rank,sector);
    titleLink.href=`/companies/${company.slug}/`;titleLink.textContent=company.name;title.append(titleLink);
    summary.className='company-directory-summary';summary.textContent=company.summary;
    funding.className='funding-context';fundingLabel.textContent='Latest disclosed financing';fundingValue.textContent=text(company.latest_round,'Not yet added');funding.append(fundingLabel,fundingValue);
    theses.className='thesis-columns';[['bull','Bull case',text(company.bull_case,'Editorial note coming soon.')],['bear','Bear case',text(company.bear_case,'Editorial note coming soon.')]].forEach(([kind,label,copy])=>{const column=document.createElement('div'),heading=document.createElement('span'),paragraph=document.createElement('p');heading.className=`thesis-label ${kind}`;heading.textContent=label;paragraph.textContent=copy;column.append(heading,paragraph);theses.append(column)});
    article.append(kicker,title,summary,funding,theses);
    if(company.directory_notes?.length){const notes=document.createElement('ul');notes.className='company-directory-notes';company.directory_notes.forEach(note=>{const item=document.createElement('li');item.textContent=note;notes.append(item)});article.append(notes)}
    profileLink.className='company-profile-link';profileLink.href=`/companies/${company.slug}/`;profileLink.textContent='View company profile →';article.append(profileLink);
    return article;
  };
  const render=()=>{
    grid.replaceChildren();const shown=companies.filter(matches).sort((a,b)=>(b.valuation??-1)-(a.valuation??-1)||a.name.localeCompare(b.name));
    shown.forEach(company=>grid.append(card(company)));
    count.textContent=`${shown.length} companies`;
  };
  controls.addEventListener('click',event=>{const button=event.target.closest('.ledger-filter');if(!button)return;activeCategory=button.dataset.value;controls.querySelectorAll('.ledger-filter').forEach(item=>item.setAttribute('aria-pressed',String(item.dataset.value===activeCategory)));render()});
  search.addEventListener('input',render);valuation.addEventListener('change',()=>{activeValuation=valuation.value;render()});render();
})();
