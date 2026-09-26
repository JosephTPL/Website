(()=>{
  const root=document.querySelector('#valuation-chart');
  if(!root)return;
  let series=[];
  try{series=JSON.parse(root.dataset.valuationSeries||'[]')}catch(_){return}
  const canvas=root.querySelector('.valuation-chart-canvas');
  const tooltip=root.querySelector('.valuation-tooltip');
  const legend=document.querySelector('.valuation-legend');
  // A focused opening view preserves legibility across companies with very different scales.
  const selected=new Set(['spacex','anthropic','openai'].filter(slug=>series.some(item=>item.slug===slug)));
  let range='all';
  let indexed=false;
  const colors=['#ff5c58','#5d9cff','#f3ab39','#58b293','#c87fe8','#56c3bf','#e07a9e','#d8cb70','#9d88e9','#ec8c54','#61a4d9','#a9b75c','#db7690','#b491df','#4eb2a7','#dfbf65','#7697e8','#df6e67','#73bd83','#e69aab','#4f86aa','#a7d2c2','#d99845','#a382bd','#b6c56b','#c56e62','#78aacd','#cba85f','#84a86b'];
  const colorFor=item=>colors[series.findIndex(entry=>entry.slug===item.slug)%colors.length];
  const money=value=>value>=1000?`$${(value/1000).toLocaleString('en-US',{maximumFractionDigits:1})}T`:value<1?`$${Math.round(value*1000)}M`:`$${value.toLocaleString('en-US',{maximumFractionDigits:1})}B`;
  const percent=value=>`${value>0?'+':''}${value.toLocaleString('en-US',{maximumFractionDigits:0})}%`;
  const visible=()=>series.filter(item=>selected.has(item.slug));
  const filtered=()=>{
    const now=new Date();
    const cutoff=range==='all'?null:new Date(now.getFullYear()-Number(range),now.getMonth(),now.getDate());
    return visible().map(item=>({...item,events:item.events.filter(event=>!cutoff||new Date(event.date)>=cutoff)})).filter(item=>item.events.length);
  };
  const showTooltip=(event,item,color)=>{
    tooltip.hidden=false;
    tooltip.innerHTML=`<strong>${item.name}</strong><span>${event.label} · ${event.round||'Reported event'}</span><b>${event.value}${indexed?` <small>${percent(event.chartAmount)} from first visible event</small>`:''}</b>`;
    tooltip.style.left=`${Math.max(8,Math.min(root.clientWidth-190,event.clientX-root.getBoundingClientRect().left+12))}px`;
    tooltip.style.top=`${Math.max(8,event.clientY-root.getBoundingClientRect().top-94)}px`;
    tooltip.style.setProperty('--tip-color',color);
  };
  const draw=()=>{
    const items=filtered().map(item=>{
      const baseline=item.events[0].amount;
      return {...item,events:item.events.map(event=>({...event,chartAmount:indexed?((event.amount/baseline-1)*100):event.amount}))};
    });
    canvas.replaceChildren();legend.replaceChildren();
    if(!items.length){canvas.textContent='No disclosed valuation events in this period.';return}
    const allEvents=items.flatMap(item=>item.events);
    const dates=allEvents.map(item=>new Date(item.date).getTime());
    const amounts=allEvents.map(item=>item.chartAmount);
    const minDate=Math.min(...dates),maxDate=Math.max(...dates),maxAmount=Math.max(...amounts)*1.12;
    const minAmount=indexed?Math.min(0,...amounts)*1.12:0;
    const width=1000,height=520,pad={top:42,right:38,bottom:61,left:76};
    const x=value=>pad.left+(width-pad.left-pad.right)*((value-minDate)/(maxDate-minDate||1));
    const y=value=>height-pad.bottom-(height-pad.top-pad.bottom)*((value-minAmount)/(maxAmount-minAmount||1));
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('preserveAspectRatio','none');svg.setAttribute('aria-hidden','true');
    const add=(name,attrs={},text='')=>{const el=document.createElementNS('http://www.w3.org/2000/svg',name);Object.entries(attrs).forEach(([key,value])=>el.setAttribute(key,value));if(text)el.textContent=text;svg.append(el);return el};
    for(let i=0;i<5;i++){
      const amount=maxAmount*i/4,py=y(amount);
      add('line',{x1:pad.left,y1:py,x2:width-pad.right,y2:py,class:'valuation-gridline'});
      add('text',{x:pad.left-13,y:py+5,'text-anchor':'end',class:'valuation-axis-label'},indexed?percent(amount):money(amount));
    }
    const tickCount=Math.min(5,Math.max(2,new Set(allEvents.map(event=>event.date.slice(0,4))).size));
    for(let i=0;i<tickCount;i++){
      const time=minDate+(maxDate-minDate)*(i/(tickCount-1||1)),px=x(time),label=new Date(time).toLocaleDateString('en-US',{year:'numeric',month:'short'});
      add('line',{x1:px,y1:pad.top,x2:px,y2:height-pad.bottom,class:'valuation-gridline vertical'});
      add('text',{x:px,y:height-24,'text-anchor':'middle',class:'valuation-axis-label'},label);
    }
    items.forEach(item=>{
      const color=colorFor(item);let path='';
      item.events.forEach((event,index)=>{
        const px=x(new Date(event.date).getTime()),py=y(event.chartAmount);
        if(index===0)path+=`M ${px} ${py}`;
        else{const prior=item.events[index-1];path+=` H ${px} V ${py}`;}
      });
      add('path',{d:path,class:'valuation-line',stroke:color});
      item.events.forEach(event=>{
        const point=add('circle',{cx:x(new Date(event.date).getTime()),cy:y(event.chartAmount),r:6,fill:color,class:'valuation-point',tabindex:'0'});
        point.addEventListener('pointerenter',e=>showTooltip(e,item,color));
        point.addEventListener('pointerleave',()=>tooltip.hidden=true);
        point.addEventListener('focus',()=>{const rect=root.getBoundingClientRect();showTooltip({clientX:rect.left+x(new Date(event.date).getTime()),clientY:rect.top+y(event.chartAmount)},item,color)});
        point.addEventListener('blur',()=>tooltip.hidden=true);
      });
      const link=document.createElement('a');link.href=item.url;link.className='valuation-legend-item';link.innerHTML=`<i style="--series-color:${color}"></i>${item.name}`;legend.append(link);
    });
    canvas.append(svg);
  };
  document.querySelectorAll('.valuation-company').forEach(button=>{
    const active=selected.has(button.dataset.series);button.classList.toggle('is-active',active);button.setAttribute('aria-pressed',String(active));
    button.addEventListener('click',()=>{
    const slug=button.dataset.series;selected.has(slug)?selected.delete(slug):selected.add(slug);
    if(!selected.size)selected.add(slug);
    button.classList.toggle('is-active',selected.has(slug));button.setAttribute('aria-pressed',String(selected.has(slug)));draw();
    });
  });
  document.querySelectorAll('.valuation-range button').forEach(button=>button.addEventListener('click',()=>{
    if(button.classList.contains('valuation-index')){indexed=!indexed;button.classList.toggle('is-active',indexed);button.setAttribute('aria-pressed',String(indexed));draw();return}
    range=button.dataset.range;document.querySelectorAll('.valuation-range button').forEach(item=>item.classList.toggle('is-active',item===button));draw();
  }));
  draw();
})();
