(() => {
  const grid = document.querySelector('#research-grid');
  if (!grid) return;
  const cards = [...grid.children];
  const search = document.querySelector('#search');
  const sort = document.querySelector('#sort');
  const chips = [...document.querySelectorAll('button[data-sector]')];
  const savedButton = document.querySelector('#saved-filter');
  const params = () => new URLSearchParams(location.search);
  const currentView = () => location.pathname === '/insights/' || params().get('view') === 'insights' ? 'insights' : 'library';
  let view = currentView(), sector = params().get('sector') || 'All sectors', savedOnly = params().get('saved') === '1';
  search.value = params().get('q') || '';
  if (['new','old','name'].includes(params().get('sort'))) sort.value = params().get('sort');
  if (!chips.some(c => c.dataset.sector === sector)) sector = 'All sectors';
  function syncUrl(push = false) {
    const query = new URLSearchParams();
    if (search.value.trim()) query.set('q',search.value.trim());
    if (sector !== 'All sectors' && view !== 'insights') query.set('sector',sector);
    if (sort.value !== 'new') query.set('sort',sort.value);
    if (savedOnly) query.set('saved','1');
    const url = (view === 'insights' ? '/insights/' : '/') + (query.size ? '?' + query : '');
    history[push ? 'pushState' : 'replaceState']({},'',url);
  }
  function render() {
    let visible = 0;
    const terms = search.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    for (const card of cards) {
      const matchesView = view === 'insights' ? card.dataset.sector === 'Insights' : card.dataset.sector !== 'Insights';
      const saved = window.LedgerReader?.isSaved(card.dataset.slug) || false;
      card.hidden = !((savedOnly || matchesView) && (sector === 'All sectors' || card.dataset.sector === sector) && terms.every(t => card.dataset.search.toLowerCase().includes(t)) && (!savedOnly || saved));
      if (!card.hidden) visible++;
    }
    cards.sort((a,b) => sort.value === 'name' ? a.dataset.name.localeCompare(b.dataset.name) : sort.value === 'old' ? Number(b.dataset.order)-Number(a.dataset.order) : Number(a.dataset.order)-Number(b.dataset.order)).forEach(card => grid.append(card));
    document.querySelector('#result-count').textContent = visible + ' ' + (savedOnly || view === 'insights' ? (visible === 1 ? 'article' : 'articles') : (visible === 1 ? 'report' : 'reports'));
    const empty = document.querySelector('.empty'); empty.hidden = visible > 0;
    empty.querySelector('h3').textContent = savedOnly ? 'No saved articles here yet' : 'No matching research';
    empty.querySelector('p').textContent = savedOnly ? 'Save a report or essay for later, or clear your filters to see more.' : 'Try another company, topic, or sector.';
    document.querySelector('.chips').hidden = view === 'insights' && !savedOnly;
    document.querySelector('.library-count').hidden = view === 'insights' || savedOnly;
    document.querySelector('#start-here').hidden = document.querySelector('#start-here').dataset.unavailable === 'true' || view === 'insights' || savedOnly || Boolean(search.value.trim()) || sector !== 'All sectors';
    document.querySelector('#view-title').textContent = savedOnly ? 'Your reading list.' : view === 'insights' ? document.body.dataset.insightsTitle : document.body.dataset.libraryTitle;
    document.querySelector('#list-title').textContent = savedOnly ? 'Saved for later' : view === 'insights' ? 'General articles' : 'Company research';
    document.querySelector('#view-subtitle').textContent = savedOnly ? 'Your saved reports and essays, together in one place on this browser.' : view === 'insights' ? document.body.dataset.insightsSubtitle : document.body.dataset.librarySubtitle;
    document.title = (savedOnly ? 'Saved Articles' : view === 'insights' ? 'General Articles' : 'Research Library') + ' | The Private Ledger';
    document.querySelectorAll('[data-view]').forEach(a => { a.classList.toggle('active',a.dataset.view === view); if (a.dataset.view === view) a.setAttribute('aria-current','page'); else a.removeAttribute('aria-current'); });
    chips.forEach(c => c.setAttribute('aria-pressed',String(c.dataset.sector === sector)));
    savedButton.setAttribute('aria-pressed',String(savedOnly));
  }
  search.addEventListener('input',() => { render(); syncUrl(); });
  sort.addEventListener('change',() => { render(); syncUrl(); });
  chips.forEach(c => c.addEventListener('click',() => { sector = c.dataset.sector; render(); syncUrl(); }));
  savedButton.addEventListener('click',() => { savedOnly = !savedOnly; sector = 'All sectors'; render(); syncUrl(); });
  document.querySelectorAll('[data-view]').forEach(a => a.addEventListener('click',event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault(); view = a.dataset.view; sector = 'All sectors'; savedOnly = false; search.value = ''; syncUrl(true); render();
  }));
  window.addEventListener('popstate',() => { view=currentView(); sector=params().get('sector') || 'All sectors'; search.value=params().get('q') || ''; savedOnly=params().get('saved') === '1'; sort.value=params().get('sort') || 'new'; render(); });
  document.querySelector('#reset').addEventListener('click',() => { sector='All sectors';search.value='';savedOnly=false;render();syncUrl();search.focus(); });
  document.addEventListener('keydown',event => { if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !document.activeElement.isContentEditable && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) {event.preventDefault();search.focus();} });
  document.addEventListener('ledger:state',render);
  render();
})();
