import { useCallback, useEffect, useState } from "react";
import { api, fmtDate } from "./api.js";

const severityOrder = ["Critical", "High", "Medium", "Low"];
const verdictOrder = ["Malicious", "Suspicious", "Benign"];
const severityColors = { Critical: "#ff6077", High: "#ff9e59", Medium: "#e9bd62", Low: "#44cba4" };
const verdictColors = { Malicious: "#ff6077", Suspicious: "#e9bd62", Benign: "#40d7b8" };

function Glyph({ name, size = 20 }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "1.7", strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };
  const paths = {
    shield: <><path d="m12 2 8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4Z"/><path d="m9 12 2 2 4-4"/></>,
    alert: <><path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v4m0 3h.01"/></>,
    scan: <><path d="M4 9V4h5m6 0h5v5m0 6v5h-5m-6 0H4v-5"/><circle cx="12" cy="12" r="3"/></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/></>,
    arrow: <><path d="M5 12h14m-6-6 6 6-6 6"/></>,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.2 9A7 7 0 0 1 18 7l2 5M4 12l2 5a7 7 0 0 0 11.8-2"/></>,
    radio: <><circle cx="12" cy="12" r="2"/><path d="M7.8 7.8a6 6 0 0 0 0 8.4m8.4-8.4a6 6 0 0 1 0 8.4M4.5 4.5a11 11 0 0 0 0 15m15-15a11 11 0 0 1 0 15"/></>,
  };
  return <svg {...common}>{paths[name] || paths.layers}</svg>;
}

function MetricCard({ label, value, caption, color, icon, onClick }) {
  return <button className="soc-metric" onClick={onClick} type="button" aria-label={`Show ${label.toLowerCase()}`}>
    <div className="soc-metric-top"><span>{label}</span><span className={`soc-metric-icon ${color}`}><Glyph name={icon} size={18}/></span></div>
    <strong>{Number(value).toLocaleString()}</strong>
    <div className="soc-metric-foot"><span className={`soc-dot ${color}`}/>{caption}<span className="soc-metric-arrow">↗</span></div>
  </button>;
}

function Distribution({ title, subtitle, rows, colors, onPick }) {
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  return <section className="soc-panel soc-distribution">
    <div className="soc-panel-header"><div><h2>{title}</h2><p>{subtitle}</p></div><span className="soc-panel-chip">LIVE DATA</span></div>
    <div className="soc-stacked" aria-label={`${title} stacked distribution`}>{rows.map((row) => <button key={row.name} title={`${row.name}: ${row.value}`} aria-label={`${row.name}: ${row.value}`} onClick={() => onPick(row.name)} className="soc-stack-piece" style={{background:colors[row.name] || "#59bcca",flex:Math.max(0,row.value),display:row.value?"block":"none"}}/>)}</div>
    {total === 0 && <div className="soc-empty-track">No observations recorded</div>}
    <div className="soc-distribution-rows">{rows.map(row=><button key={row.name} type="button" onClick={()=>onPick(row.name)} className="soc-distribution-row"><span className="soc-distribution-name"><i style={{background:colors[row.name]||"#59bcca"}}/>{row.name}</span><span className="soc-distribution-bar"><span style={{width:`${total?row.value/total*100:0}%`,background:colors[row.name]||"#59bcca"}}/></span><strong>{row.value}</strong><small>{total?Math.round(row.value/total*100):0}%</small></button>)}</div>
  </section>;
}

