import { useEffect, useMemo, useState } from "react";
import { api } from "./api.js";

const INFO = {
  "1-1": ["Classify databases", "Group sample database products by family.", "Requires MONGO_LABS_URI for the isolated MongoDB lab server."],
  "1-2": ["Map application workloads", "Match ride-sharing and social analytics access patterns to data models.", "Requires MONGO_LABS_URI for the isolated MongoDB lab server."],
  "2-1": ["Check MongoDB versions", "Inspect Docker MongoDB and optionally compare Atlas.", "Requires MONGO_LABS_URI. Set MONGO_URI_ATLAS to compare both versions."],
  "2-2": ["Bookstore CRUD", "Update prices for books published before 2010.", "Requires MONGO_LABS_URI for the isolated MongoDB lab server."],
  "3-1": ["Embedded course schema", "Query schedules and student rosters with schema validation.", "Requires MONGO_LABS_URI for the isolated MongoDB lab server."],
  "3-2": ["Migrate blog comments", "Compare referenced and embedded blog documents.", "Requires MONGO_LABS_URI for the isolated MongoDB lab server."],
  "4-1": ["Product queries", "Run operator filters, pagination, and case-insensitive search.", "Requires MONGO_LABS_URI for the isolated MongoDB lab server."],
  "4-2": ["Upsert and bulk operations", "Update stock and verify repeated imports do not duplicate records.", "Requires MONGO_LABS_URI for the isolated MongoDB lab server."],
  "5-1": ["Sales analytics", "Aggregate revenue, top customers, and order sizes.", "Requires MONGO_LABS_URI for the isolated MongoDB lab server."],
  "5-2": ["Lookup joins", "Enrich orders and find products with no orders.", "Requires MONGO_LABS_URI for the isolated MongoDB lab server."],
  "6-1": ["Index design", "Compare MongoDB execution statistics before and after indexing.", "Requires MONGO_LABS_URI for the isolated MongoDB lab server."],
  "6-2": ["Index strategies", "Measure write overhead and compare covered and fetched reads.", "Requires MONGO_LABS_URI for the isolated MongoDB lab server."],
  "7-1": ["Production schema analysis", "Evaluate and redesign the CTI document model.", "Open the dedicated schema analysis workspace."],
  "7-2": ["Working-set analysis", "Measure MongoDB cache and document access patterns.", "Open the dedicated working-set profiler."],
  "8-1": ["Deploy a replica set", "Provision a three-member MongoDB replica set.", "Docker must be installed and the cluster initialized manually."],
  "8-2": ["Failover observation", "Inspect the health and election status of replica-set members.", "The dashboard performs a read-only replica-set check; failover requires a test cluster."],
  "9-1": ["Write-concern benchmark", "Measure latency for w:1, majority, and all with journaling variations.", "Requires an isolated three-member replica set; inserts 6,000 test documents."],
  "9-2": ["Network partition simulation", "Observe replica-set behavior during node isolation.", "Run only using a disposable Docker network; never disconnect a production node."],
  "10-1": ["Atomic bank transfer", "Demonstrate transactions and rollback on insufficient funds.", "Requires a MongoDB replica set at MONGO_LABS_URI."],
  "10-2": ["Concurrent inventory reservation", "Test competing transactions against a limited stock count.", "Requires a MongoDB replica set at MONGO_LABS_URI."],
  "11-1": ["Shard-key evaluation", "Compare candidate shard keys using an illustrative scoring matrix.", "Runs locally; scores are illustrative rather than measured on a sharded cluster."],
  "11-2": ["Shard distribution simulation", "Generate 10,000 sample documents and simulate hashing.", "Requires MONGO_LABS_URI for lab-only data; simulation is not real sharding."],
  "12-1": ["Authentication and RBAC", "Inspect the authenticated roles of your MongoDB connection.", "Read-only check. Real role tests require a dedicated secured instance."],
  "12-2": ["TLS connection validation", "Verify a connection to a TLS-enabled MongoDB instance.", "Configure MONGO_TLS_URI and CA for a separate test environment."],
  "13-1": ["Replica set with Docker", "Deploy authenticated MongoDB containers using Compose.", "Manual infrastructure deployment with a keyfile is required."],
  "13-2": ["Kubernetes StatefulSet", "Evaluate persistent MongoDB pods and self-healing.", "Requires a working Kubernetes cluster and kubectl."],
  "14-1": ["MongoDB metrics", "Read connection counts, operation counters, and WiredTiger metrics.", "A read-only metric snapshot is connected; continuous logging remains manual."],
  "14-2": ["Backup and restore", "Inspect backup workflows and integrity verification.", "Restore operations are deliberately never launched from an open web endpoint."],
  "15-1": ["Multi-tenant REST API", "Task CRUD with tenant isolation and rate limits.", "Standalone sample code is included; production auth/RBAC requires integration."],
  "15-2": ["Tenant migration", "Compare document-level and per-tenant isolation strategies.", "Migrations require a reviewed plan and a disposable database."],
  "16-1": ["Polyglot data modeling", "Compare MongoDB, Cassandra, and Neo4j schemas and queries.", "Runs an offline schema comparison; it does not contact Cassandra or Neo4j."],
  "16-2": ["Hybrid query service", "Combine document, wide-column, and graph lookups.", "Requires Cassandra, MongoDB and Neo4j services."],
  "17-1": ["RAG pipeline", "Document chunking, embeddings, vector retrieval, and LLM answers.", "Requires Atlas Vector Search and an embedding API."],
  "17-2": ["Vector index comparison", "Compare approximate search and exact search on synthetic vectors.", "Offline educational simulation, not an Atlas HNSW or IVF benchmark."],
  "18-1": ["Comparative capstone", "Compare multiple databases using threat intelligence workloads.", "Requires MONGO_LABS_URI. Runs four measured MongoDB workloads on synthetic data."],
  "18-2": ["Comparative report", "Summarize performance, scalability, and architecture trade-offs.", "Requires MONGO_LABS_URI. Returns Markdown with measured MongoDB timings and labeled Cassandra and Neo4j estimates."],
};

