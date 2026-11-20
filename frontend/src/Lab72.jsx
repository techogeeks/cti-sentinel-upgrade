import { useEffect, useRef, useState } from "react";
import { api, fmtBytes } from "./api.js";

function Sparkline({ values }) {
  const pts = values.filter((v) => v != null);
  if (pts.length < 2) return <p className="muted">Collecting readings…</p>;
  const min = Math.min(...pts, 90), max = 100;
  const d = pts.map((v, i) => `${(i / (pts.length - 1)) * 300},${50 - ((v - min) / (max - min || 1)) * 46 - 2}`).join(" ");
  return <svg viewBox="0 0 300 50" className="spark" role="img" aria-label="Hit ratio over time"><polyline points={d} fill="none" stroke="var(--accent)" strokeWidth="2" /></svg>;
}

const ratio = (prev, cur) => {
  const req = cur.pagesRequested - prev.pagesRequested, miss = cur.pagesRead - prev.pagesRead;
  return req > 0 ? +((1 - miss / req) * 100).toFixed(2) : null;
};

export default function Lab72({ notify }) {
  const [count, setCount] = useState(100000);
  const [job, setJob] = useState(null);
  const [snap, setSnap] = useState(null);
  const [reads, setReads] = useState(null);
  const [readN, setReadN] = useState(5000);
  const [busy, setBusy] = useState("");
  const [live, setLive] = useState(false);
  const [series, setSeries] = useState([]);
  const [scan, setScan] = useState(null);
  const prev = useRef(null);

  const refresh = () => api("/lab72/metrics").then(setSnap).catch((e) => notify(e.message, "err"));
  useEffect(() => { refresh(); api("/lab72/load/status").then(setJob).catch(() => {}); }, []);

  // Poll the loader while it runs.
  useEffect(() => {
    if (!job?.running) return;
    const t = setInterval(async () => {
      const s = await api("/lab72/load/status");
      setJob(s);
      if (!s.running) { clearInterval(t); s.error ? notify(s.error, "err") : notify("Documents loaded"); refresh(); }
    }, 1000);
    return () => clearInterval(t);
  }, [job?.running]);

  // Live monitor: reads the cache counters every 10 seconds (same as labs/monitor.py).
  useEffect(() => {
    if (!live) { prev.current = null; return; }
    const tick = async () => {
      try {
        const cur = await api("/monitor/cache");
        if (prev.current) setSeries((s) => [...s.slice(-29), { t: new Date().toLocaleTimeString(), hit: ratio(prev.current, cur), used: cur.usedPercent }]);
        prev.current = cur;
        setSnap(cur);
      } catch (e) { notify(e.message, "err"); setLive(false); }
    };
    tick();
    const t = setInterval(tick, 10000);
    return () => clearInterval(t);
  }, [live]);

  const start = async () => {
    try { setJob(await api("/lab72/load", { method: "POST", body: { count } })); }
    catch (e) { notify(e.message, "err"); }
  };
  const runReads = async () => {
    setBusy("reads");
    try { setReads(await api("/lab72/random-reads", { method: "POST", body: { reads: readN } })); refresh(); }
    catch (e) { notify(e.message, "err"); }
    setBusy("");
  };
  const doScan = async () => {
    setBusy("scan");
    try { setScan(await api("/monitor/new-reports")); } catch (e) { notify(e.message, "err"); }
    setBusy("");
  };
  const ingest = async () => {
    try { const r = await api("/monitor/ingest", { method: "POST" }); notify(`Saved ${r.saved} new report(s)`); doScan(); }
    catch (e) { notify(e.message, "err"); }
  };

  const pct = job?.total ? Math.round((job.loaded / job.total) * 100) : 0;

  return (
    <div className="stack">
      <section className="lead">
        <div>
          <h1>Lab 7.2: does the working set fit in the cache?</h1>
          <p className="muted">Load about 2 KB documents, read the WiredTiger cache counters, then read at random and watch the hit ratio.</p>
        </div>
      </section>

      <section className="panel">
        <h3>1. Insert test documents</h3>
        <div className="actions left">
          <select value={count} onChange={(e) => setCount(+e.target.value)} disabled={job?.running} aria-label="Number of documents">
            <option value={10000}>10,000 documents</option>
            <option value={100000}>100,000 documents (lab requirement)</option>
          </select>
          <button className="primary" onClick={start} disabled={job?.running}>{job?.running ? "Loading…" : "Insert documents"}</button>
        </div>
        {job?.total > 0 && (
          <>
            <div className="progress"><span style={{ width: `${pct}%` }} /></div>
            <p className="muted">
              {job.loaded.toLocaleString()} of {job.total.toLocaleString()} inserted
              {job.result && `. Finished in ${job.result.seconds}s, average ${job.result.avgDocBytes} bytes per document.`}
            </p>
          </>
        )}
      </section>

      <section className="panel">
        <h3>2. WiredTiger cache (serverStatus)</h3>
        {snap && (
          <div className="facts">
            <div><span>Cache size</span><strong>{fmtBytes(snap.maxBytes)}</strong></div>
            <div><span>In cache now</span><strong>{fmtBytes(snap.usedBytes)} ({snap.usedPercent}%)</strong></div>
            <div><span>Dirty bytes</span><strong>{fmtBytes(snap.dirtyBytes)}</strong></div>
            <div><span>Collection data cached</span><strong>{snap.collectionCachedPercent ?? "n/a"}%</strong></div>
            <div><span>Hit ratio since start</span><strong>{snap.hitRatio ?? "n/a"}%</strong></div>
          </div>
        )}
        <button onClick={refresh}>Refresh</button>
      </section>

      <section className="panel">
        <h3>3. Random reads across the whole collection</h3>
        <div className="actions left">
          <select value={readN} onChange={(e) => setReadN(+e.target.value)} aria-label="Number of reads">
            <option value={2000}>2,000 reads</option><option value={5000}>5,000 reads</option><option value={20000}>20,000 reads</option>
          </select>
          <button className="primary" onClick={runReads} disabled={busy === "reads"}>{busy === "reads" ? "Reading…" : "Run random reads"}</button>
        </div>
        {reads && (
          <>
            <div className="scroll">
              <table className="table">
                <thead><tr><th>Reads</th><th>Time per read</th><th>Hit ratio (this interval)</th><th>Hit ratio (cumulative)</th><th>Cache used</th></tr></thead>
                <tbody>
                  {reads.points.map((p) => (
                    <tr key={p.reads}><td>{p.reads.toLocaleString()}</td><td>{p.msPerRead} ms</td><td>{p.intervalHitRatio ?? "n/a"}%</td><td>{p.cumulativeHitRatio ?? "n/a"}%</td><td>{p.cacheUsedPercent}%</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted">
              If the data set fits in the cache the ratio stays near 100%. To see it fall, restart mongod with a small cache, for example
              <code> mongod --wiredTigerCacheSizeGB 0.25</code>, and run the reads again.
            </p>
          </>
        )}
      </section>

      <section className="panel">
        <h3>4. Live cache monitor</h3>
        <div className="actions left">
          <button className={live ? "primary" : ""} onClick={() => setLive(!live)}>{live ? "Stop monitoring" : "Start monitoring (every 10 s)"}</button>
          <span className="muted">The same readings are printed by <code>python -m labs.monitor</code>.</span>
        </div>
        <Sparkline values={series.map((s) => s.hit)} />
        {series.length > 0 && (
          <p className="muted">Latest reading at {series[series.length - 1].t}: hit ratio {series[series.length - 1].hit ?? "n/a"}%, cache used {series[series.length - 1].used}%.</p>
        )}
      </section>

      <section className="panel">
        <h3>5. Find newer threat reports</h3>
        <p>Browses the awesome-annual-security-reports list and ctidigest.com, and lists links that are not in the database yet.</p>
        <div className="actions left">
          <button onClick={doScan} disabled={busy === "scan"}>{busy === "scan" ? "Scanning…" : "Scan for new reports"}</button>
          {scan?.newCount > 0 && <button className="primary" onClick={ingest}>Save {scan.newCount} new report(s)</button>}
        </div>
        {scan && (
          <>
            <p className="muted">{scan.linksFound} links found, {scan.newCount} not saved yet, {scan.catalogSize} already in the catalogue.</p>
            {scan.errors.map((e) => <p key={e} className="error">Could not read {e}</p>)}
            <ul className="found">
              {scan.new.slice(0, 15).map((r) => (
                <li key={r.url}><a href={r.url} target="_blank" rel="noreferrer">{r.title}</a> <span className="muted">{r.host}{r.year ? `, ${r.year}` : ""}</span></li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}
