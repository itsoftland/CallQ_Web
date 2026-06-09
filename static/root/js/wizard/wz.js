/* CallQ Grouping Wizard — Vanilla JS */
'use strict';

/* ── SVG Icons ── */
const ICONS = window.CQ_ICONS || {};
function ico(name, style) {
  const p = ICONS[name] || '';
  const s = style ? ` style="${style}"` : '';
  return `<svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;display:block;${style||''}">${p}</svg>`;
}

/* ── Type metadata ── */
const TYPE = {
  TOKEN_DISPENSER:{label:'Token Dispenser',plural:'Token Dispensers',short:'Dispenser',icon:'fa-ticket',color:'var(--t-disp)',bg:'var(--t-disp-bg)'},
  KEYPAD:  {label:'Keypad',plural:'Keypads',short:'Keypad',icon:'fa-keyboard',color:'var(--t-keypad)',bg:'var(--t-keypad-bg)'},
  LED:     {label:'LED Display',plural:'LEDs',short:'LED',icon:'fa-lightbulb',color:'var(--t-led)',bg:'var(--t-led-bg)'},
  BROKER:  {label:'Broker',plural:'Brokers',short:'Broker',icon:'fa-server',color:'var(--t-broker)',bg:'var(--t-broker-bg)'},
  TV:      {label:'TV Display',plural:'TVs',short:'TV',icon:'fa-tv',color:'var(--t-tv)',bg:'var(--t-tv-bg)'},
};
const TYPE_ORDER = ['TOKEN_DISPENSER','KEYPAD','LED','BROKER','TV'];

/* ── State ── */
let WZ = window.__WZ || {};
let state = {
  brId: '',
  dcId: '',
  gName: '',
  counts: {TOKEN_DISPENSER:0, KEYPAD:0, LED:0, BROKER:0, TV:0},
  pool: {TOKEN_DISPENSER:[], KEYPAD:[], LED:[], BROKER:[], TV:[]},
  asn: {included:{}, dispToKeypad:{}, keypadToLed:{}, keypadToBroker:{}, brokerToTv:{}},
  // dispToKeypad: { dispId: [kpId1, kpId2, ...] }  — multi-keypad per dispenser
  poolMode: false,
  cur: 0,
  loading: false,
};

/* ── Derived ── */
function inclDisp() { return (state.pool.TOKEN_DISPENSER||[]).filter(d=>state.asn.included[d.id]); }
function kpDevs() {
  const ids = [];
  inclDisp().forEach(d => {
    const arr = state.asn.dispToKeypad[d.id] || [];
    arr.forEach(kId => { if (!ids.includes(kId)) ids.push(kId); });
  });
  return ids.map(id=>(state.pool.KEYPAD||[]).find(d=>d.id===id)).filter(Boolean);
}
function brkDevs()  {
  const ids = [...new Set(kpDevs().map(k=>state.asn.keypadToBroker[k.id]).filter(Boolean))];
  return ids.map(id=>(state.pool.BROKER||[]).find(d=>d.id===id)).filter(Boolean);
}
function ledIds()   { return [...new Set(kpDevs().map(k=>state.asn.keypadToLed[k.id]).filter(Boolean))]; }
function tvIds()    { return [...new Set(brkDevs().map(b=>state.asn.brokerToTv[b.id]).filter(Boolean))]; }

/* ── Steps ── */
function buildSteps() {
  const c = state.counts;
  const steps = [{id:'config',label:'Configure',kind:'config'}];
  if (c.TOKEN_DISPENSER>0 && c.KEYPAD>0)
    steps.push({id:'disp_keypad',label:'Dispensers → Keypads',kind:'map',from:'TOKEN_DISPENSER',to:'KEYPAD'});
  if (c.KEYPAD>0 && c.LED>0)
    steps.push({id:'keypad_led',label:'Keypads → LEDs',kind:'map',from:'KEYPAD',to:'LED'});
  if (c.KEYPAD>0 && c.BROKER>0)
    steps.push({id:'keypad_broker',label:'Keypads → Brokers',kind:'map',from:'KEYPAD',to:'BROKER'});
  if (c.BROKER>0 && c.TV>0)
    steps.push({id:'broker_tv',label:'Brokers → TVs',kind:'map',from:'BROKER',to:'TV'});
  steps.push({id:'review',label:'Review',kind:'review'});
  return steps;
}