function status(a) {
  if (!a) return ["Unavailable","missing"];
  if (a.execution === "existing-ui") return ["Dedicated workspace","connected"];
  if (a.execution === "benchmark-api" || a.execution === "monitoring-api" || a.execution === "replica-inspection") return ["API connected","connected"];
  if (a.runnable && a.execution === "offline-demo") return ["Offline demo","connected"];
  if (a.runnable && a.execution === "guided-security") return ["Setup check","ready"];
  if (a.runnable) return ["Runner available","ready"];
  return ["Manual setup","manual"];
}

export default function Assignments({onNavigate}) {
  const [items,setItems] = useState([]);
  const [selected,setSelected] = useState("1-1");
  const [query,setQuery] = useState("");
  const [filter,setFilter] = useState("all");
  const [loadError,setLoadError] = useState("");
  const [running,setRunning] = useState("");
  const [results,setResults] = useState({});
  const [source,setSource] = useState({});
  const [sourceBusy,setSourceBusy] = useState("");
  const [showSource,setShowSource] = useState(false);
  useEffect(()=>{api("/assignments").then(r=>setItems(r.assignments||[])).catch(e=>setLoadError(e.message));},[]);
  const chapterItems=useMemo(()=>items,[items]);
  const visible=chapterItems.filter(a=>{
    const key=`${a.chapter}-${a.lab}`;
    const match=(`${key} ${INFO[key]?.join(" ")||""}`).toLowerCase().includes(query.toLowerCase());
    return match&&(filter==="all"||(filter==="ready"&&status(a)[1]!=="manual")||(filter==="manual"&&status(a)[1]==="manual"));
  });
  const a=chapterItems.find(x=>`${x.chapter}-${x.lab}`===selected);
  const [name,summary,requirement]=INFO[selected]||["MongoDB experiment","Experiment details",""];
  const [statusLabel,statusKind]=status(a);
  const output=results[selected];
  const ready=chapterItems.filter(x=>status(x)[1]!=="manual").length;
  const available=chapterItems.filter(x=>x.viewable).length;
  async function execute(){
    if(!a||running)return;
    const key=selected;
    if(key==="7-1"||key==="7-2") {onNavigate(key==="7-1"?"lab71":"lab72");return;}
    let path,options;
    if(key==="8-2")path="/labs/replica/status";
    else if(key==="14-1")path="/labs/14/1/metrics";
    else if(key==="9-1") {
      if(!window.confirm("Run 6,000 real writes ONLY on your isolated 3-member lab replica set?"))return;
      path="/labs/9/1/benchmark";options={method:"POST",body:{confirm:"isolated-lab"}};
    } else if(a.runnable){path=`/labs/${a.chapter}/${a.lab}/run`;options={method:"POST"};}
    else return;
    setRunning(key);setResults(old=>({...old,[key]:null}));
    try{const data=await api(path,options);setResults(old=>({...old,[key]:{data}}));}
    catch(e){setResults(old=>({...old,[key]:{error:e.message}}));}
    finally{setRunning("");}
  }
  async function loadSource(){
    if(!a)return;
    setShowSource(old=>!old);
    if(source[selected])return;
    setSourceBusy(selected);
    try{const data=await api(`/assignments/${a.chapter}/${a.lab}/source`);setSource(old=>({...old,[selected]:data}));}
    catch(e){setSource(old=>({...old,[selected]:{error:e.message}}));}
    finally{setSourceBusy("");}
  }
  const canRun=a&&(a.runnable||["7-1","7-2","8-2","9-1","14-1"].includes(selected));
  return <div className="lab-page">
    <div className="page-heading"><div><div className="eyebrow">MONGODB / EXPERIMENT WORKSPACE</div><h1>Lab control center</h1><p>Inspect source, run approved experiments, and review results from Chapters 1–18.</p></div><span className="lab-index-label">36 LAB EXPERIMENTS</span></div>
    <div className="lab-stats"><div><small>IN SCOPE</small><strong>36<span> labs</span></strong></div><div><small>SOURCE DETECTED</small><strong>{available}<span> / 36</span></strong></div><div><small>WORKSPACE / CHECK / DEMO</small><strong>{ready}<span> / 36</span></strong></div><div className="lab-stats-note">Availability ≠ runtime verification. Infrastructure labs are intentionally restricted.</div></div>
    {loadError&&<div className="notice error-notice" role="alert">Could not load lab catalog: {loadError}</div>}
    <div className="lab-workspace">
      <aside className="lab-sidebar"><div className="lab-filters"><input value={query} onChange={e=>setQuery(e.target.value)} aria-label="Search labs" placeholder="⌕  Search labs…"/><div className="lab-filter-row">{[["all","All"],["ready","Connected"],["manual","Manual"]].map(([id,label])=><button className={filter===id?"selected":""} key={id} onClick={()=>setFilter(id)}>{label}</button>)}</div></div><div className="lab-menu">{Array.from({length:18},(_,i)=>i+1).map(ch=>{
        const labs=visible.filter(a=>a.chapter===ch);if(!labs.length)return null;
        return <div key={ch} className="lab-chapter-group"><div className="lab-chapter-label">CHAPTER {String(ch).padStart(2,"0")}</div>{labs.map(item=>{const key=`${item.chapter}-${item.lab}`;const [label,kind]=status(item);return <button key={key} className={`lab-nav-item ${selected===key?"selected":""}`} onClick={()=>{setSelected(key);setShowSource(false)}}><span className="lab-nav-number">{item.chapter}.{item.lab}</span><span className="lab-nav-content"><span>{INFO[key]?.[0]||item.title}</span><small>{label}</small></span><span className={`lab-dot ${kind}`}/></button>})}</div>;
      })}{!visible.length&&<p className="small-note">No labs match your search.</p>}</div></aside>
      <section className="lab-detail"><div className="lab-detail-head"><div><div className="eyebrow">CHAPTER {a?.chapter||1} / EXPERIMENT {a?.lab||1}</div><h2>Lab {selected.replace("-",".")} — {name}</h2><p>{summary}</p></div><span className={`lab-status ${statusKind}`}>{statusLabel}</span></div>
        <div className="lab-detail-body"><div className="lab-info-block"><div className="lab-block-label">ENVIRONMENT & PREREQUISITES</div><p>{requirement}</p><p className="small-note">Source: <strong>{a?.viewable?"Included":"Not in project"}</strong>. The dashboard only runs allowlisted operations.</p></div>
          <div className="lab-actions"><button className="action-primary" disabled={!canRun||!!running} onClick={execute}>{running===selected?"Executing…":a?.execution==="existing-ui"?"Open workspace →":selected==="8-2"||selected==="14-1"?"Read metrics →":a?.execution==="guided-security"?"Check setup →":"Run experiment →"}</button><button className="quiet-btn" disabled={!a?.viewable||sourceBusy===selected} onClick={loadSource}>{sourceBusy===selected?"Loading…":showSource?"Hide source":"View source code"}</button></div>
          {!canRun&&<div className="notice">This experiment requires external services or manual setup. Its source is available to inspect; no simulated success will be shown.</div>}
          {output?.error&&<div className="notice error-notice" role="alert"><strong>Execution failed</strong><p>{output.error}</p></div>}
          {output?.data&&<div className="lab-output"><div className="lab-output-head"><span>EXECUTION OUTPUT</span><span>{output.data.passed===true?"✓ Completed":output.data.passed===false?"✕ Failed":"ℹ Result received"}</span><button onClick={()=>navigator.clipboard?.writeText(JSON.stringify(output.data,null,2))}>Copy JSON</button></div>{output.data.note&&<div className="notice">{output.data.note}</div>}<pre>{output.data.output||JSON.stringify(output.data,null,2)}</pre></div>}
          {showSource&&<div className="lab-source"><div className="lab-output-head"><span>ASSIGNMENT SOURCE</span><span>{a?.files.length||0} files</span></div>{source[selected]?.error&&<p className="error">{source[selected].error}</p>}{source[selected]?.sources?.map(f=><details key={f.file} open><summary>{f.file}</summary><pre>{f.content||f.error}</pre></details>)}</div>}
          <div className="lab-info-footer"><span>Safety: changes to replica sets, security settings and restore operations are not triggered automatically.</span><span>CTI / MONGODB</span></div>
        </div>
      </section>
    </div>
  </div>;
}
