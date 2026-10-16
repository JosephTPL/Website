(() => {
  const toggleButtons = [...document.querySelectorAll('.view-toggle')];
  const viewContents = [...document.querySelectorAll('.ipo-view-content')];
  if (!toggleButtons.length) return;
  const setView = view => {
    toggleButtons.forEach(button => {
      const active = button.dataset.view === view;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    viewContents.forEach(content => content.hidden = content.dataset.view !== view);
    try { localStorage.setItem('ipo-calendar-view', view); } catch { /* Optional preference only. */ }
  };
  let saved = 'calendar';
  try { saved = localStorage.getItem('ipo-calendar-view') || saved; } catch { /* Optional preference only. */ }
  setView(saved);
  toggleButtons.forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));
})();

(() => {
  const earningsEvents = [...document.querySelectorAll('.earnings-event')];
  const earningsMonth = document.querySelector('.ipo-month');
  if (earningsEvents.length && earningsMonth) {
    const panel = document.createElement('aside');
    panel.className = 'earnings-detail';
    panel.setAttribute('aria-live', 'polite');
    panel.innerHTML = '<p class="overline">PRIVATE-MARKET READ-THROUGH</p><h3>Select an earnings marker.</h3><p>Choose a public company on the calendar to see why its results matter for private markets.</p>';
    earningsMonth.querySelector('.ipo-month-grid').insertAdjacentElement('afterend', panel);
    const select = button => {
      earningsEvents.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      panel.innerHTML = `<p class="overline">${button.dataset.ticker} / ${button.dataset.confidence}</p><h3>${button.dataset.company}</h3><p class="earnings-timing">${button.dataset.timing}</p><p>${button.dataset.impact}</p><a href="${button.dataset.source}" rel="noopener">Earnings source ↗</a>`;
    };
    document.querySelector('#ipo-title') && (document.querySelector('#ipo-title').textContent = 'The IPO calendar');
    if (document.title.startsWith('The $5B+ IPO calendar.')) document.title = 'The IPO calendar | The Private Ledger';
    earningsEvents.forEach(button => button.addEventListener('click', () => select(button)));
  }
})();

(() => {
  const chart = document.querySelector('.weekly-chart-plot');
  const tooltip = chart?.querySelector('.weekly-chart-tooltip');
  if (!chart || !tooltip) return;
  const show = event => {
    const point = event.currentTarget;
    tooltip.innerHTML = `<strong>${point.dataset.value}</strong><span>${point.dataset.date}</span><b>${point.dataset.round || 'Reported valuation event'}</b>`;
    tooltip.hidden = false;
    const plot = chart.getBoundingClientRect();
    const box = point.getBoundingClientRect();
    tooltip.style.left = `${Math.max(8, Math.min(chart.clientWidth - tooltip.offsetWidth - 8, box.left - plot.left + 12))}px`;
    tooltip.style.top = `${Math.max(8, box.top - plot.top - tooltip.offsetHeight - 10)}px`;
  };
  const hide = () => { tooltip.hidden = true; };
  chart.querySelectorAll('.weekly-chart-point').forEach(point => {
    point.addEventListener('pointerenter', show);
    point.addEventListener('pointerleave', hide);
    point.addEventListener('click', show);
    point.addEventListener('focus', show);
    point.addEventListener('blur', hide);
  });
})();

(() => {
  const sidebar = document.querySelector('.sidebar');
  const topbar = document.querySelector('.topbar');
  if (sidebar && topbar) {
    sidebar.id = 'site-navigation';
    const menuButton = document.createElement('button');
    menuButton.className = 'menu-toggle';
    menuButton.type = 'button';
    menuButton.setAttribute('aria-controls', sidebar.id);
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', 'Open navigation menu');
    menuButton.innerHTML = '<span></span><span></span><span></span>';
    const closeMenu = () => {
      document.body.classList.remove('menu-open');
      menuButton.setAttribute('aria-expanded', 'false');
      menuButton.setAttribute('aria-label', 'Open navigation menu');
    };
    menuButton.addEventListener('click', () => {
      const open = !document.body.classList.contains('menu-open');
      document.body.classList.toggle('menu-open', open);
      menuButton.setAttribute('aria-expanded', String(open));
      menuButton.setAttribute('aria-label', open ? 'Close navigation menu' : 'Open navigation menu');
    });
    sidebar.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
    document.addEventListener('keydown', event => { if (event.key === 'Escape') closeMenu(); });
    window.matchMedia('(min-width:701px)').addEventListener('change', event => { if (event.matches) closeMenu(); });
    topbar.append(menuButton);
    document.documentElement.classList.add('menu-ready');
  }
})();

