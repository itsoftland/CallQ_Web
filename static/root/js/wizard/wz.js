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
  COUNTER: {label:'Counter',plural:'Counters',short:'Counter',icon:'fa-hashtag',color:'#6366F1',bg:'#EEF2FF'},
};
const TYPE_ORDER = ['TOKEN_DISPENSER','KEYPAD','LED','BROKER','TV'];

/* ── State ── */
let WZ = window.__WZ || {};
let state = {
  brId: '',
  dcId: '',
  gName: '',
  counts: {TOKEN_DISPENSER:0, KEYPAD:0, LED:0, BROKER:0, TV:0},
  pool: {TOKEN_DISPENSER:[], KEYPAD:[], LED:[], BROKER:[], TV:[], COUNTER:[]},
  asn: {included:{}, dispBtnToKeypad:{}, dispBtnKeypadsPool:{}, keypadToLed:{}, keypadToBroker:{}, brokerToTv:{}, keypadToCounter:{}},
  // dispBtnToKeypad: { dispId: { '1': kpId, '2': kpId, ... } } — per-button keypad assignment (normal mode)
  // dispBtnKeypadsPool: { dispId: { '1': { '1': kpId, '2': kpId, ... }, '2': { ... } } } — pool mode: multiple keypads per button
  poolMode: false,
  cur: 0,
  loading: false,
};

