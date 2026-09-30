(()=>{
  const root=document.querySelector('#spv-tracker');if(!root)return;
  const search=root.querySelector('#spv-search'),recent=root.querySelector('#spv-recent'),sort=root.querySelector('#spv-sort'),count=root.querySelector('#spv-count'),cards=[...root.querySelectorAll('.spv-card')],container=root.querySelector('.spv-cards');let onlyRecent=false;
  const render=()=>{
    const term=search.value.trim().toLowerCase();
    const visible=cards.filter(card=>!term||card.dataset.search.toLowerCase().includes(term));
    const sorted=[...visible].sort((a,b)=>sort.value==='name'?a.dataset.name.localeCompare(b.dataset.name):sort.value==='newest'?b.dataset.newest.localeCompare(a.dataset.newest):Number(b.dataset[sort.value])-Number(a.dataset[sort.value]));
    cards.forEach(card=>{
      const rows=[...card.querySelectorAll('tbody tr')];
      const shown=rows.filter(row=>{row.hidden=onlyRecent&&!row.matches('[data-recent="true"]');return !row.hidden});
      card.hidden=!visible.includes(card)||(onlyRecent&&!shown.length);
      card.querySelector('summary').textContent=`Show ${shown.length} vehicles`;
    });
    sorted.forEach(card=>container.append(card));count.textContent=`${sorted.filter(card=>!card.hidden).length} of ${cards.length} companies`;
  };
  recent.addEventListener('click',()=>{onlyRecent=!onlyRecent;recent.setAttribute('aria-pressed',String(onlyRecent));render()});search.addEventListener('input',render);sort.addEventListener('change',render);render();
})();