export default function Dashboard({ onOpen, onLabs, onAI }) {
  const [stats, setStats] = useState(null);
  const [feed, setFeed] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshedAt, setRefreshedAt] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [s,t] = await Promise.all([api("/stats"),api("/threats",{params:{page:1,limit:6,sort:"newest"}})]);
      setStats(s);
      setFeed(t.items||[]);
      setRefreshedAt(new Date());
      setError("");
    } catch(e) {setError(e.message);}
    finally {setLoading(false);}
  },[]);
  useEffect(()=>{refresh();},[refresh]);

  const s = stats || {total:0,awaitingReview:0,reviewed:0,severities:{},verdicts:{},sources:[],categories:[]};
  const severityRows = severityOrder.map(name=>({name,value:s.severities?.[name]||0}));
  const verdictRows = verdictOrder.map(name=>({name,value:s.verdicts?.[name]||0}));
  const topCategories = s.categories||[];
  const dominantCategory = topCategories[0]?.name;
  const empty = !loading && !error && !s.total;

  return <div className="soc-dashboard">
    <div className="soc-heading">
      <div><div className="soc-kicker"><span className="soc-kicker-line"/> SECURITY OPERATIONS / INTELLIGENCE</div><h1>Security overview<span className="soc-heading-glow">.</span></h1><p>Actionable threat intelligence, powered by your MongoDB database.</p></div>
      <div className="soc-heading-actions"><span className="soc-data-tag"><span/> DATABASE FEED</span><button className="soc-refresh" type="button" disabled={loading} onClick={refresh}><Glyph name="refresh" size={15}/>{loading?"Refreshing…":"Refresh data"}</button></div>
    </div>
    {error && <div role="alert" className="notice error-notice">Unable to load live dashboard data: {error}. Check that Flask and MongoDB are running. <button type="button" className="quiet-btn" onClick={refresh}>Retry</button></div>}
    <div className="soc-metrics">
      <MetricCard label="TOTAL THREATS" value={s.total} caption="Indexed intelligence records" icon="scan" color="aqua" onClick={()=>onOpen({})}/>
      <MetricCard label="CRITICAL ALERTS" value={s.severities?.Critical||0} caption="Highest-priority severity" icon="alert" color="red" onClick={()=>onOpen({severity:"Critical"})}/>
      <MetricCard label="PENDING REVIEW" value={s.awaitingReview} caption="Awaiting analyst verdict" icon="shield" color="amber" onClick={()=>onOpen({reviewed:"false"})}/>
      <MetricCard label="CONFIRMED REVIEWS" value={s.reviewed} caption="Reviewed classifications" icon="layers" color="blue" onClick={()=>onOpen({reviewed:"true"})}/>
    </div>
    <div className="soc-content-grid">
      <Distribution title="Threat severity" subtitle="Distribution by classification priority" rows={severityRows} colors={severityColors} onPick={severity=>onOpen({severity})}/>
      <Distribution title="Verdict breakdown" subtitle="Current machine and analyst verdicts" rows={verdictRows} colors={verdictColors} onPick={verdict=>onOpen({verdict})}/>
    </div>
    <div className="soc-content-grid soc-secondary-grid">
      <section className="soc-panel soc-activity">
        <div className="soc-panel-header"><div><h2>Recent intelligence</h2><p>Latest recorded threat observations</p></div><button type="button" className="soc-text-link" onClick={()=>onOpen({})}>View all <Glyph name="arrow" size={14}/></button></div>
        {feed.length ? <div className="soc-threat-table-wrap"><table className="soc-threat-table"><thead><tr><th>THREAT</th><th>SEVERITY</th><th>VERDICT</th><th>OBSERVED</th></tr></thead><tbody>{feed.map((t)=><tr key={t.id} onClick={()=>onOpen({search:t.title})} tabIndex={0} onKeyDown={e=>{if(e.key==="Enter")onOpen({search:t.title});}}><td><div className="soc-threat-title">{t.title||"Untitled event"}</div><div className="soc-threat-sub">{t.source?.name||t.category||"Unattributed"}</div></td><td><span className={`soc-severity ${String(t.severity||"").toLowerCase()}`}>{t.severity||"Unknown"}</span></td><td>{t.classification?.verdict||"Unclassified"}</td><td>{fmtDate(t.createdAt)||"—"}</td></tr>)}</tbody></table></div> : <div className="soc-empty-state"><Glyph name="radio" size={28}/><strong>No recorded threats</strong><p>{empty?"Your database has no threat records yet. Add records from the Threat intelligence tab.":"No recent threats available."}</p></div>}
      </section>
      <section className="soc-panel soc-intel-panel"><div className="soc-panel-header"><div><h2>Intelligence sources</h2><p>Top sources by submitted records</p></div><span className="soc-panel-chip">MONGODB</span></div>
        <div className="soc-sources">{(s.sources||[]).length ? s.sources.map((source,i)=><div className="soc-source-item" key={`${source.name}-${i}`}><span className="soc-source-avatar">{(source.name||"?").slice(0,2).toUpperCase()}</span><div><strong>{source.name||"Unknown"}</strong><small>Reliability: {source.reliability??"n/a"}%</small></div><span className="soc-source-count">{source.n}</span></div>) : <div className="soc-empty-state compact"><strong>No source data yet</strong><p>Sources appear after threat ingestion.</p></div>}</div>
        {dominantCategory&&<div className="soc-insight"><span className="soc-insight-label">MOST OBSERVED CATEGORY</span><strong>{dominantCategory}</strong><span>{topCategories[0].n} records</span></div>}
      </section>
    </div>
    <div className="soc-quick-actions"><div><span className="soc-kicker">NEXT ACTION</span><h2>Continue your investigation</h2><p>Open the MongoDB lab environment or ask the AI assistant to explain a finding.</p></div><div className="soc-quick-buttons"><button type="button" onClick={onLabs}>Open MongoDB labs <Glyph name="arrow" size={16}/></button><button type="button" onClick={onAI}>Open AI assistant <Glyph name="arrow" size={16}/></button></div></div>
    <div className="soc-last-sync">{refreshedAt?`Data refreshed ${refreshedAt.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}`:"Waiting for live data"} · All figures reflect actual API responses; no fabricated activity</div>
  </div>;
}