/* ── Validation ── */
function stageOk(id) {
  const inc = inclDisp(), kp = kpDevs(), brk = brkDevs();
  if(id==='disp_keypad')   return inc.length>=1 && inc.every(d=>{ const arr=state.asn.dispToKeypad[d.id]; return arr&&arr.length>0; });
  if(id==='keypad_led')    return kp.length>=1  && kp.every(k=>state.asn.keypadToLed[k.id]);
  if(id==='keypad_broker') return kp.length>=1  && kp.every(k=>state.asn.keypadToBroker[k.id]);
  if(id==='broker_tv')     return brk.length>=1 && brk.every(b=>state.asn.brokerToTv[b.id]);
  return true;
}
function stepOk(step) {
  if(step.kind==='config') return state.gName.trim() && (state.brId||state.dcId) && state.counts.TOKEN_DISPENSER>0 && state.counts.KEYPAD>0;
  if(step.kind==='map')    return stageOk(step.id);
  return true;
}

/* ── Render: Stepper Rail ── */
function renderStepper() {
  const steps = buildSteps();
  const cur = Math.min(state.cur, steps.length-1);
  document.getElementById('wz-stepper').innerHTML = steps.map((s,i) => {
    const cls = i===cur ? 'current' : i<cur ? 'done' : '';
    const node = i<cur ? ico('fa-check') : (i+1);
    const conn = i<steps.length-1 ? `<div class="rconn ${i<cur?'fill':''}"></div>` : '';
    return `<div class="rstep ${cls}" data-idx="${i}" onclick="wzJump(${i})">\n      <span class="nodeo">${node}</span><span class="lbl">${s.label}</span>\n    </div>${conn}`;
  }).join('');
}

/* ── Render: Chain Pipeline ── */
function chainNode(type, active) {
  const t=TYPE[type], c=state.counts[type];
  return `<div class="cnode ${active?'active':''}"><div class="cic" style="background:${t.bg};color:${t.color};border-color:${active?t.color:'transparent'}">${ico(t.icon)}</div><div class="cnm">${t.short}</div><div class="ccount">${c} device${c===1?'':'s'}</div></div>`;
}
function renderChain(activeTypes) {
  activeTypes=activeTypes||[];
  const c=state.counts, on=t=>activeTypes.includes(t);
  const ar=`<div class="carrow">${ico('fa-arrow-right-long')}</div>`;
  let html=chainNode('TOKEN_DISPENSER',on('TOKEN_DISPENSER'))+ar+chainNode('KEYPAD',on('KEYPAD'));
  const branches=[];
  if(c.LED>0) branches.push(['LED']);
  if(c.BROKER>0) branches.push(c.TV>0?['BROKER','TV']:['BROKER']);
  if(branches.length===1) html+=ar+branches[0].map((t,i)=>(i>0?ar:'')+chainNode(t,on(t))).join('');
  else if(branches.length===2) html+=`<div class="carrow">${ico('fa-code-fork')}</div><div class="cbranch"><div class="chain">${branches[0].map((t,i)=>(i>0?ar:'')+chainNode(t,on(t))).join('')}</div><div class="chain">${branches[1].map((t,i)=>(i>0?ar:'')+chainNode(t,on(t))).join('')}</div></div>`;
  return `<div class="chain">${html}</div>`;
}