/* ── Derived ── */
function inclDisp() { return (state.pool.TOKEN_DISPENSER||[]).filter(d=>state.asn.included[d.id]); }
function numButtons(disp) {
  const m = (disp.tokenType||'').match(/^(\d+)_BUTTON$/);
  return m ? parseInt(m[1]) : 1;
}
function kpDevs() {
  const ids = [];
  if (state.poolMode) {
    inclDisp().forEach(d => {
      const poolMap = state.asn.dispBtnKeypadsPool[d.id] || {};
      Object.values(poolMap).forEach(slotMap => {
        Object.values(slotMap).forEach(kId => {
          if (kId && !ids.includes(kId)) ids.push(kId);
        });
      });
    });
  } else {
    inclDisp().forEach(d => {
      Object.values(state.asn.dispBtnToKeypad[d.id] || {}).forEach(kId => {
        if (kId && !ids.includes(kId)) ids.push(kId);
      });
    });
  }
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
  if (state.poolMode && c.KEYPAD>0)
    steps.push({id:'keypad_counter',label:'Keypads → Counters',kind:'map',from:'KEYPAD',to:'COUNTER'});
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
  if(id==='disp_keypad') {
    if (!inc.length) return false;
    if (state.poolMode) {
      const used = [];
      for (const d of inc) {
        const nBtns = numButtons(d);
        const poolMap = state.asn.dispBtnKeypadsPool[d.id] || {};
        for (let b = 1; b <= nBtns; b++) {
          const slotMap = poolMap[String(b)] || {};
          const assigned = Object.values(slotMap).filter(Boolean);
          if (!assigned.length) return false;
          for (const kId of assigned) {
            if (used.includes(kId)) return false;
            used.push(kId);
          }
        }
      }
      return true;
    }
    const used = [];
    for (const d of inc) {
      const nBtns = numButtons(d);
      const btnMap = state.asn.dispBtnToKeypad[d.id] || {};
      for (let b = 1; b <= nBtns; b++) {
        const kId = btnMap[String(b)];
        if (!kId || used.includes(kId)) return false;
        used.push(kId);
      }
    }
    return true;
  }
  if(id==='keypad_counter') return kp.length>=1 && kp.every(k=>state.asn.keypadToCounter[k.id]);
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
  const fieldMap = {keypad_counter:'keypadToCounter',keypad_led:'keypadToLed',keypad_broker:'keypadToBroker',broker_tv:'brokerToTv'};
  const field = fieldMap[step.id];
  const guidance = {
    disp_keypad:`Choose which <b>token dispensers</b> belong to this group, then assign each <b>button</b> on the dispenser to the <b>keypad</b> it drives.`,
    keypad_counter:`Map each <b>keypad</b> directly to the <b>counter</b> it serves — pool mode bypasses the dispenser chain.`,
    keypad_led:`Tell each <b>keypad</b> which <b>LED board</b> shows its called token number.`,
    keypad_broker:`Connect each <b>keypad</b> to the <b>broker</b> that routes its calls.`,
    broker_tv:`Point each <b>broker</b> at the <b>TV display</b> that shows its live queue.`,
  }[step.id];

  let rows='', done=0, total=0;

  if(step.id==='disp_keypad'){
    const all=state.pool.TOKEN_DISPENSER||[];
    const allKp=state.pool.KEYPAD||[];
    const inc=all.filter(d=>state.asn.included[d.id]);
    const nPoolKp=state.counts.KEYPAD;

    // Collect all globally assigned keypad IDs for exclusion from other slots
    const globalUsed = {};
    if (state.poolMode) {
      inc.forEach(d => {
        const poolMap = state.asn.dispBtnKeypadsPool[d.id] || {};
        Object.entries(poolMap).forEach(([slot, slotMap]) => {
          Object.entries(slotMap).forEach(([pidx, kId]) => {
            if (kId) globalUsed[kId] = {dispId:d.id, slot, pidx};
          });
        });
      });
    } else {
      inc.forEach(d => {
        Object.entries(state.asn.dispBtnToKeypad[d.id]||{}).forEach(([slot,kId])=>{
          if(kId) globalUsed[kId] = {dispId:d.id, slot};
        });
      });
    }

    total=inc.length;
    if (state.poolMode) {
      done=inc.filter(d=>{
        const nBtns=numButtons(d);
        const poolMap=state.asn.dispBtnKeypadsPool[d.id]||{};
        for(let b=1;b<=nBtns;b++){
          const assigned=Object.values(poolMap[String(b)]||{}).filter(Boolean);
          if(!assigned.length) return false;
        }
        return true;
      }).length;
    } else {
      done=inc.filter(d=>{
        const nBtns=numButtons(d);
        const btnMap=state.asn.dispBtnToKeypad[d.id]||{};
        return Object.values(btnMap).filter(Boolean).length>=nBtns;
      }).length;
    }

    rows=all.map(d=>{
      const on=!!state.asn.included[d.id];
      const nBtns=numButtons(d);
      let linkHtml;
      if(on){
        const btnRows=[];
        if (state.poolMode) {
          const poolMap=state.asn.dispBtnKeypadsPool[d.id]||{};
          let totalFilled=0, totalSlots=nBtns;
          for(let b=1;b<=nBtns;b++){
            const slotMap=poolMap[String(b)]||{};
            const assignedInBtn=Object.values(slotMap).filter(Boolean);
            if(assignedInBtn.length) totalFilled++;
            const poolDropdowns=[];
            for(let p=1;p<=nPoolKp;p++){
              const curKpId=slotMap[String(p)]||'';
              const availKps=allKp.filter(k=>{
                const u=globalUsed[k.id];
                return !u || (u.dispId===d.id && u.slot===String(b) && u.pidx===String(p));
              });
              const opts=availKps.map(k=>`<option value="${k.id}"${k.id===curKpId?' selected':''}>${k.name} · ${k.code}</option>`).join('');
              const isFilled=!!curKpId;
              poolDropdowns.push(`<div style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:7px;background:${isFilled?'var(--cq-primary-light)':'var(--bg-2)'};border:1px solid ${isFilled?'var(--cq-primary)':'var(--border)'}">
                <span style="font-size:11px;font-weight:600;color:var(--ink-3);white-space:nowrap;min-width:62px">Keypad ${p}</span>
                <select class="select" style="height:32px;font-size:12.5px;min-width:170px" onchange="wzSetBtnKeypadsPool('${d.id}',${b},${p},this.value)">
                  <option value="">-- Select Keypad --</option>${opts}
                </select>
              </div>`);
            }
            const btnFilled=assignedInBtn.length;
            const btnBadge=btnFilled>0?`<span class="statchip ok" style="font-size:10px;margin-left:4px">${btnFilled}/${nPoolKp}</span>`:'';
            btnRows.push(`<div style="padding:10px 12px;border-radius:10px;background:var(--bg-2);border:1.5px solid ${btnFilled?'var(--cq-primary)':'var(--border)'}">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                <span style="font-size:11.5px;font-weight:700;color:var(--ink-2)">Button ${b}</span>
                <span style="color:var(--ink-4);font-size:11px">${ico('fa-arrow-right-long')}</span>
                <span style="font-size:11.5px;color:var(--ink-3)">Pool keypads</span>${btnBadge}
              </div>
              <div style="display:flex;flex-direction:column;gap:5px">${poolDropdowns.join('')}</div>
            </div>`);
          }
          const badge=totalFilled>0?`<span class="statchip ok" style="margin-left:4px">${totalFilled}/${totalSlots} mapped</span>`:'';
          linkHtml=`<span class="lk">${ico('fa-arrow-right-long')}</span><div class="tgt-wrap"><div class="tgt-label">${ico(toT.icon)} Routes to keypads ${badge}</div><div style="display:flex;flex-direction:column;gap:8px;margin-top:8px">${btnRows.join('')}</div></div>`;
        } else {
          const btnMap=state.asn.dispBtnToKeypad[d.id]||{};
          const filled=Object.values(btnMap).filter(Boolean).length;
          const badge=filled>0?`<span class="statchip ok" style="margin-left:4px">${filled}/${nBtns} mapped</span>`:'';
          for(let b=1;b<=nBtns;b++){
            const curKpId=btnMap[String(b)]||'';
            const availKps=allKp.filter(k=>{
              const u=globalUsed[k.id];
              return !u || (u.dispId===d.id && u.slot===String(b));
            });
            const opts=availKps.map(k=>`<option value="${k.id}"${k.id===curKpId?' selected':''}>${k.name} · ${k.code}</option>`).join('');
            const filled1=!!curKpId;
            btnRows.push(`<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:9px;background:${filled1?'var(--cq-primary-light)':'var(--bg-2)'};border:1.5px solid ${filled1?'var(--cq-primary)':'var(--border)'}">
              <span style="font-size:11.5px;font-weight:700;color:var(--ink-3);white-space:nowrap;min-width:54px">Button ${b}</span>
              <span style="color:var(--ink-4)">${ico('fa-arrow-right-long')}</span>
              <select class="select" style="height:36px;font-size:13px;min-width:180px" onchange="wzSetBtnKeypad('${d.id}',${b},this.value)">
                <option value="">-- Select Keypad --</option>${opts}
              </select>
            </div>`);
          }
          linkHtml=`<span class="lk">${ico('fa-arrow-right-long')}</span><div class="tgt-wrap"><div class="tgt-label">${ico(toT.icon)} Routes to keypads ${badge}</div><div style="display:flex;flex-direction:column;gap:6px;margin-top:8px">${btnRows.join('')}</div></div>`;
        }
      } else {
        linkHtml=`<span style="font-size:12.5px;color:var(--ink-4)">Not part of this group</span>`;
      }
      return `<div class="mapcard${on?' on':''}" id="mc-${d.id}">
        <div class="mrow">
          <div class="srcchip"><div class="sico" style="background:${fromT.bg};color:${fromT.color}">${ico(fromT.icon)}</div><div style="min-width:0"><div class="snm">${d.name}</div><div class="scode">${d.code} · ${d.model}${d.tokenType?` · ${d.tokenType.replace('_',' ')}`:''}</div></div></div>
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
  state.brId=id; state.pool={TOKEN_DISPENSER:[],KEYPAD:[],LED:[],BROKER:[],TV:[],COUNTER:[]};
  state.asn={included:{},dispBtnToKeypad:{},dispBtnKeypadsPool:{},keypadToLed:{},keypadToBroker:{},brokerToTv:{},keypadToCounter:{}};
  loadDevices();
}
function wzSetDc(id) {
  state.dcId=id; state.pool={TOKEN_DISPENSER:[],KEYPAD:[],LED:[],BROKER:[],TV:[],COUNTER:[]};
  state.asn={included:{},dispBtnToKeypad:{},dispBtnKeypadsPool:{},keypadToLed:{},keypadToBroker:{},brokerToTv:{},keypadToCounter:{}};
  loadDevices();
}
function wzSetName(v) { state.gName=v; updateFooter(); }

function wzToggle(devId) {
  state.asn.included[devId]=!state.asn.included[devId];
  if(!state.asn.included[devId]) {
    delete state.asn.dispBtnToKeypad[devId];
    delete state.asn.dispBtnKeypadsPool[devId];
  }
  wzRender();
}

function wzSetBtnKeypad(dispId, btnSlot, kpId) {
  if (!state.asn.dispBtnToKeypad[dispId]) state.asn.dispBtnToKeypad[dispId] = {};
  if (kpId) {
    state.asn.dispBtnToKeypad[dispId][String(btnSlot)] = kpId;
  } else {
    delete state.asn.dispBtnToKeypad[dispId][String(btnSlot)];
  }
  wzRender();
}

function wzSetBtnKeypadsPool(dispId, btnSlot, poolIdx, kpId) {
  if (!state.asn.dispBtnKeypadsPool[dispId]) state.asn.dispBtnKeypadsPool[dispId] = {};
  if (!state.asn.dispBtnKeypadsPool[dispId][String(btnSlot)]) state.asn.dispBtnKeypadsPool[dispId][String(btnSlot)] = {};
  if (kpId) {
    state.asn.dispBtnKeypadsPool[dispId][String(btnSlot)][String(poolIdx)] = kpId;
  } else {
    delete state.asn.dispBtnKeypadsPool[dispId][String(btnSlot)][String(poolIdx)];
  }
  wzRender();
}

function wzMap(fieldId, srcId, targetType, val) {
  const fieldMap={keypad_counter:'keypadToCounter',keypad_led:'keypadToLed',keypad_broker:'keypadToBroker',broker_tv:'brokerToTv'};
  const steps=buildSteps(); const step=steps[Math.min(state.cur,steps.length-1)];
  const field=fieldMap[step.id];
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
      const g={TOKEN_DISPENSER:[],KEYPAD:[],LED:[],BROKER:[],TV:[],COUNTER:state.pool.COUNTER||[]};
      (data.devices||[]).forEach(d=>{
        if(!g[d.device_type])g[d.device_type]=[];
        g[d.device_type].push({id:String(d.id),name:d.get_display_identifier,code:d.serial_number,model:d.device_model||'CQ Device',inGroup:!!d.in_group,tokenType:d.token_type||null});
      });
      state.pool=g;
    })
    .catch(()=>{})
    .finally(()=>{state.loading=false; wzRender(); loadCounters();});
}

function loadCounters() {
  // Derive company_id from the selected branch (injected into branches_json)
  const branch=(WZ.branches||[]).find(b=>String(b.id)===state.brId);
  const companyId=branch&&branch.company_id?branch.company_id:null;
  const url=companyId?`/CallQ/config/api/counters/?company_id=${companyId}`:'/CallQ/config/api/counters/';
  fetch(url)
    .then(r=>r.json())
    .then(data=>{
      state.pool.COUNTER=(data.counters||[]).map(c=>({
        id:String(c.id),
        name:c.counter_name,
        code:c.counter_name,
      }));
      wzRender();
    })
    .catch(()=>{});
}

/* ── Finish & Submit ── */
function wzFinish() {
  const inc=inclDisp(), kp=kpDevs(), brk=brkDevs();
  const dispIds=inc.map(d=>d.id);

  // Collect all unique keypad IDs across all dispenser→button→keypad assignments
  const keypIdSet=new Set();
  if (state.poolMode) {
    dispIds.forEach(dId=>{
      const poolMap=state.asn.dispBtnKeypadsPool[dId]||{};
      Object.values(poolMap).forEach(slotMap=>{ Object.values(slotMap).forEach(kId=>{if(kId)keypIdSet.add(kId);}); });
    });
  } else {
    dispIds.forEach(dId=>{ Object.values(state.asn.dispBtnToKeypad[dId]||{}).forEach(kId=>{if(kId)keypIdSet.add(kId);}); });
  }
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
  // Pool mode: keypad → counter mappings
  if (state.poolMode) {
    keypIds.forEach(kId=>{ const cId=state.asn.keypadToCounter[kId]; if(cId) h('keypad_counter_map[]',`${kId}:${cId}`); });
  }
  lIds.forEach(id=>h('leds[]',id));
  brIds.forEach(id=>h('brokers[]',id));
  tIds.forEach(id=>h('tvs[]',id));
  // Send dispenser→button→keypad triples for per-button mapping storage
  if (state.poolMode) {
    dispIds.forEach(dId=>{
      const poolMap=state.asn.dispBtnKeypadsPool[dId]||{};
      Object.entries(poolMap).forEach(([btnSlot,slotMap])=>{
        Object.values(slotMap).forEach(kId=>{ if(kId) h('disp_keypad_map[]',`${dId}:${btnSlot}:${kId}`); });
      });
    });
  } else {
    dispIds.forEach(dId=>{
      Object.entries(state.asn.dispBtnToKeypad[dId]||{}).forEach(([btnSlot,kId])=>{
        if(kId) h('disp_keypad_map[]',`${dId}:${btnSlot}:${kId}`);
      });
    });
  }
  document.body.appendChild(form); form.submit();
}

/* ── Init ── */
document.addEventListener('DOMContentLoaded', function() {
  WZ = window.__WZ || {};
  if(WZ.branches&&WZ.branches[0]) state.brId=String(WZ.branches[0].id);
  wzRender();
  if(state.brId||state.dcId) loadDevices();
});
