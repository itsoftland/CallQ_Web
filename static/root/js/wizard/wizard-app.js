/* CallQ Grouping Wizard — Django-integrated app
   Reads:  window.__WZ  (injected by mapping.html Django template)
   Uses:   Ico, T, buildSteps, Stepper, ChainPipeline, Guide, Counter, Switch, DeviceSelect
           (all exported to window by wizard-components.js) */

const {useState, useEffect, useMemo} = React;
const WZ = window.__WZ;

/* ── Type metadata (mirrors wizard-data.js TYPE block) ── */
window.CQ = {
  TYPE: {
    TOKEN_DISPENSER:{label:'Token Dispenser',plural:'Token Dispensers',short:'Dispenser',icon:'fa-ticket',color:'var(--t-disp)',bg:'var(--t-disp-bg)'},
    KEYPAD:  {label:'Keypad',plural:'Keypads',short:'Keypad',icon:'fa-keyboard',color:'var(--t-keypad)',bg:'var(--t-keypad-bg)'},
    LED:     {label:'LED Display',plural:'LEDs',short:'LED',icon:'fa-lightbulb',color:'var(--t-led)',bg:'var(--t-led-bg)'},
    BROKER:  {label:'Broker',plural:'Brokers',short:'Broker',icon:'fa-server',color:'var(--t-broker)',bg:'var(--t-broker-bg)'},
    TV:      {label:'TV Display',plural:'TVs',short:'TV',icon:'fa-tv',color:'var(--t-tv)',bg:'var(--t-tv-bg)'},
  },
};

/* ── Helpers ── */
const EMPTY_POOL = {TOKEN_DISPENSER:[],KEYPAD:[],LED:[],BROKER:[],TV:[]};
const EMPTY_ASN  = {dispToKeypad:{},included:{},keypadToLed:{},keypadToBroker:{},brokerToTv:{}};