/* ── Render: Count Cards ── */
function renderCountCards() {
  return TYPE_ORDER.map(type=>{
    const t=TYPE[type], opt=['LED','BROKER','TV'].includes(type), zero=state.counts[type]===0;
    const excl=['TOKEN_DISPENSER','KEYPAD','LED'].includes(type);
    const devs=state.pool[type]||[], total=devs.length, avail=excl?devs.filter(d=>!d.inGroup).length:total;
    let badge=zero?`<div class="badge-skip">${ico('fa-circle-minus')} step skipped</div>`:'';
    let avline='';
    if(total>0){const col=avail===0?'var(--danger)':avail<total?'var(--warning)':'var(--success)';const ic=avail===0?'fa-circle-xmark':avail===total?'fa-circle-check':'fa-circle-half-stroke';avline=`<div style="margin-top:8px;font-size:11px;font-weight:600;display:flex;align-items:center;gap:5px;color:${col}">${ico(ic)}<span>${excl?`${avail} of ${total} available`:`${total} in branch`}</span></div>`;}
    else if((state.brId||state.dcId)&&!state.loading) avline=`<div style="margin-top:8px;font-size:11px;font-weight:600;color:var(--ink-4);display:flex;align-items:center;gap:5px">${ico('fa-circle-exclamation')}<span>No devices registered</span></div>`;
    return `<div class="ccard${zero&&opt?' zero':''}" data-type="${type}"><div class="chead"><div class="cdico" style="background:${t.bg};color:${t.color}">${ico(t.icon)}</div><div><div class="ctitle">${t.plural}</div><div class="csub">${opt?'optional':'required'}</div></div></div><div class="counter"><button onclick="wzCount('${type}',-1)">${ico('fa-minus')}</button><input type="number" id="cnt-${type}" value="${state.counts[type]}" onchange="wzCountSet('${type}',this.value)"/><button onclick="wzCount('${type}',1)">${ico('fa-plus')}</button></div>${badge}${avline}</div>`;
  }).join('');
}

/* ── Pool Mode ── */
function wzSetPoolMode(on) { state.poolMode = !!on; wzRender(); }

/* ── Render: Config Step ── */
function renderConfig() {
  const steps=buildSteps();
  const skipped=[state.counts.LED===0&&'LED',state.counts.BROKER===0&&'Broker'].filter(Boolean);
  const skipMsg=skipped.length?`${skipped.join(' & ')} steps are skipped because you set their count to 0.`:'All device types configured — every mapping step will appear.';
  const selHtml=WZ.isDealerView
    ?`<div class="field"><label>Dealer Customer <span class="req">*</span></label><select class="select" id="wz-dc" onchange="wzSetDc(this.value)"><option value="">-- Select Customer --</option>${(WZ.dealerCustomers||[]).map(dc=>`<option value="${dc.id}"${state.dcId===String(dc.id)?' selected':''}>${dc.name}</option>`).join('')}</select></div>`
    :`<div class="field"><label>Branch <span class="req">*</span></label><select class="select" id="wz-br" onchange="wzSetBr(this.value)">${(WZ.branches||[]).map(b=>`<option value="${b.id}"${state.brId===String(b.id)?' selected':''}>${b.name}</option>`).join('')}</select></div>`;
  const poolToggleHtml=`<div style="background:var(--bg);border-radius:12px;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;border:1.5px solid ${state.poolMode?'var(--cq-primary)':'var(--border)'}"><div><div style="font-size:13.5px;font-weight:700;color:var(--ink-1);display:flex;align-items:center;gap:7px">${ico('fa-water')} Pool Mode${state.poolMode?` <span class="statchip ok" style="font-size:10px">Enabled</span>`:''}</div><div style="font-size:11.5px;color:var(--ink-3);margin-top:3px">Counters map directly to keypads — no dispenser chain</div></div><div class="switch${state.poolMode?' on':''}" onclick="wzSetPoolMode(${!state.poolMode})" style="flex-shrink:0;margin-left:16px"><div class="knob"></div></div></div>`;
  return `<div style="padding:26px"><div style="display:flex;align-items:center;gap:13px;margin-bottom:22px"><div style="width:40px;height:40px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:16px;background:var(--cq-primary-light);color:var(--cq-primary)">${ico('fa-sliders')}</div><div><div style="font-size:16px;font-weight:800">Group configuration</div><div style="font-size:12.5px;color:var(--ink-3);margin-top:1px">Name the group and tell us how many of each device it contains.</div></div></div><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:24px">${selHtml}<div class="field" style="grid-column:span 2"><label>Group name <span class="req">*</span></label><input class="input" id="wz-gname" placeholder="e.g. Counter 1 Setup" value="${state.gName.replace(/"/g,'&quot;')}" oninput="wzSetName(this.value)"/></div></div>${state.loading?'<div style="text-align:center;padding:20px;color:var(--ink-3);font-size:13px">⟳ Loading devices…</div>':''}<div class="field"><label>Devices in this group</label></div><div class="countgrid" style="margin-bottom:22px">${renderCountCards()}</div>${poolToggleHtml}<div style="background:var(--bg);border-radius:14px;padding:16px 18px"><div style="display:flex;align-items:center;gap:8px;margin-bottom:12px"><span style="font-size:12px;font-weight:700;color:var(--ink-2);text-transform:uppercase;letter-spacing:.5px">Your mapping flow</span><span class="statchip neutral">${steps.length} steps</span></div>${renderChain([])}<div style="margin-top:12px;font-size:12.5px;color:var(--ink-3);display:flex;align-items:center;gap:7px">${ico('fa-circle-info')} <span>${skipMsg}</span></div></div></div>`;
}

