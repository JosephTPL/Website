(()=>{
  const grid=document.querySelector('#company-directory-grid'),search=document.querySelector('#company-search'),count=document.querySelector('#company-result-count');
  if(!grid||!search||!count)return;
  const companies=/* PROFILE_DIRECTORY */;
  const darkLogoNames=new Set(['long lake','neros','revel','ricursive']);
  let activeCategory='all',activeValuation='all';
  const controls=document.createElement('div');controls.className='ledger-filters';controls.setAttribute('aria-label','Filter companies');
  const makeButton=(value,label)=>{const button=document.createElement('button');button.type='button';button.className='ledger-filter';button.dataset.value=value;button.setAttribute('aria-pressed',String(value==='all'));button.textContent=label;controls.append(button)};
  // Keep the public directory deliberately editorial: these are reader-facing lenses,
  // not a mirror of every internal data taxonomy.
  [['all','All'],['ai','AI'],['fintech','Fintech'],['defense','Defense'],['hardware','Robotics, hardware & semiconductors'],['social','Social'],['ownership','Acquired & subsidiaries'],['former','Former private companies']].forEach(([value,label])=>makeButton(value,label));
  const valuationLabel=document.createElement('label'),valuation=document.createElement('select');valuationLabel.className='ledger-valuation-filter';valuationLabel.textContent='Valuation ';
  [['all','Any value'],['100','$100B+'],['10','$10B–$99.9B'],['1','$1B–$9.9B'],['under-1','Under $1B'],['undisclosed','No disclosed valuation']].forEach(([value,label])=>{const option=document.createElement('option');option.value=value;option.textContent=label;valuation.append(option)});
  valuation.setAttribute('aria-label','Filter by reported valuation');valuationLabel.append(valuation);controls.append(valuationLabel);document.querySelector('.directory-tools').after(controls);
  const relationship=company=>company.status==='subsidiary'?`Subsidiary of ${company.parent}`:company.status==='acquired'?`Acquired by ${company.parent}${company.deal_value?` · ${company.deal_value}`:''}`:company.status==='acquisition_pending'?`Being acquired by ${company.parent}${company.deal_value?` · ${company.deal_value}`:''}`:company.status==='public'?'Former private company · Now public':company.sector;
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
    const haystack=[company.name,company.sector,company.parent,company.website,company.status].join(' ').toLowerCase();
    return (!search.value.trim()||haystack.includes(search.value.trim().toLowerCase()))&&categoryMatches(company)&&matchesValuation(company);
  };
  const card=company=>{
    const article=document.createElement('article'),link=document.createElement('a'),image=document.createElement('img'),body=document.createElement('div'),title=document.createElement('h2'),meta=document.createElement('p'),value=document.createElement('strong');
    article.className='ledger-card';link.className='ledger-card-link';link.href=`/companies/${company.slug}/`;image.src=company.logo||`https://www.google.com/s2/favicons?domain=${encodeURIComponent(company.website)}&sz=128`;image.alt=`${company.name} logo`;if(darkLogoNames.has(company.name.toLowerCase()))image.className='dark-logo';title.textContent=company.name;meta.className='ledger-source';meta.textContent=relationship(company);value.textContent=company.valuation===null?'No disclosed valuation':`Reported valuation · ${company.valuation_label}`;body.append(title,meta,value);link.append(image,body);article.append(link);return article;
  };
  const render=()=>{
    grid.replaceChildren();const shown=companies.filter(matches).sort((a,b)=>(b.valuation??-1)-(a.valuation??-1)||a.name.localeCompare(b.name));
    const groups=[['Private companies by reported valuation',shown.filter(company=>!['public','acquired'].includes(company.status))],['Former private companies',shown.filter(company=>['public','acquired'].includes(company.status))]];
    groups.forEach(([label,items])=>{if(!items.length)return;if(label!=='Private companies by reported valuation'){const heading=document.createElement('h2');heading.className='ledger-label';heading.textContent=label;grid.append(heading)}items.forEach(company=>grid.append(card(company)))});
    count.textContent=`${shown.length} companies`;
  };
  controls.addEventListener('click',event=>{const button=event.target.closest('.ledger-filter');if(!button)return;activeCategory=button.dataset.value;controls.querySelectorAll('.ledger-filter').forEach(item=>item.setAttribute('aria-pressed',String(item.dataset.value===activeCategory)));render()});
  search.addEventListener('input',render);valuation.addEventListener('change',()=>{activeValuation=valuation.value;render()});render();
})();
