/* CallQ Grouping Wizard — presentational components + step logic.
   Exports to window for the app file. */
const { useState } = React;

/* ---- tiny helpers ---- */
const Ico = ({ name, style, className }) => {
  const p = (window.CQ_ICONS || {})[name] || '';
  return (
    <svg className={className} viewBox="0 0 24 24" width="1em" height="1em" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      style={{ flexShrink: 0, display: 'block', ...style }}
      dangerouslySetInnerHTML={{ __html: p }} />
  );
};
const T = (k) => window.CQ.TYPE[k];

/* The heart of the fix: build the ordered step list from device counts.
   A mapping step only exists when the device types it connects are present.
   0-count types are never added — so they can't be navigated to. */
function buildSteps(counts) {
  const steps = [{ id: 'config', label: 'Configure', kind: 'config' }];
  // Dispenser -> Keypad : needs both (always >= 1 in a valid group)
  if (counts.TOKEN_DISPENSER > 0 && counts.KEYPAD > 0)
    steps.push({ id: 'disp_keypad', label: 'Dispensers → Keypads', short: 'Keypads',
      kind: 'map', from: 'TOKEN_DISPENSER', to: 'KEYPAD' });
  // Keypad -> LED : only if LEDs configured
  if (counts.KEYPAD > 0 && counts.LED > 0)
    steps.push({ id: 'keypad_led', label: 'Keypads → LEDs', short: 'LEDs',
      kind: 'map', from: 'KEYPAD', to: 'LED' });
  // Keypad -> Broker : only if Brokers configured
  if (counts.KEYPAD > 0 && counts.BROKER > 0)
    steps.push({ id: 'keypad_broker', label: 'Keypads → Brokers', short: 'Brokers',
      kind: 'map', from: 'KEYPAD', to: 'BROKER' });
  // Broker -> TV : only if both Brokers and TVs configured
  if (counts.BROKER > 0 && counts.TV > 0)
    steps.push({ id: 'broker_tv', label: 'Brokers → TVs', short: 'TVs',
      kind: 'map', from: 'BROKER', to: 'TV' });
  steps.push({ id: 'review', label: 'Review', kind: 'review' });
  return steps;
}

/* ---------- STEPPER (3 variants) ---------- */
function Stepper({ steps, current, onJump, variant }) {
  if (variant === 'tabs') {
    return (
      <div className="tabs">
        {steps.map((s, i) => {
          const cls = i === current ? 'current' : i < current ? 'done' : '';
          return (
            <div key={s.id} className={`tab ${cls}`} onClick={() => i <= current && onJump(i)}>
              <span className="tn">{i < current ? <Ico name="fa-check" /> : i + 1}</span>
              {s.label}
            </div>
          );
        })}
      </div>
    );
  }
  if (variant === 'vertical') {
    return (
      <div className="vrail">
        {steps.map((s, i) => {
          const cls = i === current ? 'current' : i < current ? 'done' : '';
          return (
            <div key={s.id} className={`vstep ${cls}`} onClick={() => i <= current && onJump(i)}>
              <span className="vn">{i < current ? <Ico name="fa-check" /> : i + 1}</span>
              <div>
                <div className="vl">{s.label}</div>
                <div className="vsub">{s.kind === 'map' ? 'Link devices' : s.kind === 'config' ? 'Group setup' : 'Confirm & save'}</div>
              </div>
            </div>
          );
        })}
      </div>
    );
  }
  // default: adaptive rail
  return (
    <div className="rail">
      {steps.map((s, i) => {
        const cls = i === current ? 'current' : i < current ? 'done' : '';
        return (
          <React.Fragment key={s.id}>
            <div className={`rstep ${cls}`} onClick={() => i <= current && onJump(i)}>
              <span className="nodeo">{i < current ? <Ico name="fa-check" /> : i + 1}</span>
              <span className="lbl">{s.label}</span>
            </div>
            {i < steps.length - 1 && <div className={`rconn ${i < current ? 'fill' : ''}`}></div>}
          </React.Fragment>
        );
      })}
    </div>
  );
}

/* ---------- CHAIN PIPELINE (visual builder) ---------- */
function CNode({ type, count, active }) {
  const t = T(type);
  return (
    <div className={`cnode ${active ? 'active' : ''}`}>
      <div className="cic" style={{ background: t.bg, color: t.color, borderColor: active ? t.color : 'transparent' }}>
        <Ico name={t.icon} />
      </div>
      <div className="cnm">{t.short}</div>
      <div className="ccount">{count} device{count === 1 ? '' : 's'}</div>
    </div>
  );
}
const Arrow = () => <div className="carrow"><Ico name="fa-arrow-right-long" /></div>;