/* ── Render: Dropdown ── */
function deviceSelectHtml(fieldId, srcId, targetType, currentVal) {
  const opts = state.pool[targetType]||[];
  const sel = opts.find(o=>o.id===currentVal);
  const t = TYPE[targetType];
  const selHtml = `<select class="select" id="${fieldId}" onchange="wzMap('${fieldId}','${srcId}','${targetType}',this.value)" style="height:40px;font-size:13px">
    <option value="">-- Select ${t.short} --</option>
    ${opts.map(o=>`<option value="${o.id}"${o.id===currentVal?' selected':''}>${o.name} · ${o.code}</option>`).join('')}
  </select>`;
  return selHtml;
}

/* ── Render: Map Stage ── */
function renderMapStage(step) {
  const fromT=TYPE[step.from], toT=TYPE[step.to];
  const fieldMap = {disp_keypad:'dispToKeypad',keypad_led:'keypadToLed',keypad_broker:'keypadToBroker',broker_tv:'brokerToTv'};
  const field = fieldMap[step.id];
  const guidance = {
    disp_keypad:`Choose which <b>token dispensers</b> belong to this group, then link each to the <b>keypad</b> it drives.`,
    keypad_led:`Tell each <b>keypad</b> which <b>LED board</b> shows its called token number.`,
    keypad_broker:`Connect each <b>keypad</b> to the <b>broker</b> that routes its calls.`,
    broker_tv:`Point each <b>broker</b> at the <b>TV display</b> that shows its live queue.`,
  }[step.id];

  let rows='', done=0, total=0;

  if(step.id==='disp_keypad'){
    const all=state.pool.TOKEN_DISPENSER||[];
    const allKp=state.pool.KEYPAD||[];
    const inc=all.filter(d=>state.asn.included[d.id]);
    total=inc.length; done=inc.filter(d=>{ const a=state.asn.dispToKeypad[d.id]; return a&&a.length>0; }).length;
    rows=all.map(d=>{
      const on=!!state.asn.included[d.id];
      const selIds=state.asn.dispToKeypad[d.id]||[];
      let linkHtml;
      if(on){
        const kpChecks=allKp.map(k=>{
          const chk=selIds.includes(k.id)?'checked':'';
          return `<label style="display:flex;align-items:center;gap:7px;padding:7px 10px;border-radius:9px;cursor:pointer;font-size:13px;font-weight:600;background:${chk?'var(--cq-primary-light)':'var(--bg-2)'};border:1.5px solid ${chk?'var(--cq-primary)':'var(--border)'};transition:all .15s">
            <input type="checkbox" style="display:none" ${chk} onchange="wzToggleKeypad('${d.id}','${k.id}',this.checked)">
            ${ico(toT.icon)}<span>${k.name}</span><span style="color:var(--ink-4);font-size:11px">${k.code}</span>
          </label>`;
        }).join('');
        const badge=selIds.length>0?`<span class="statchip ok" style="margin-left:4px">${selIds.length} selected</span>`:'';
        linkHtml=`<span class="lk">${ico('fa-arrow-right-long')}</span><div class="tgt-wrap"><div class="tgt-label">${ico(toT.icon)} Routes to keypads ${badge}</div><div style="display:flex;flex-wrap:wrap;gap:7px;margin-top:6px">${kpChecks||'<span style="color:var(--ink-4);font-size:12px">No keypads available</span>'}</div></div>`;
      } else {
        linkHtml=`<span style="font-size:12.5px;color:var(--ink-4)">Not part of this group</span>`;
      }
      return `<div class="mapcard${on?' on':''}" id="mc-${d.id}">
        <div class="mrow">
          <div class="srcchip"><div class="sico" style="background:${fromT.bg};color:${fromT.color}">${ico(fromT.icon)}</div><div style="min-width:0"><div class="snm">${d.name}</div><div class="scode">${d.code} · ${d.model}</div></div></div>
          <div class="mlink">${linkHtml}</div>
          <div class="incl-toggle"><span class="it-lbl">${on?'Included':'Include'}</span>
            <div class="switch ${on?'on':''}" onclick="wzToggle('${d.id}')" id="sw-${d.id}"><div class="knob"></div></div>
          </div>
        </div>
      </div>`;
    }).join('');
    if(!rows) rows=`<div class="empty">${ico('fa-diagram-project')}<div style="font-size:13px;font-weight:600">No dispensers loaded yet</div></div>`;
  } else {
    const sources = step.id==='broker_tv' ? brkDevs() : kpDevs();
    total=sources.length; done=sources.filter(s=>state.asn[field][s.id]).length;
    rows=sources.length===0
      ? `<div class="empty">${ico('fa-diagram-project')}<div style="font-size:13px;font-weight:600">Finish the previous step first</div></div>`
      : sources.map(s=>{
          const mapped=state.asn[field][s.id];
          return `<div class="mapcard${mapped?' on':''}">
            <div class="mrow">
              <div class="srcchip"><div class="sico" style="background:${fromT.bg};color:${fromT.color}">${ico(fromT.icon)}</div><div style="min-width:0"><div class="snm">${s.name}</div><div class="scode">${s.code} · ${s.model}</div></div></div>
              <div class="mlink"><span class="lk">${ico('fa-arrow-right-long')}</span>
                <div class="tgt-wrap"><div class="tgt-label">${ico(toT.icon)} ${toT.label}</div>${deviceSelectHtml('sel-'+step.id+'-'+s.id,s.id,step.to,mapped)}</div>
              </div>
            </div>
          </div>`;
        }).join('');
  }

  const ok=total>0&&done===total;
  return `<div class="fade-in" style="padding:26px">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:16px">
      <div style="display:flex;align-items:center;gap:13px"><div style="width:40px;height:40px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:16px;background:${fromT.bg};color:${fromT.color}">${ico(fromT.icon)}</div><div><div style="font-size:16px;font-weight:800">${fromT.plural} → ${toT.plural}</div><div style="font-size:12.5px;color:var(--ink-3);margin-top:1px">Link each ${fromT.short.toLowerCase()} to its ${toT.short.toLowerCase()}.</div></div></div>
      <span class="statchip${ok?' ok':' warn'}">${ico(ok?'fa-circle-check':'fa-circle-half-stroke')} ${done}/${total} linked</span>
    </div>
    <div style="margin-bottom:16px"><div class="guide"><div class="gi">${ico('fa-wand-magic-sparkles')}</div><div class="gt">${guidance}</div></div></div>
    <div style="margin-bottom:18px;padding:12px 14px;border:1px dashed var(--border);border-radius:12px">${renderChain([step.from,step.to])}</div>
    <div class="maplist">${rows}</div>
  </div>`;
}