/* ── Main App ── */
function App() {
  const [brId,  setBrId]  = useState(WZ.branches[0] ? String(WZ.branches[0].id) : '');
  const [dcId,  setDcId]  = useState('');
  const [gName, setGName] = useState('');
  const [counts,setCounts]= useState({TOKEN_DISPENSER:1,KEYPAD:1,LED:0,BROKER:0,TV:1});
  const [pool,  setPool]  = useState(EMPTY_POOL);
  const [asn,   setAsn]   = useState(EMPTY_ASN);
  const [cur,   setCur]   = useState(0);
  const [loading,setLoad] = useState(false);

  /* Load branch/customer devices whenever selection changes */
  useEffect(() => {
    const id = WZ.isDealerView ? dcId : brId;
    if (!id) return;
    const url = WZ.isDealerView
      ? `/CallQ/config/api/dealer-customer/${id}/devices/`
      : `/CallQ/config/api/branch/${id}/devices/`;
    setLoad(true);
    fetch(url)
      .then(r => r.json())
      .then(data => {
        const g = {...EMPTY_POOL};
        (data.devices || []).forEach(d => {
          if (!g[d.device_type]) g[d.device_type] = [];
          g[d.device_type].push({
            id: String(d.id),
            name: d.get_display_identifier,
            code: d.serial_number,
            model: d.device_model || 'CQ Device',
          });
        });
        setPool(g);
        setAsn(EMPTY_ASN);
      })
      .catch(()=>{})
      .finally(()=>setLoad(false));
  }, [brId, dcId]);

  /* ── Derived device sets ── */
  const byId = (type, id) => (pool[type]||[]).find(d=>d.id===id);
  const inclDisp = (pool.TOKEN_DISPENSER||[]).filter(d=>asn.included[d.id]);
  const kpIds    = [...new Set(inclDisp.map(d=>asn.dispToKeypad[d.id]).filter(Boolean))];
  const kpDevs   = kpIds.map(id=>byId('KEYPAD',id)).filter(Boolean);
  const ledIds   = [...new Set(kpDevs.map(k=>asn.keypadToLed[k.id]).filter(Boolean))];
  const brkIds   = [...new Set(kpDevs.map(k=>asn.keypadToBroker[k.id]).filter(Boolean))];
  const brkDevs  = brkIds.map(id=>byId('BROKER',id)).filter(Boolean);
  const tvIds    = [...new Set(brkDevs.map(b=>asn.brokerToTv[b.id]).filter(Boolean))];

  /* ── Steps ── */
  const steps = useMemo(()=>buildSteps(counts),[counts]);
  const idx   = Math.min(cur, steps.length-1);
  const step  = steps[idx];

  function stageOk(id) {
    if(id==='disp_keypad')   return inclDisp.length>=1 && inclDisp.every(d=>asn.dispToKeypad[d.id]);
    if(id==='keypad_led')    return kpDevs.length>=1   && kpDevs.every(k=>asn.keypadToLed[k.id]);
    if(id==='keypad_broker') return kpDevs.length>=1   && kpDevs.every(k=>asn.keypadToBroker[k.id]);
    if(id==='broker_tv')     return brkDevs.length>=1  && brkDevs.every(b=>asn.brokerToTv[b.id]);
    return true;
  }
  function stepOk(s) {
    if(s.kind==='config') return gName.trim() && (brId||dcId) && counts.TOKEN_DISPENSER>0 && counts.KEYPAD>0;
    if(s.kind==='map')    return stageOk(s.id);
    return true;
  }
  const canNext = stepOk(step);

  /* ── Mutations ── */
  const setCount  = (t,v) => setCounts(c=>({...c,[t]:v}));
  const toggleInc = id    => setAsn(a=>({...a,included:{...a.included,[id]:!a.included[id]}}));
  const setMap    = (f,k,v)=> setAsn(a=>({...a,[f]:{...a[f],[k]:v}}));
  const goNext    = ()    => { if(idx<steps.length-1) setCur(idx+1); };
  const goBack    = ()    => { if(idx>0) setCur(idx-1); };

  /* ── Finish & Save → form POST → mapping_view ── */
  function finish() {
    const dispIds = inclDisp.map(d=>d.id);
    const keypIds = [...new Set(dispIds.map(id=>asn.dispToKeypad[id]).filter(Boolean))];
    const lIds    = counts.LED>0    ? [...new Set(keypIds.map(id=>asn.keypadToLed[id]).filter(Boolean))] : [];
    const brIdsF  = counts.BROKER>0 ? [...new Set(keypIds.map(id=>asn.keypadToBroker[id]).filter(Boolean))] : [];
    const tIds    = (counts.TV>0 && counts.BROKER>0) ? [...new Set(brIdsF.map(id=>asn.brokerToTv[id]).filter(Boolean))] : [];

    const form = document.createElement('form');
    form.method='POST'; form.action=WZ.saveUrl;
    const h=(n,v)=>{const i=document.createElement('input');i.type='hidden';i.name=n;i.value=v;form.appendChild(i);};
    h('csrfmiddlewaretoken', WZ.csrfToken);
    h('action','create'); h('group_name', gName.trim());
    if(WZ.isDealerView) h('dealer_customer_id',dcId); else h('branch_id',brId);
    h('qty_dispenser',counts.TOKEN_DISPENSER); h('qty_keypad',counts.KEYPAD);
    h('qty_led',counts.LED); h('qty_broker',counts.BROKER); h('qty_tv',counts.TV);
    dispIds.forEach(id=>h('dispensers[]',id));
    keypIds.forEach(id=>h('keypads[]',id));
    lIds.forEach(id=>h('leds[]',id));
    brIdsF.forEach(id=>h('brokers[]',id));
    tIds.forEach(id=>h('tvs[]',id));
    document.body.appendChild(form); form.submit();
  }

  const propsShared = {pool,asn,toggleInc,setMap,counts,kpDevs,brkDevs,ledIds,brkIds,tvIds,stageOk};

  return (
    <div>
      {/* Page header */}
      <div className="page-head">
        <div>
          <h2>New Device Group</h2>
          <p>Link your branch devices into a working call-flow. The wizard only shows the steps your selected devices need.</p>
        </div>
        <a className="pill-link" href={WZ.listUrl}><Ico name="fa-list-check"/> Group List</a>
      </div>

      {/* Stepper */}
      <div className="card" style={{marginBottom:18,overflowX:'auto'}}>
        <Stepper steps={steps} current={idx} onJump={i=>i<=idx&&setCur(i)} variant="rail"/>
      </div>

      {/* Step body */}
      <div className="card elev fade-in" key={step.id}>
        {step.kind==='config' && (
          <ConfigStep gName={gName} setGName={setGName} counts={counts} setCount={setCount}
            brId={brId} setBrId={setBrId} dcId={dcId} setDcId={setDcId} steps={steps} loading={loading}/>
        )}
        {step.kind==='map' && (
          <div style={{padding:26}}>
            <MapStage stageId={step.id} {...propsShared}/>
          </div>
        )}
        {step.kind==='review' && (
          <ReviewStep gName={gName} counts={counts} inclDisp={inclDisp} kpDevs={kpDevs}
            ledIds={ledIds} brkDevs={brkDevs} tvIds={tvIds} pool={pool} brId={brId}/>
        )}
        {/* Footer */}
        <div className="cardfoot">
          <button className="btn btn-ghost" onClick={goBack} disabled={idx===0}
            style={idx===0?{opacity:.4,cursor:'not-allowed'}:{}}>
            <Ico name="fa-arrow-left"/> Back
          </button>
          <div style={{display:'flex',alignItems:'center',gap:16}}>
            {!canNext && (
              <span style={{fontSize:12,color:'var(--ink-4)',display:'flex',alignItems:'center',gap:6}}>
                <Ico name="fa-circle-info"/>
                {step.kind==='config'
                  ? 'Enter a group name, pick a branch and set at least 1 dispenser & keypad'
                  : 'Link every device shown above to continue'}
              </span>
            )}
            {idx===steps.length-1
              ? <button className="btn btn-success" onClick={finish}><Ico name="fa-check"/> Finish &amp; Save</button>
              : <button className="btn btn-primary" onClick={goNext} disabled={!canNext}>Continue <Ico name="fa-arrow-right"/></button>}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── CONFIG STEP ── */
function ConfigStep({gName,setGName,counts,setCount,brId,setBrId,dcId,setDcId,steps,loading}) {
  const order=['TOKEN_DISPENSER','KEYPAD','LED','BROKER','TV'];
  return (
    <div style={{padding:26}}>
      <SectionHead icon="fa-sliders" title="Group configuration" sub="Name the group and tell us how many of each device it contains."/>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:16,marginBottom:24}}>
        {WZ.isDealerView ? (
          <div className="field">
            <label>Dealer Customer <span className="req">*</span></label>
            <select className="select" value={dcId} onChange={e=>setDcId(e.target.value)}>
              <option value="">-- Select Customer --</option>
              {WZ.dealerCustomers.map(dc=><option key={dc.id} value={String(dc.id)}>{dc.name}</option>)}
            </select>
          </div>
        ) : (
          <div className="field">
            <label>Branch <span className="req">*</span></label>
            <select className="select" value={brId} onChange={e=>setBrId(e.target.value)}>
              {WZ.branches.map(b=><option key={b.id} value={String(b.id)}>{b.name}</option>)}
            </select>
          </div>
        )}
        <div className="field" style={{gridColumn:'span 2'}}>
          <label>Group name <span className="req">*</span></label>
          <input className="input" placeholder="e.g. Counter 1 Setup" value={gName} onChange={e=>setGName(e.target.value)}/>
        </div>
      </div>

      {loading && <div style={{textAlign:'center',padding:20,color:'var(--ink-3)',fontSize:13}}>⟳ Loading devices…</div>}

      <div className="field"><label>Devices in this group</label></div>
      <div className="countgrid" style={{marginBottom:22}}>
        {order.map(type=>{
          const ty=T(type); const zero=counts[type]===0; const opt=type==='LED'||type==='BROKER'||type==='TV';
          return (
            <div className={`ccard${zero&&opt?' zero':''}`} key={type}>
              <div className="chead">
                <div className="cdico" style={{background:ty.bg,color:ty.color}}><Ico name={ty.icon}/></div>
                <div><div className="ctitle">{ty.plural}</div><div className="csub">{opt?'optional':'required'}</div></div>
              </div>
              <Counter value={counts[type]} min={opt?0:1} onChange={v=>setCount(type,v)}/>
              {zero&&opt&&<div className="badge-skip"><Ico name="fa-circle-minus"/> step skipped</div>}
            </div>
          );
        })}
      </div>

      <div style={{background:'var(--bg)',borderRadius:14,padding:'16px 18px'}}>
        <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:12}}>
          <span style={{fontSize:12,fontWeight:700,color:'var(--ink-2)',textTransform:'uppercase',letterSpacing:.5}}>Your mapping flow</span>
          <span className="statchip neutral">{steps.length} steps</span>
        </div>
        <ChainPipeline counts={counts} activeTypes={[]}/>
        <div style={{marginTop:12,fontSize:12.5,color:'var(--ink-3)',display:'flex',alignItems:'center',gap:7}}>
          <Ico name="fa-circle-info" style={{color:'var(--cq-primary)'}}/>
          {counts.LED===0||counts.BROKER===0
            ? <span>{[counts.LED===0&&'LED',counts.BROKER===0&&'Broker'].filter(Boolean).join(' & ')} steps are skipped because you set their count to 0.</span>
            : <span>All device types configured — every mapping step will appear.</span>}
        </div>
      </div>
    </div>
  );
}