function ChainPipeline({ counts, activeTypes = [] }) {
  const has = (t) => counts[t] > 0;
  const on = (t) => activeTypes.includes(t);
  const branches = [];
  if (has('LED')) branches.push(['LED']);
  if (has('BROKER')) branches.push(has('TV') ? ['BROKER', 'TV'] : ['BROKER']);

  const renderBranch = (b) =>
    b.map((type, i) => (
      <React.Fragment key={type}>
        {i > 0 && <Arrow />}
        <CNode type={type} count={counts[type]} active={on(type)} />
      </React.Fragment>
    ));

  return (
    <div className="chain">
      <CNode type="TOKEN_DISPENSER" count={counts.TOKEN_DISPENSER} active={on('TOKEN_DISPENSER')} />
      <Arrow />
      <CNode type="KEYPAD" count={counts.KEYPAD} active={on('KEYPAD')} />
      {branches.length === 1 && (
        <React.Fragment><Arrow />{renderBranch(branches[0])}</React.Fragment>
      )}
      {branches.length === 2 && (
        <React.Fragment>
          <div className="carrow"><Ico name="fa-code-fork" style={{ transform: 'rotate(90deg)' }} /></div>
          <div className="cbranch">
            <div className="chain" style={{ alignItems: 'center' }}>{renderBranch(branches[0])}</div>
            <div className="chain" style={{ alignItems: 'center' }}>{renderBranch(branches[1])}</div>
          </div>
        </React.Fragment>
      )}
    </div>
  );
}

/* ---------- guidance banner ---------- */
function Guide({ children }) {
  return (
    <div className="guide">
      <div className="gi"><Ico name="fa-wand-magic-sparkles" /></div>
      <div className="gt">{children}</div>
    </div>
  );
}

/* ---------- form controls ---------- */
function Counter({ value, min = 0, max = 20, onChange }) {
  const set = (v) => onChange(Math.max(min, Math.min(max, v)));
  return (
    <div className="counter">
      <button onClick={() => set(value - 1)} aria-label="decrease"><Ico name="fa-minus" /></button>
      <input type="number" value={value} onChange={(e) => set(parseInt(e.target.value) || 0)} />
      <button onClick={() => set(value + 1)} aria-label="increase"><Ico name="fa-plus" /></button>
    </div>
  );
}

function Switch({ on, onClick }) {
  return <div className={`switch ${on ? 'on' : ''}`} onClick={onClick}><div className="knob"></div></div>;
}

/* target device dropdown — portal-based so it escapes overflow:hidden parents */
function DeviceSelect({ value, options, placeholder, onChange }) {
  const [open, setOpen] = React.useState(false);
  const [pos, setPos]   = React.useState({ top: 0, left: 0, width: 0 });
  const btnRef = React.useRef(null);
  const menuRef = React.useRef(null);

  /* Measure button position whenever dropdown opens or window scrolls/resizes */
  const measure = React.useCallback(() => {
    if (!btnRef.current) return;
    const r = btnRef.current.getBoundingClientRect();
    setPos({ top: r.bottom + 6, left: r.left, width: r.width });
  }, []);

  React.useEffect(() => {
    if (!open) return;
    measure();
    window.addEventListener('scroll', measure, true);
    window.addEventListener('resize', measure);
    return () => {
      window.removeEventListener('scroll', measure, true);
      window.removeEventListener('resize', measure);
    };
  }, [open, measure]);

  /* Close when clicking outside */
  React.useEffect(() => {
    const h = (e) => {
      if (
        btnRef.current && !btnRef.current.contains(e.target) &&
        menuRef.current && !menuRef.current.contains(e.target)
      ) setOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const sel = options.find((o) => o.id === value);

  const menu = open && ReactDOM.createPortal(
    <div
      ref={menuRef}
      className="cs-menu"
      style={{
        position: 'fixed',
        top: pos.top,
        left: pos.left,
        width: pos.width,
        zIndex: 9999,
      }}
    >
      {options.length === 0
        ? <div style={{ padding: '12px 14px', fontSize: 13, color: 'var(--ink-4)' }}>No devices available</div>
        : options.map((o) => (
          <div key={o.id} className={`cs-opt ${o.id === value ? 'on' : ''}`}
            onMouseDown={(e) => { e.preventDefault(); onChange(o.id); setOpen(false); }}>
            <div className="cs-opt-main">
              <div className="cs-opt-nm">{o.name}</div>
              <div className="cs-opt-sub">{o.code} · {o.model}</div>
            </div>
            {o.id === value && <Ico name="fa-check" style={{ fontSize: 13, color: 'var(--cq-primary)' }} />}
          </div>
        ))}
    </div>,
    document.body
  );

  return (
    <div className="cs">
      <button ref={btnRef} type="button"
        className={`cs-btn ${open ? 'open' : ''} ${sel ? 'has' : ''}`}
        onClick={() => { measure(); setOpen((o) => !o); }}>
        <span className={sel ? 'cs-val' : 'cs-ph'}>{sel ? `${sel.name} · ${sel.code}` : placeholder}</span>
        <Ico name="fa-chevron-down" className="cs-chev" style={{ fontSize: 13, color: 'var(--ink-4)' }} />
      </button>
      {menu}
    </div>
  );
}

Object.assign(window, {
  Ico, T, buildSteps, Stepper, ChainPipeline, CNode, Arrow, Guide, Counter, Switch, DeviceSelect,
});