/* ── Render: Review ── */
function renderReview() {
  const c=state.counts, inc=inclDisp(), kp=kpDevs(), brk=brkDevs();
  const lIds=ledIds(), tIds=tvIds();
  const lDevs=lIds.map(id=>(state.pool.LED||[]).find(d=>d.id===id)).filter(Boolean);
  const tDevs=tIds.map(id=>(state.pool.TV||[]).find(d=>d.id===id)).filter(Boolean);
  const cols=[
    {type:'TOKEN_DISPENSER',devs:inc},{type:'KEYPAD',devs:kp},
    c.LED>0&&{type:'LED',devs:lDevs}, c.BROKER>0&&{type:'BROKER',devs:brk}, c.BROKER>0&&c.TV>0&&{type:'TV',devs:tDevs},
  ].filter(Boolean);
  const sums=[
    {type:'TOKEN_DISPENSER',n:inc.length},{type:'KEYPAD',n:kp.length},
    {type:'LED',n:lDevs.length},{type:'BROKER',n:brk.length},{type:'TV',n:tDevs.length},
  ].filter(s=>c[s.type]>0||s.n>0);
  const brLabel=(WZ.branches||[]).find(b=>String(b.id)===state.brId)?.name||'';
  const ar=`<div style="display:flex;align-items:center;color:var(--ink-4);padding:0 8px">${ico('fa-arrow-right-long')}</div>`;
  const colsHtml=cols.map((col,i)=>{const ty=TYPE[col.type];return `${i>0?ar:''}<div style="display:flex;flex-direction:column;gap:8px;min-width:150px"><span style="align-self:flex-start;font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:${ty.color};background:${ty.bg};padding:4px 10px;border-radius:999px">${ty.plural}</span>${col.devs.map(d=>`<div style="display:flex;align-items:center;gap:9px;padding:10px 12px;border-radius:11px;background:${ty.bg};border:1px solid ${ty.color}22">${ico(ty.icon,'color:'+ty.color+';font-size:13px')}<div><div style="font-size:12.5px;font-weight:700">${d.name}</div><div style="font-size:10.5px;color:var(--ink-4)">${d.code}</div></div></div>`).join('')}</div>`;}).join('');
  return `<div style="padding:26px" class="fade-in">
    <div style="display:flex;align-items:center;gap:13px;margin-bottom:22px"><div style="width:40px;height:40px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:16px;background:var(--cq-primary-light);color:var(--cq-primary)">${ico('fa-clipboard-check')}</div><div><div style="font-size:16px;font-weight:800">Review &amp; save</div><div style="font-size:12.5px;color:var(--ink-3);margin-top:1px">Confirm the group before saving.</div></div></div>
    <div class="summary-grid" style="margin-top:6px;margin-bottom:22px">${sums.map(s=>{const ty=TYPE[s.type];return`<div class="sumtile"><div class="stico" style="background:${ty.bg};color:${ty.color}">${ico(ty.icon)}</div><div><div class="stn">${s.n}</div><div class="stl">${ty.plural}</div></div></div>`;}).join('')}</div>
    <div class="rev-card">
      <div class="rev-head"><div style="display:flex;align-items:center;gap:10px">${ico('fa-sitemap','color:var(--cq-primary)')}<span style="font-weight:800;font-size:14px">${state.gName||'Untitled group'}</span>${brLabel?`<span style="font-size:11.5px;color:var(--ink-4)">· ${brLabel}</span>`:''}</div><span class="statchip ok">${ico('fa-circle-check')} Ready</span></div>
      <div class="rev-body" style="overflow-x:auto"><div style="display:flex;align-items:stretch;gap:4px;min-width:fit-content">${colsHtml}</div></div>
    </div>
  </div>`;
}

