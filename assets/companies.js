(() => {
  const input = document.querySelector('#company-search');
  const cards = [...document.querySelectorAll('.company-directory-card')];
  const count = document.querySelector('#company-result-count');
  if (!input || !cards.length) return;
  const update = () => {
    const q = input.value.trim().toLowerCase(); let shown = 0;
    cards.forEach(card => { const visible = !q || card.dataset.search.toLowerCase().includes(q); card.hidden = !visible; if (visible) shown++; });
    count.textContent = `${shown} ${shown === 1 ? 'company' : 'companies'}`;
  };
  input.addEventListener('input', update); update();
})();