(() => {
  const key = 'private-ledger-reader-v1';
  let state = {saved: [], progress: {}};
  let available = true;
  try {
    const stored = JSON.parse(localStorage.getItem(key) || '{}');
    if (Array.isArray(stored.saved)) state.saved = stored.saved.filter(x => typeof x === 'string');
    if (stored.progress && typeof stored.progress === 'object' && !Array.isArray(stored.progress)) state.progress = stored.progress;
  } catch { available = false; }
  let messageTimer;
  function announce(message) {
    const region = document.querySelector('#reader-announcement');
    if (!region) return;
    region.textContent = message;
    region.classList.add('visible');
    clearTimeout(messageTimer);
    messageTimer = setTimeout(() => region.classList.remove('visible'), 5000);
  }
  function persist() {
    try { localStorage.setItem(key, JSON.stringify(state)); available = true; return true; }
    catch { available = false; return false; }
  }
  function refresh() {
    document.querySelectorAll('[data-save]').forEach(button => {
      const saved = state.saved.includes(button.dataset.save);
      button.setAttribute('aria-pressed', String(saved));
      button.textContent = saved ? 'Saved ✓' : 'Save for later';
      const name = button.closest('.card')?.dataset.name || document.body.dataset.title || 'article';
      button.setAttribute('aria-label', saved ? `Remove ${name} from saved articles` : `Save ${name} for later`);
    });
    const count = document.querySelector('#saved-count');
    if (count) count.textContent = state.saved.length;
    const section = document.querySelector('#continue-reading');
    if (section) {
      const recent = Object.entries(state.progress).filter(([slug,p]) => p && p.percent > 2 && p.percent < 98 && /^[a-z0-9-]+$/.test(slug))
        .sort((a,b) => b[1].updated - a[1].updated)[0];
      section.hidden = !recent;
      if (recent) {
        document.querySelector('#continue-title').textContent = `${recent[1].title || 'Your article'} · ${recent[1].percent}% read`;
        document.querySelector('#continue-link').href = `/articles/${recent[0]}/?resume=1`;
      }
    }
    document.dispatchEvent(new Event('ledger:state'));
  }
  window.LedgerReader = {
    isSaved: slug => state.saved.includes(slug),
    progress: slug => state.progress[slug],
    saveProgress(slug, value) { state.progress[slug] = value; persist(); },
    announce
  };
  document.querySelectorAll('[data-save]').forEach(button => button.addEventListener('click', () => {
    const slug = button.dataset.save;
    const wasSaved = state.saved.includes(slug);
    state.saved = wasSaved ? state.saved.filter(item => item !== slug) : [...state.saved, slug];
    const stored = persist();
    refresh();
    announce(stored ? (wasSaved ? 'Removed from saved articles.' : 'Saved for later on this browser.') : 'Browser storage is unavailable. This change lasts only until you leave the page.');
  }));
  async function copyLink(url) {
    try { await navigator.clipboard.writeText(url); announce('Link copied.'); }
    catch {
      const dialog = document.querySelector('#copy-dialog');
      const input = document.querySelector('#copy-value');
      input.value = url; dialog.showModal(); input.focus(); input.select();
    }
  }
  document.querySelector('[data-copy-article]')?.addEventListener('click', () => copyLink(location.origin + location.pathname));
  document.querySelectorAll('[data-copy-section]').forEach(button => button.addEventListener('click', () => copyLink(location.origin + location.pathname + '#' + button.dataset.copySection)));
  const printDocument = () => {
    const opened = [...document.querySelectorAll('details')].map(detail => [detail, detail.open]);
    document.querySelectorAll('details').forEach(detail => detail.open = true);
    const restore = () => {
      opened.forEach(([detail, open]) => detail.open = open);
      window.removeEventListener('afterprint', restore);
    };
    window.addEventListener('afterprint', restore);
    window.print();
  };
  const printCompanyProfile = () => {
    const profile = document.querySelector('.company-profile, .intelligence-profile');
    if (!profile) {
      printDocument();
      return;
    }
    const printStyle = document.createElement('style');
    printStyle.media = 'print';
    printStyle.textContent = `
      @page { size: A4; margin: 15mm 16mm 18mm; }
      html, body { background: #fff !important; color: #17222d !important; font: 10.5pt/1.52 Georgia, serif !important; }
      .topbar, .sidebar, .skip, .back, .subscribe-panel, footer, .reader-announcement, dialog, .company-profile-actions { display: none !important; }
      main { display: block !important; max-width: none !important; margin: 0 !important; padding: 0 !important; }
      main > :not(.company-profile):not(.intelligence-profile) { display: none !important; }
      .company-profile, .intelligence-profile { display: block !important; max-width: none !important; margin: 0 !important; padding: 0 !important; border: 0 !important; background: #fff !important; box-shadow: none !important; }
      .company-profile::before, .intelligence-profile::before { content: 'THE PRIVATE LEDGER  /  COMPANY BRIEF'; display: block; margin: 0 0 20pt !important; padding: 0 0 8pt !important; border-bottom: 1px solid #b79457 !important; color: #71562d !important; font: 700 8pt/1 Arial, sans-serif !important; letter-spacing: .16em !important; }
      .company-profile h1, .intelligence-header h1 { margin: 0 0 7pt !important; color: #10283a !important; font: 500 28pt/1.02 Georgia, serif !important; }
      .company-profile .subtitle, .intelligence-description { max-width: none !important; margin: 0 0 16pt !important; color: #4d5f69 !important; font: 13pt/1.42 Georgia, serif !important; }
      .profile-image { max-height: 105mm !important; margin: 12pt auto 20pt !important; object-fit: contain !important; break-inside: avoid; }
      .article-body, .intelligence-main { max-width: none !important; color: #17222d !important; font-size: 10.5pt !important; line-height: 1.58 !important; }
      .article-body p, .intelligence-content p { margin: 0 0 10pt !important; orphans: 3; widows: 3; }
      .article-body h2, .article-body h3, .intelligence-content h2 { margin: 22pt 0 8pt !important; color: #10283a !important; font-family: Georgia, serif !important; break-after: avoid; }
      .article-body h2 + p, .article-body h3 + p, .intelligence-content h2 + p { margin-top: 0 !important; }
      .article-body ul, .article-body ol, .intelligence-content ul, .intelligence-content ol { margin: 8pt 0 14pt !important; padding-left: 19pt !important; }
      .article-body li, .intelligence-content li { margin: 0 0 5pt !important; }
      .facts, .intelligence-metrics, .intelligence-main > section, .intelligence-aside > section, .valuation-history { break-inside: avoid; }
      .facts { display: block !important; margin: 22pt 0 0 !important; border: 1px solid #d8d1c4 !important; background: #faf9f5 !important; }
      .facts .facts-inner { display: block !important; padding: 14pt 15pt !important; }
      .facts .snapshot-note { margin: 0 0 12pt !important; }
      .facts-grid { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 10pt 18pt !important; }
      .facts-grid > div { border: 0 !important; padding: 0 !important; }
      .intelligence-header, .intelligence-content { display: block !important; }
      .intelligence-header { padding: 0 !important; border: 0 !important; }
      .intelligence-meta { margin: 0 0 8pt !important; }
      .intelligence-logo { display: block !important; margin: 0 0 18pt !important; }
      .intelligence-logo-actions, .intelligence-aside { display: none !important; }
      .intelligence-logo-identity { display: inline-flex !important; align-items: center !important; gap: 8pt !important; color: #10283a !important; font: 700 13pt/1 Arial, sans-serif !important; }
      .intelligence-logo-identity img { width: 28pt !important; height: 28pt !important; object-fit: contain !important; }
      .intelligence-metrics { display: grid !important; grid-template-columns: repeat(4, minmax(0, 1fr)) !important; gap: 0 !important; margin: 20pt 0 22pt !important; border-top: 1px solid #d8d1c4 !important; border-bottom: 1px solid #d8d1c4 !important; }
      .intelligence-metrics > div { min-width: 0 !important; padding: 11pt 12pt !important; border: 0 !important; border-right: 1px solid #d8d1c4 !important; }
      .intelligence-metrics > div:first-child { padding-left: 0 !important; }
      .intelligence-metrics > div:last-child { border-right: 0 !important; }
      .intelligence-metrics strong { font-size: 16pt !important; line-height: 1.1 !important; }
      .intelligence-metrics span { font-size: 8.5pt !important; line-height: 1.3 !important; }
      .intelligence-metrics small { font-size: 7.5pt !important; line-height: 1.3 !important; }
      .intelligence-content { padding-top: 0 !important; }
      .intelligence-main > section, .intelligence-aside > section { margin: 0 0 16pt !important; padding: 0 0 15pt !important; border-color: #d8d1c4 !important; }
      .intelligence-main > section:last-child { margin-bottom: 0 !important; }
      .valuation-history, .takeaways, .change-log, .intelligence-sources { margin: 10pt 0 0 !important; }
      .change-log { padding-left: 18pt !important; }
      .profile-verification { margin: 22pt 0 0 !important; padding-top: 9pt !important; border-top: 1px solid #d8d1c4 !important; }
      a { color: #17222d !important; text-decoration: none !important; }
    `;
    document.head.append(printStyle);
    const opened = [...document.querySelectorAll('details')].map(d => [d, d.open]);
    document.querySelectorAll('details').forEach(d => d.open = true);
    const restore = () => {
      opened.forEach(([detail, open]) => detail.open = open);
      printStyle.remove();
      window.removeEventListener('afterprint', restore);
    };
    window.addEventListener('afterprint', restore);
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => window.print()));
  };
  document.querySelectorAll('[data-print]').forEach(button => button.addEventListener('click', () => {
    button.closest('.company-profile, .intelligence-profile') ? printCompanyProfile() : printDocument();
  }));
  if (new URLSearchParams(location.search).get('download') === 'pdf') {
    window.addEventListener('load', () => window.setTimeout(printCompanyProfile, 250), { once: true });
  }
  window.addEventListener('storage', event => {
    if (event.key !== key) return;
    try {
      const incoming = JSON.parse(event.newValue || '{}');
      state.saved = Array.isArray(incoming.saved) ? incoming.saved.filter(x => typeof x === 'string') : [];
      state.progress = incoming.progress && typeof incoming.progress === 'object' ? incoming.progress : {};
      refresh();
    } catch { /* Ignore malformed state from another tab. */ }
  });
  document.querySelectorAll('[data-reader-loop]').forEach(rail => {
    const count = Number(rail.dataset.readerCount || 0);
    if (!count || rail.children.length < count * 2) return;
    let moving = false;
    const spanWidth = () => [...rail.children].slice(0, count).reduce((total, card) => total + card.getBoundingClientRect().width, 0);
    const moveToStart = () => {
      const width = spanWidth();
      if (width) rail.scrollLeft = width;
    };
    requestAnimationFrame(moveToStart);
    rail.addEventListener('scroll', () => {
      if (moving) return;
      const width = spanWidth();
      if (!width) return;
      const atEnd = rail.scrollLeft >= (width * 2) - rail.clientWidth - 2;
      if (rail.scrollLeft > 1 && !atEnd) return;
      moving = true;
      rail.scrollLeft = rail.scrollLeft <= 1 ? rail.scrollLeft + width : rail.scrollLeft - width;
      moving = false;
    });
  });
  document.querySelectorAll('[data-theme-toggle]').forEach(button => {
    const sync = () => button.setAttribute('aria-label', document.documentElement.getAttribute('data-theme') === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    sync();
    button.addEventListener('click', () => {
      const dark = document.documentElement.getAttribute('data-theme') !== 'dark';
      if (dark) document.documentElement.setAttribute('data-theme', 'dark'); else document.documentElement.removeAttribute('data-theme');
      try { localStorage.setItem('theme', dark ? 'dark' : 'light'); } catch (error) {}
      sync();
    });
  });
  document.querySelectorAll('[data-noop]').forEach(item => item.addEventListener('click', event => event.preventDefault()));
  document.querySelectorAll('[data-login-form]').forEach(form => form.addEventListener('submit', event => event.preventDefault()));
  document.querySelectorAll('[data-show-password]').forEach(button => button.addEventListener('click', () => {
    const input = document.getElementById(button.getAttribute('aria-controls'));
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    button.textContent = show ? 'Hide' : 'Show';
    button.setAttribute('aria-pressed', String(show));
  }));
  const dashboard = document.querySelector('[data-ipo-dashboard]');
  if (dashboard) {
    const records = JSON.parse(dashboard.querySelector('.ipo-dashboard-data').textContent);
    const rows = dashboard.querySelector('[data-dashboard-rows]');
    const count = dashboard.querySelector('[data-dashboard-count]');
    const pagination = dashboard.querySelector('[data-dashboard-pagination]');
    const chips = dashboard.querySelector('[data-dashboard-chips]');
    const compare = dashboard.querySelector('[data-dashboard-compare]');
    const savedButton = dashboard.querySelector('[data-dashboard-saved-view]');
    const params = new URLSearchParams(location.search);
    const getSaved = () => { try { return JSON.parse(localStorage.getItem('tpl-dashboard-saved-v1') || '[]'); } catch { return []; } };
    let saved = getSaved();
    let selected = [];
    const state = { view: params.get('view') || 'all', query: params.get('q') || '', sector: params.get('sector') || '', stage: params.get('stage') || '', window: params.get('window') || '', lifecycle: params.get('lifecycle') || '', research: params.get('research') || '', sort: params.get('sort') || 'priority', page: Math.max(1, Number(params.get('page')) || 1) };
    const search = dashboard.querySelector('[data-dashboard-search]');
    const selects = { sector: dashboard.querySelector('[data-dashboard-sector]'), stage: dashboard.querySelector('[data-dashboard-stage]'), window: dashboard.querySelector('[data-dashboard-window]'), lifecycle: dashboard.querySelector('[data-dashboard-lifecycle]'), research: dashboard.querySelector('[data-dashboard-research]'), sort: dashboard.querySelector('[data-dashboard-sort]') };
    selects.lifecycle.closest('label').firstChild.textContent = 'Process status';
    selects.research.closest('label').firstChild.textContent = 'Timing evidence';
    selects.lifecycle.innerHTML = '<option value="">All process statuses</option>';
    selects.research.innerHTML = '<option value="">All timing evidence</option>';
    const headers = dashboard.querySelectorAll('thead th');
    headers[2].textContent = 'Filing stage';
    headers[3].textContent = 'Target window';
    const escape = value => String(value || '').replace(/[&<>"']/g, char => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;' })[char]);
    const options = (select, values, label) => { [...new Set(values.filter(Boolean))].sort().forEach(value => select.insertAdjacentHTML('beforeend', `<option value="${escape(value)}">${escape(value)}</option>`)); select.value = state[label] || ''; };
    selects.window.innerHTML = '<option value="">Any window</option>';
    options(selects.sector, records.map(item => item.sector), 'sector'); options(selects.stage, records.map(item => item.stage), 'stage');
    options(selects.lifecycle, records.map(item => item.processStatus), 'lifecycle');
    options(selects.research, records.map(item => item.timingEvidence), 'research');
    options(selects.window, records.map(item => item.window), 'window');
    Object.entries(selects).forEach(([name, select]) => { if (name !== 'sort') select.value = state[name] || ''; }); selects.sort.value = state.sort;
    search.value = state.query;
    selects.sort.insertAdjacentHTML('beforeend', '<option value="window">Expected window</option>');
    const priority = { 'Reported target': 0, 'Public filing': 1, 'Roadshow': 2, 'Confidential submission': 3, 'Preparing': 4, 'Watching': 5, 'Postponed': 6, 'Withdrawn': 7, 'Listed': 8 };
    const windowPriority = { 'Reported target: Oct 21': 0, 'Active filing': 1, '2026 watch': 2, '2027 watch': 3, 'Not announced': 4 };
    const valuationNumber = value => Number(String(value || '').replace(/[^0-9.]/g, '')) || -1;
    const writeURL = () => { const next = new URLSearchParams(); Object.entries(state).forEach(([key, value]) => { if (value && !(key === 'view' && value === 'all') && !(key === 'sort' && value === 'priority') && !(key === 'page' && value === 1)) next.set(key, value); }); history.replaceState({}, '', `${location.pathname}${next.size ? `?${next}` : ''}`); };
    const visible = () => records.filter(item => {
      const haystack = `${item.name} ${item.sector}`.toLowerCase();
      if (state.query && !haystack.includes(state.query.toLowerCase())) return false;
      if (state.sector && item.sector !== state.sector) return false;
      if (state.stage && item.stage !== state.stage) return false;
      if (state.window && item.window !== state.window) return false;
      if (state.lifecycle && item.processStatus !== state.lifecycle) return false;
      if (state.research && item.timingEvidence !== state.research) return false;
      if (state.view === 'active' && ['In progress','Preparing'].indexOf(item.processStatus) < 0) return false;
      if (state.view === 'watching' && !(item.research || ['higgsfield','prometheus','ramp','revolut'].includes(item.slug))) return false;
      if (state.view === 'paused' && ['Delayed / on hold','Withdrawn'].indexOf(item.processStatus) < 0) return false;
      if (state.view === 'public' && !['Public','Acquired','Subsidiary'].includes(item.lifecycle)) return false;
      if (state.view === 'saved' && !saved.includes(item.slug)) return false;
      return true;
    }).sort((a,b) => state.sort === 'name' ? a.name.localeCompare(b.name) : state.sort === 'updated' ? String(b.updated).localeCompare(String(a.updated)) : state.sort === 'valuation' ? valuationNumber(b.valuation) - valuationNumber(a.valuation) : state.sort === 'window' ? (windowPriority[a.window] ?? 99) - (windowPriority[b.window] ?? 99) || a.name.localeCompare(b.name) : (priority[a.stage] - priority[b.stage]) || a.name.localeCompare(b.name));
    const render = () => {
      const list = visible(); const perPage = 15; const pages = Math.max(1, Math.ceil(list.length / perPage)); state.page = Math.min(state.page, pages); const start = (state.page - 1) * perPage; const slice = list.slice(start, start + perPage);
      count.textContent = `${list.length} of ${records.length} companies`;
      rows.innerHTML = slice.length ? slice.map(item => `<tr data-slug="${escape(item.slug)}"><td><input type="checkbox" data-dashboard-compare-box value="${escape(item.slug)}" aria-label="Compare ${escape(item.name)}" ${selected.includes(item.slug) ? 'checked' : ''}></td><td><div class="ipo-dashboard-company"><span class="ipo-dashboard-company-logo">${item.logo ? `<img src="${escape(item.logo)}" alt="">` : escape(item.name[0])}</span><div><a href="/companies/${escape(item.slug)}/">${escape(item.name)}</a><small>${escape(item.sector)}${item.research ? ' · TPL research' : ''}</small></div></div></td><td><span class="ipo-stage" data-stage="${escape(item.stage)}">${escape(item.stage)}</span><small>${escape(item.sourceType)}</small></td><td>${escape(item.window)}</td><td>${escape(item.valuation)}<small>${escape(item.valuationBasis)}${item.valuationDate ? ` · ${escape(item.valuationDate)}` : ''}</small></td><td class="ipo-dashboard-question">${escape(item.summary)}</td><td><div class="ipo-dashboard-actions-cell"><button type="button" data-dashboard-save="${escape(item.slug)}" aria-pressed="${saved.includes(item.slug)}" aria-label="Save ${escape(item.name)}">${saved.includes(item.slug) ? '♥' : '♡'}</button><button type="button" data-dashboard-expand="${escape(item.slug)}" aria-expanded="false" aria-label="Show ${escape(item.name)} details">⌄</button></div></td></tr>`).join('') : `<tr><td colspan="7">No companies match these filters. <button type="button" data-dashboard-clear>Clear filters</button></td></tr>`;
      pagination.innerHTML = `<span>Showing ${list.length ? start + 1 : 0}–${Math.min(start + perPage, list.length)} of ${list.length}</span><div><button type="button" data-dashboard-page="${state.page - 1}" ${state.page === 1 ? 'disabled' : ''}>Previous</button><button type="button" disabled>Page ${state.page} of ${pages}</button><button type="button" data-dashboard-page="${state.page + 1}" ${state.page === pages ? 'disabled' : ''}>Next</button></div>`;
      const active = Object.entries({ sector: state.sector, stage: state.stage, window: state.window, lifecycle: state.lifecycle, research: state.research }).filter(([, value]) => value); chips.hidden = !active.length; chips.innerHTML = active.map(([key, value]) => `<button type="button" data-dashboard-remove="${key}">${escape(value)} ×</button>`).join('') + (active.length ? '<button type="button" data-dashboard-clear>Clear filters</button>' : '');
      dashboard.querySelectorAll('[data-dashboard-view]').forEach(button => button.setAttribute('aria-selected', String(button.dataset.dashboardView === state.view)));
      savedButton.querySelector('b').textContent = saved.length;
      compare.hidden = selected.length < 1; compare.innerHTML = selected.length ? `<strong>${selected.length} selected</strong><span>${selected.map(slug => records.find(item => item.slug === slug)?.name).join(', ')}</span><button type="button" data-dashboard-compare-open ${selected.length < 2 ? 'disabled' : ''}>Compare</button><button type="button" data-dashboard-compare-clear>Clear</button>` : '';
      writeURL();
    };
    const reset = () => { state.page = 1; render(); };
    search.addEventListener('input', () => { state.query = search.value.trim(); reset(); }); Object.entries(selects).forEach(([name, select]) => select.addEventListener('change', () => { state[name] = select.value; reset(); }));
    dashboard.addEventListener('click', event => { const target = event.target.closest('button'); if (!target) return; if (target.dataset.dashboardView) { state.view = target.dataset.dashboardView; reset(); } if (target.dataset.dashboardPage) { state.page = Number(target.dataset.dashboardPage); render(); } if (target.dataset.dashboardSave) { const slug = target.dataset.dashboardSave; saved = saved.includes(slug) ? saved.filter(item => item !== slug) : [...saved, slug]; localStorage.setItem('tpl-dashboard-saved-v1', JSON.stringify(saved)); render(); } if (target.dataset.dashboardRemove) { state[target.dataset.dashboardRemove] = ''; selects[target.dataset.dashboardRemove].value = ''; reset(); } if (target.matches('[data-dashboard-clear]')) { Object.assign(state, { query:'', sector:'', stage:'', window:'', lifecycle:'', research:'', page:1 }); search.value = ''; Object.entries(selects).forEach(([name, select]) => { if (name !== 'sort') select.value = ''; }); render(); } if (target.dataset.dashboardExpand) { const row = target.closest('tr'); const alreadyOpen = row.nextElementSibling?.classList.contains('ipo-dashboard-detail'); dashboard.querySelectorAll('.ipo-dashboard-detail').forEach(detail => detail.remove()); dashboard.querySelectorAll('[data-dashboard-expand]').forEach(button => button.setAttribute('aria-expanded', 'false')); if (!alreadyOpen) { const item = records.find(record => record.slug === target.dataset.dashboardExpand); target.setAttribute('aria-expanded','true'); row.insertAdjacentHTML('afterend', `<tr class="ipo-dashboard-detail"><td colspan="7"><div><section><h3>Financial snapshot</h3><p>${escape(item.description)}</p><p><strong>${escape(item.revenue)}</strong> ${escape(item.revenueNote)}</p></section><section><h3>The TPL view</h3><p>${escape(item.summary)}</p><p><strong>Risk:</strong> ${escape(item.risk)}</p></section><section><h3>IPO evidence</h3><p>${escape(item.evidence)}</p><p>${item.source ? `<a href="${escape(item.source)}" target="_blank" rel="noopener">Source ↗</a> · ` : ''}<a href="/companies/${escape(item.slug)}/">Company profile ↗</a></p></section></div></td></tr>`); } } if (target.matches('[data-dashboard-compare-clear]')) { selected = []; render(); } if (target.matches('[data-dashboard-compare-open]')) { const items = selected.map(slug => records.find(item => item.slug === slug)); const fields = [['Sector','sector'],['Lifecycle','lifecycle'],['IPO stage','stage'],['Expected window','window'],['Latest valuation','valuation'],['Revenue metric','revenue'],['Main risk','risk']]; compare.insertAdjacentHTML('beforeend', `<div class="ipo-dashboard-compare-result"><strong>Comparison</strong><table><thead><tr><th>Field</th>${items.map(item => `<th>${escape(item.name)}</th>`).join('')}</tr></thead><tbody>${fields.map(([label,key]) => `<tr><th>${label}</th>${items.map(item => `<td>${escape(item[key] || 'Not comparable')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`); } });
    dashboard.addEventListener('change', event => { const box = event.target.closest('[data-dashboard-compare-box]'); if (!box) return; selected = box.checked ? [...new Set([...selected, box.value])].slice(-3) : selected.filter(slug => slug !== box.value); render(); }); savedButton.addEventListener('click', () => { state.view = 'saved'; reset(); });
    render();
  }
  refresh();
  if (!available) announce('Browser storage is unavailable. Saved articles and reading progress may not persist.');
})();