/* ── Main Render ── */
function wzRender() {
  const steps = buildSteps();
  const idx = Math.min(state.cur, steps.length-1);
  const step = steps[idx];
  renderStepper();

  let bodyHtml='';
  if(step.kind==='config') bodyHtml=renderConfig();
  else if(step.kind==='map') bodyHtml=renderMapStage(step);
  else bodyHtml=renderReview();
  document.getElementById('wz-body').innerHTML=bodyHtml;

  const canNext=stepOk(step);
  const isLast=idx===steps.length-1;
  const backBtn=document.getElementById('wz-back');
  const nextBtn=document.getElementById('wz-next');
  const finBtn=document.getElementById('wz-finish');
  const hint=document.getElementById('wz-hint');

  backBtn.disabled=idx===0; backBtn.style.opacity=idx===0?'.4':'1';
  if(isLast){nextBtn.style.display='none';finBtn.style.display='';}
  else{nextBtn.style.display='';finBtn.style.display='none';}
  nextBtn.disabled=!canNext;
  hint.style.display=canNext?'none':'flex';
  hint.querySelector('.hint-msg').textContent=step.kind==='config'
    ?'Enter a group name, pick a branch and set at least 1 dispenser & keypad'
    :'Link every device shown above to continue';
}

/* ── Event Handlers ── */
function wzJump(i) { if(i<=state.cur){state.cur=i; wzRender();} }
function wzBack()  { if(state.cur>0){state.cur--; wzRender();} }
function wzNext()  { const steps=buildSteps(); if(state.cur<steps.length-1){state.cur++; wzRender();} }

