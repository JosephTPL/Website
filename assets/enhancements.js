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
  document.querySelector('[data-print]')?.addEventListener('click', () => {
    const opened = [...document.querySelectorAll('details')].map(d => [d,d.open]);
    document.querySelectorAll('details').forEach(d => d.open = true);
    const restore = () => { opened.forEach(([d,open]) => d.open = open); window.removeEventListener('afterprint',restore); };
    window.addEventListener('afterprint',restore);
    window.print();
  });
  window.addEventListener('storage', event => {
    if (event.key !== key) return;
    try {
      const incoming = JSON.parse(event.newValue || '{}');
      state.saved = Array.isArray(incoming.saved) ? incoming.saved.filter(x => typeof x === 'string') : [];
      state.progress = incoming.progress && typeof incoming.progress === 'object' ? incoming.progress : {};
      refresh();
    } catch { /* Ignore malformed state from another tab. */ }
  });
  refresh();
  if (!available) announce('Browser storage is unavailable. Saved articles and reading progress may not persist.');
})();