/* ── MAP STAGE ── */
function MapStage({stageId,pool,asn,toggleInc,setMap,kpDevs,brkDevs,counts}) {
  const cfgMap={
    disp_keypad:{from:'TOKEN_DISPENSER',to:'KEYPAD'},
    keypad_led: {from:'KEYPAD',to:'LED'},
    keypad_broker:{from:'KEYPAD',to:'BROKER'},
    broker_tv:  {from:'BROKER',to:'TV'},
  }[stageId];
  const fromT=T(cfgMap.from), toT=T(cfgMap.to);
  const targets=pool[cfgMap.to]||[];

  const guidance={
    disp_keypad:<span>Choose which <b>token dispensers</b> belong to this group, then link each to the <b>keypad</b> it drives.</span>,
    keypad_led: <span>Tell each <b>keypad</b> which <b>LED board</b> shows its called token number.</span>,
    keypad_broker:<span>Connect each <b>keypad</b> to the <b>broker</b> that routes its calls.</span>,
    broker_tv:  <span>Point each <b>broker</b> at the <b>TV display</b> that shows its live queue.</span>,
  }[stageId];

  let done=0,total=0,rows;
  if(stageId==='disp_keypad'){
    const all=pool.TOKEN_DISPENSER||[];
    const inc=all.filter(d=>asn.included[d.id]);
    total=inc.length; done=inc.filter(d=>asn.dispToKeypad[d.id]).length;
    rows=all.map(d=>{
      const on=!!asn.included[d.id];
      return (
        <div className={`mapcard${on?' on':''}`} key={d.id}>
          <div className="mrow">
            <SrcChip type="TOKEN_DISPENSER" dev={d}/>
            <div className="mlink">
              {on ? (
                <React.Fragment>
                  <span className="lk"><Ico name="fa-arrow-right-long"/></span>
                  <div className="tgt-wrap">
                    <div className="tgt-label"><Ico name={toT.icon} style={{color:toT.color}}/> Routes to keypad</div>
                    <DeviceSelect value={asn.dispToKeypad[d.id]} options={targets} placeholder="Select a keypad…"
                      onChange={v=>setMap('dispToKeypad',d.id,v)}/>
                  </div>
                </React.Fragment>
              ):<span style={{fontSize:12.5,color:'var(--ink-4)'}}>Not part of this group</span>}
            </div>
            <div className="incl-toggle">
              <span className="it-lbl">{on?'Included':'Include'}</span>
              <Switch on={on} onClick={()=>toggleInc(d.id)}/>
            </div>
          </div>
        </div>
      );
    });
  } else {
    const sources=stageId==='broker_tv'?brkDevs:kpDevs;
    const field=stageId==='keypad_led'?'keypadToLed':stageId==='keypad_broker'?'keypadToBroker':'brokerToTv';
    total=sources.length; done=sources.filter(s=>asn[field][s.id]).length;
    rows=sources.length===0
      ? <div className="empty"><Ico name="fa-diagram-project"/><div style={{fontSize:13,fontWeight:600}}>Finish the previous step first</div></div>
      : sources.map(s=>(
          <div className={`mapcard${asn[field][s.id]?' on':''}`} key={s.id}>
            <div className="mrow">
              <SrcChip type={cfgMap.from} dev={s}/>
              <div className="mlink">
                <span className="lk"><Ico name="fa-arrow-right-long"/></span>
                <div className="tgt-wrap">
                  <div className="tgt-label"><Ico name={toT.icon} style={{color:toT.color}}/> {toT.label}</div>
                  <DeviceSelect value={asn[field][s.id]} options={targets} placeholder={`Select a ${toT.short.toLowerCase()}…`}
                    onChange={v=>setMap(field,s.id,v)}/>
                </div>
              </div>
            </div>
          </div>
        ));
  }

  const ok=total>0&&done===total;
  return (
    <div className="fade-in">
      <div style={{display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:16,marginBottom:16}}>
        <SectionHead icon={fromT.icon} iconColor={fromT.color} iconBg={fromT.bg}
          title={`${fromT.plural} → ${toT.plural}`} sub={`Link each ${fromT.short.toLowerCase()} to its ${toT.short.toLowerCase()}.`} compact/>
        <span className={`statchip${ok?' ok':' warn'}`}>{ok?<Ico name="fa-circle-check"/>:<Ico name="fa-circle-half-stroke"/>}{done}/{total} linked</span>
      </div>
      <div style={{marginBottom:16}}><Guide>{guidance}</Guide></div>
      <div style={{marginBottom:18,padding:'12px 14px',border:'1px dashed var(--border)',borderRadius:12}}>
        <ChainPipeline counts={counts} activeTypes={[cfgMap.from,cfgMap.to]}/>
      </div>
      <div className="maplist">{rows}</div>
    </div>
  );
}