function wzCount(type, delta) {
  const min=0, max=20;
  state.counts[type]=Math.max(min,Math.min(max,state.counts[type]+delta));
  wzRender();
}
function wzCountSet(type, val) {
  state.counts[type]=Math.max(0,Math.min(20,parseInt(val)||0));
  wzRender();
}

function wzSetBr(id) {
  state.brId=id; state.pool={TOKEN_DISPENSER:[],KEYPAD:[],LED:[],BROKER:[],TV:[]};
  state.asn={included:{},dispToKeypad:{},keypadToLed:{},keypadToBroker:{},brokerToTv:{}};
  loadDevices();
}
function wzSetDc(id) {
  state.dcId=id; state.pool={TOKEN_DISPENSER:[],KEYPAD:[],LED:[],BROKER:[],TV:[]};
  state.asn={included:{},dispToKeypad:{},keypadToLed:{},keypadToBroker:{},brokerToTv:{}};
  loadDevices();
}
function wzSetName(v) { state.gName=v; updateFooter(); }

function wzToggle(devId) {
  state.asn.included[devId]=!state.asn.included[devId];
  if(!state.asn.included[devId]) delete state.asn.dispToKeypad[devId];
  wzRender();
}

function wzToggleKeypad(dispId, kpId, checked) {
  if(!state.asn.dispToKeypad[dispId]) state.asn.dispToKeypad[dispId]=[];
  const arr=state.asn.dispToKeypad[dispId];
  if(checked){ if(!arr.includes(kpId)) arr.push(kpId); }
  else { state.asn.dispToKeypad[dispId]=arr.filter(id=>id!==kpId); }
  updateFooter();
  const mc=document.getElementById('mc-'+dispId);
  if(mc) mc.classList.toggle('on', state.asn.dispToKeypad[dispId].length>0);
  // re-render to refresh badges
  wzRender();
}

function wzMap(fieldId, srcId, targetType, val) {
  const fieldMap={disp_keypad:'dispToKeypad',keypad_led:'keypadToLed',keypad_broker:'keypadToBroker',broker_tv:'brokerToTv'};
  const steps=buildSteps(); const step=steps[Math.min(state.cur,steps.length-1)];
  const field=fieldMap[step.id]||'dispToKeypad';
  state.asn[field][srcId]=val;
  updateFooter();
  // update mapcard highlight
  const mc=document.getElementById('mc-'+srcId);
  if(mc){mc.classList.toggle('on',!!val);}
}

