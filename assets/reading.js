(() => {
  const article = document.querySelector('.article-body');
  if (!article) return;
  const progress = document.querySelector('#reading-progress'), status = document.querySelector('#reading-status'), toggle = document.querySelector('#contents-toggle'), mobile = document.querySelector('#mobile-contents');
  const slug = document.body.dataset.article;
  const headings = [...document.querySelectorAll('#brief, .article-body h2[id], .article-body h3[id]')];
  let pending = false, hasScrolled = false, lastWrite = 0;
  function update() {
    pending = false;
    const start = article.getBoundingClientRect().top + window.scrollY;
    const distance = Math.max(1, article.offsetHeight - window.innerHeight + 110);
    const ratio = Math.max(0,Math.min(1,(window.scrollY-start+110)/distance));
    const value = Math.round(ratio*100);
    progress.value = value; status.textContent = value+'% read';
    let active = '';
    for (const heading of headings) if (heading.getBoundingClientRect().top < 170) active = heading.id;
    document.querySelectorAll('.contents a[href^="#"]').forEach(a => { if (a.hash === '#'+active) a.setAttribute('aria-current','location');else a.removeAttribute('aria-current'); });
    if (hasScrolled && value > 2 && Date.now()-lastWrite > 500) {
      window.LedgerReader?.saveProgress(slug,{percent:value,ratio,title:document.body.dataset.title,updated:Date.now()}); lastWrite=Date.now();
    }
  }
  function schedule() { hasScrolled=true; if(!pending){pending=true;requestAnimationFrame(update);} }
  window.addEventListener('scroll',schedule,{passive:true});
  window.addEventListener('resize',update);
  window.addEventListener('pagehide',() => { lastWrite=0;update(); });
  if(toggle) toggle.addEventListener('click',() => {const expanded=toggle.getAttribute('aria-expanded') === 'true';toggle.setAttribute('aria-expanded',String(!expanded));mobile.hidden=expanded;toggle.querySelector('span').textContent=expanded?'＋':'−';});
  mobile?.addEventListener('click',event => { if(event.target.closest('a')) {mobile.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.querySelector('span').textContent='＋';} });
  function initialize() {
    const saved = window.LedgerReader?.progress(slug);
    const banner = document.querySelector('.resume-banner');
    const valid = saved && Number.isFinite(saved.ratio) && saved.percent > 2 && saved.percent < 98;
    if(valid) {
      banner.hidden=false;banner.querySelector('span').textContent=`You reached ${saved.percent}% of this article.`;
      const resume=() => {const start=article.getBoundingClientRect().top+window.scrollY;const distance=Math.max(1,article.offsetHeight-window.innerHeight+110);window.scrollTo({top:start+Math.max(0,Math.min(1,saved.ratio))*distance-110,behavior:'instant'});banner.hidden=true;};
      banner.querySelector('[data-resume]').addEventListener('click',resume);
      if(new URLSearchParams(location.search).get('resume') === '1' && !location.hash) resume();
    }
    update();
  }
  window.addEventListener('load',initialize,{once:true});
  if(document.readyState === 'complete') initialize();
  update();
})();