/* ── REVIEW STEP ── */
function ReviewStep({gName,counts,inclDisp,kpDevs,ledIds,brkDevs,tvIds,pool,brId}) {
  const lDevs=ledIds.map(id=>(pool.LED||[]).find(d=>d.id===id)).filter(Boolean);
  const tDevs=tvIds.map(id=>(pool.TV||[]).find(d=>d.id===id)).filter(Boolean);
  const cols=[
    {type:'TOKEN_DISPENSER',devs:inclDisp},
    {type:'KEYPAD',devs:kpDevs},
    counts.LED>0&&{type:'LED',devs:lDevs},
    counts.BROKER>0&&{type:'BROKER',devs:brkDevs},
    counts.BROKER>0&&counts.TV>0&&{type:'TV',devs:tDevs},
  ].filter(Boolean);
  const sums=[
    {type:'TOKEN_DISPENSER',n:inclDisp.length},{type:'KEYPAD',n:kpDevs.length},
    {type:'LED',n:lDevs.length},{type:'BROKER',n:brkDevs.length},{type:'TV',n:tDevs.length},
  ].filter(s=>counts[s.type]>0||s.n>0);
  const branchLabel = WZ.branches.find(b=>String(b.id)===brId)?.name || '';
  return (
    <div style={{padding:26}} className="fade-in">
      <SectionHead icon="fa-clipboard-check" title="Review & save" sub="Confirm the group before saving. This is exactly what will be written."/>
      <div className="summary-grid" style={{marginTop:6,marginBottom:22}}>
        {sums.map(s=>{const ty=T(s.type);return(
          <div className="sumtile" key={s.type}>
            <div className="stico" style={{background:ty.bg,color:ty.color}}><Ico name={ty.icon}/></div>
            <div><div className="stn">{s.n}</div><div className="stl">{ty.plural}</div></div>
          </div>
        );})}
      </div>
      <div className="rev-card">
        <div className="rev-head">
          <div style={{display:'flex',alignItems:'center',gap:10}}>
            <Ico name="fa-sitemap" style={{color:'var(--cq-primary)'}}/>
            <span style={{fontWeight:800,fontSize:14}}>{gName||'Untitled group'}</span>
            {branchLabel&&<span style={{fontSize:11.5,color:'var(--ink-4)'}}>· {branchLabel}</span>}
          </div>
          <span className="statchip ok"><Ico name="fa-circle-check"/> Ready</span>
        </div>
        <div className="rev-body" style={{overflowX:'auto'}}>
          <div style={{display:'flex',alignItems:'stretch',gap:4,minWidth:'fit-content'}}>
            {cols.map((c,i)=>{const ty=T(c.type);return(
              <React.Fragment key={c.type}>
                {i>0&&<div style={{display:'flex',alignItems:'center',color:'var(--ink-4)',padding:'0 8px'}}><Ico name="fa-arrow-right-long"/></div>}
                <div style={{display:'flex',flexDirection:'column',gap:8,minWidth:150}}>
                  <span style={{alignSelf:'flex-start',fontSize:10.5,fontWeight:700,textTransform:'uppercase',letterSpacing:.5,color:ty.color,background:ty.bg,padding:'4px 10px',borderRadius:999}}>{ty.plural}</span>
                  {c.devs.map(d=>(
                    <div key={d.id} style={{display:'flex',alignItems:'center',gap:9,padding:'10px 12px',borderRadius:11,background:ty.bg,border:`1px solid ${ty.color}22`}}>
                      <Ico name={ty.icon} style={{color:ty.color,fontSize:13}}/>
                      <div><div style={{fontSize:12.5,fontWeight:700}}>{d.name}</div><div style={{fontSize:10.5,color:'var(--ink-4)'}}>{d.code}</div></div>
                    </div>
                  ))}
                </div>
              </React.Fragment>
            );})}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Shared sub-components ── */
function SectionHead({icon,title,sub,iconColor,iconBg,compact}) {
  return (
    <div style={{display:'flex',alignItems:'center',gap:13,marginBottom:compact?0:22}}>
      <div style={{width:40,height:40,borderRadius:11,display:'flex',alignItems:'center',justifyContent:'center',fontSize:16,background:iconBg||'var(--cq-primary-light)',color:iconColor||'var(--cq-primary)',flexShrink:0}}><Ico name={icon}/></div>
      <div><div style={{fontSize:16,fontWeight:800,letterSpacing:'-.2px'}}>{title}</div><div style={{fontSize:12.5,color:'var(--ink-3)',marginTop:1}}>{sub}</div></div>
    </div>
  );
}

function SrcChip({type,dev}) {
  const ty=T(type);
  return (
    <div className="srcchip">
      <div className="sico" style={{background:ty.bg,color:ty.color}}><Ico name={ty.icon}/></div>
      <div style={{minWidth:0}}>
        <div className="snm">{dev.name}</div>
        <div className="scode">{dev.code} · {dev.model}</div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('wz-root')).render(<App/>);