function updateFooter() {
  const steps=buildSteps(), idx=Math.min(state.cur,steps.length-1), step=steps[idx];
  const canNext=stepOk(step), isLast=idx===steps.length-1;
  document.getElementById('wz-next').disabled=!canNext;
  document.getElementById('wz-hint').style.display=canNext?'none':'flex';
}

/* ── Fetch Branch Devices ── */
function loadDevices() {
  const id=WZ.isDealerView?state.dcId:state.brId;
  if(!id){wzRender();return;}
  const url=WZ.isDealerView?`/CallQ/config/api/dealer-customer/${id}/devices/`:`/CallQ/config/api/branch/${id}/devices/`;
  state.loading=true; wzRender();
  fetch(url)
    .then(r=>r.json())
    .then(data=>{
      const g={TOKEN_DISPENSER:[],KEYPAD:[],LED:[],BROKER:[],TV:[]};
      (data.devices||[]).forEach(d=>{
        if(!g[d.device_type])g[d.device_type]=[];
        g[d.device_type].push({id:String(d.id),name:d.get_display_identifier,code:d.serial_number,model:d.device_model||'CQ Device',inGroup:!!d.in_group});
      });
      state.pool=g;
    })
    .catch(()=>{})
    .finally(()=>{state.loading=false; wzRender();});
}

/* ── Finish & Submit ── */
function wzFinish() {
  const inc=inclDisp(), kp=kpDevs(), brk=brkDevs();
  const dispIds=inc.map(d=>d.id);

  // Collect all unique keypad IDs across all dispenser→keypad arrays
  const keypIdSet=new Set();
  dispIds.forEach(dId=>{ (state.asn.dispToKeypad[dId]||[]).forEach(kId=>keypIdSet.add(kId)); });
  const keypIds=[...keypIdSet];

  const lIds=state.counts.LED>0?[...new Set(keypIds.map(id=>state.asn.keypadToLed[id]).filter(Boolean))]:[];
  const brIds=state.counts.BROKER>0?[...new Set(keypIds.map(id=>state.asn.keypadToBroker[id]).filter(Boolean))]:[];
  const tIds=(state.counts.TV>0&&state.counts.BROKER>0)?[...new Set(brIds.map(id=>state.asn.brokerToTv[id]).filter(Boolean))]:[];

  const form=document.createElement('form');
  form.method='POST'; form.action=WZ.saveUrl;
  const h=(n,v)=>{const i=document.createElement('input');i.type='hidden';i.name=n;i.value=v;form.appendChild(i);};
  h('csrfmiddlewaretoken',WZ.csrfToken); h('action','create'); h('group_name',state.gName.trim());
  if(WZ.isDealerView) h('dealer_customer_id',state.dcId); else h('branch_id',state.brId);
  h('pool_mode', state.poolMode ? 'on' : 'off');
  h('qty_dispenser',state.counts.TOKEN_DISPENSER); h('qty_keypad',state.counts.KEYPAD);
  h('qty_led',state.counts.LED); h('qty_broker',state.counts.BROKER); h('qty_tv',state.counts.TV);
  dispIds.forEach(id=>h('dispensers[]',id));
  keypIds.forEach(id=>h('keypads[]',id));
  lIds.forEach(id=>h('leds[]',id));
  brIds.forEach(id=>h('brokers[]',id));
  tIds.forEach(id=>h('tvs[]',id));
  // Send dispenser→keypad pairs for multi-keypad mapping storage
  dispIds.forEach(dId=>{
    (state.asn.dispToKeypad[dId]||[]).forEach(kId=>h('disp_keypad_map[]',`${dId}:${kId}`));
  });
  document.body.appendChild(form); form.submit();
}

/* ── Init ── */
document.addEventListener('DOMContentLoaded', function() {
  WZ = window.__WZ || {};
  if(WZ.branches&&WZ.branches[0]) state.brId=String(WZ.branches[0].id);
  wzRender();
  if(state.brId||state.dcId) loadDevices();
});
