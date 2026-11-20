import AIChat from "./AIChat.jsx";
import Assignments from "./Assignments.jsx";
import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import Dashboard from "./Dashboard.jsx";
import Threats from "./Threats.jsx";
import Lab71 from "./Lab71.jsx";
import Lab72 from "./Lab72.jsx";

const paths = {
  overview: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
  threats: <><path d="m12 3 9 16H3L12 3Z"/><path d="M12 9v4m0 3h.01"/></>,
  labs: <><path d="M5 4h14v16H5z"/><path d="M9 9h6M9 13h6M9 17h3"/></>,
  schema: <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/></>,
  working: <><path d="M4 19V9m5 10V5m5 14v-8m5 8V3"/></>,
  ai: <><path d="m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5L12 2Z"/></>,
  chevron: <path d="m9 18 6-6-6-6"/>,
};
function Icon({name,size=19}) { return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>; }
const primary = [["overview","Overview","overview"],["threats","Threat intelligence","threats"],["assignments","MongoDB labs","labs"]];
const tools = [["lab71","Schema analysis","schema"],["lab72","Working-set profiler","working"],["ai","AI assistant","ai"]];

export default function App() {
  const [tab, setTab] = useState("overview");
  const [preset, setPreset] = useState({key:0,filters:{}});
  const [toast,setToast] = useState(null);
  const [health,setHealth] = useState(null);
  const [mobileMenu,setMobileMenu] = useState(false);
  const notify = useCallback((message,kind="ok")=>{setToast({message,kind});setTimeout(()=>setToast(null),3400);},[]);
  const go = (id) => {setTab(id);setMobileMenu(false);window.scrollTo({top:0,behavior:"smooth"});};
  useEffect(()=>{let active=true;const check=()=>api("/health").then(d=>{if(active)setHealth(d)}).catch(()=>{if(active)setHealth({backend:"offline",mongodb:"unknown"})});check();const interval=setInterval(check,30000);return ()=>{active=false;clearInterval(interval);}},[]);
  const openThreats=(filters)=>{setPreset(p=>({key:p.key+1,filters}));go("threats")};
  const nav=(data)=><div className="cti-menu-items">{data.map(([id,label,icon])=><button key={id} className={`cti-menu-item ${tab===id?"selected":""}`} onClick={()=>go(id)}><Icon name={icon}/><span>{label}</span>{tab===id&&<span className="cti-menu-active"/>}</button>)}</div>;
  const label=[...primary,...tools].find(([id])=>id===tab)?.[1] || "CTI Sentinel";
  return <div className="cti-app">
    <aside className={`cti-sidebar ${mobileMenu?"show":""}`}>
      <button className="cti-logo" onClick={()=>go("overview")}><span className="cti-logo-mark">S</span><span><strong>CTI SENTINEL</strong><small>THREAT INTELLIGENCE</small></span></button>
      <div className="cti-workspace-label"><span className="cti-online-dot"/> WORKSPACE <span className="cti-workspace-version">v2.0</span></div>
      <div className="cti-nav-label">MAIN MENU</div>{nav(primary)}
      <div className="cti-nav-label secondary">ANALYSIS TOOLS</div>{nav(tools)}
      <div className="cti-sidebar-bottom"><div className="cti-instance"><span className="cti-server-indicator"/><div><b>Local development</b><small>127.0.0.1:5000</small></div></div><div className="cti-sidebar-copyright">MongoDB Lab · Chapters 7–18</div></div>
    </aside>
    {mobileMenu&&<button className="cti-mobile-scrim" aria-label="Close menu" onClick={()=>setMobileMenu(false)}/>}
    <div className="cti-main">
      <header className="cti-topbar"><div className="cti-topbar-left"><button className="cti-menu-toggle" onClick={()=>setMobileMenu(true)} aria-label="Open navigation">☰</button><span className="cti-breadcrumb">Workspace</span><Icon name="chevron" size={14}/><b>{label}</b></div><div className="cti-topbar-right"><span className="cti-environment-tag">LOCAL ENVIRONMENT</span><span className={`cti-health ${health?.backend==="online"&&health?.mongodb==="connected"?"healthy":"unhealthy"}`}><span className="cti-online-dot"/>{health===null?"Checking…":health.backend!=="online"?"Backend offline":health.mongodb==="connected"?"Systems operational":"MongoDB disconnected"}</span><span className="cti-avatar">CT</span></div></header>
      <main className="cti-content">
        {tab==="overview"&&<><div className="page-heading"><div><div className="eyebrow">OPERATIONS / COMMAND CENTER</div><h1>Threat intelligence overview</h1><p>Monitor, investigate, and classify signals across connected sources.</p></div><button className="quiet-btn" onClick={()=>go("assignments")}>Open lab workspace →</button></div><Dashboard onOpen={openThreats} onLabs={()=>go("assignments")} onAI={()=>go("ai")}/></>}
        {tab==="threats"&&<><div className="page-heading"><div><div className="eyebrow">OPERATIONS / INVESTIGATE</div><h1>Threat intelligence</h1><p>Review and classify observed indicators and incidents.</p></div></div><Threats key={preset.key} preset={preset.filters} notify={notify}/></>}
        {tab==="lab71"&&<><div className="page-heading"><div><div className="eyebrow">MONGODB / LAB 7.1</div><h1>Production schema design</h1><p>Analyze schema patterns and document sizes.</p></div></div><Lab71 notify={notify}/></>}
        {tab==="lab72"&&<><div className="page-heading"><div><div className="eyebrow">MONGODB / LAB 7.2</div><h1>Working-set profiler</h1><p>Inspect cache behavior and read workloads.</p></div></div><Lab72 notify={notify}/></>}
        {tab==="assignments"&&<Assignments onNavigate={go}/>}
        {tab==="ai"&&<AIChat/>}
      </main>
      <footer className="cti-footer"><span>CTI SENTINEL / SECURITY OPERATIONS</span><span>LAB ENVIRONMENT · NO SIMULATED SUCCESS</span></footer>
    </div>
    {toast&&<div className={"toast "+toast.kind} role="status">{toast.message}</div>}
  </div>;
}
