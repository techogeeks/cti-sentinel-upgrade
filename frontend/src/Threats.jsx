import { useEffect, useRef, useState } from "react";
import { api, fmtDate } from "./api.js";

const SEVERITIES = ["Critical", "High", "Medium", "Low"];
const VERDICTS = ["Malicious", "Suspicious", "Benign"];
const verdictClass = (v) => "pill v-" + (v || "none").toLowerCase();

function useDebounced(value, ms = 300) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export default function Threats({ preset, notify }) {
  const [f, setF] = useState({ search: "", mode: "regex", severity: "", category: "", verdict: "", reviewed: "", source: "", sort: "newest", ...preset });
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0, pages: 1 });
  const [meta, setMeta] = useState({ categories: [], sources: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [adding, setAdding] = useState(false);
  const [tick, setTick] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const searchRef = useRef(null);
  const search = useDebounced(f.search);

  const set = (key, value) => {
    setF((old) => ({ ...old, [key]: value }));
    setPage(1);
  };
  const toggle = (key, value) => set(key, f[key] === value ? "" : value);

  useEffect(() => { api("/meta").then(setMeta).catch((e) => setError(e.message)); }, []);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api("/threats", { params: { ...f, search, page, limit: 12 } })
      .then((d) => { if (alive) { setData(d); setError(""); } })
      .catch((e) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, f.mode, f.severity, f.category, f.verdict, f.reviewed, f.source, f.sort, page, tick]);

  // Keyboard: "/" focuses search, Escape closes the panel.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
        e.preventDefault();
        searchRef.current?.focus();
      }
      if (e.key === "Escape") { setSelected(null); setAdding(false); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const syncGcve = async () => {
    setSyncing(true);
    try {
      const r = await api("/monitor/sync-gcve", { method: "POST" });
      if (r.errors.length) notify("Could not read the GCVE feed: " + r.errors[0], "err");
      else notify(r.saved ? `Added ${r.saved} new vulnerabilit${r.saved === 1 ? "y" : "ies"} from GCVE` : "Already up to date with the GCVE feed");
      if (r.saved) setTick((x) => x + 1);
    } catch (e) { notify(e.message, "err"); }
    setSyncing(false);
  };

  const activeFilters = ["severity", "category", "verdict", "reviewed", "source"].filter((k) => f[k]);
  const clear = () => { setF((o) => ({ ...o, severity: "", category: "", verdict: "", reviewed: "", source: "", search: "" })); setPage(1); };

  const saved = (updated) => {
    setData((d) => ({ ...d, items: d.items.map((t) => (t.id === updated.id ? updated : t)) }));
    setSelected(updated);
  };

  return (
    <div className="stack">
      <div className="toolbar">
        <div className="search">
          <input ref={searchRef} value={f.search} onChange={(e) => set("search", e.target.value)}
            placeholder="Search titles, descriptions, tags or an indicator (press / to focus)" aria-label="Search threats" />
          <div className="seg small" role="group" aria-label="Search mode">
            <button className={f.mode === "regex" ? "on" : ""} onClick={() => set("mode", "regex")} title="Partial matches, e.g. 'ransom'">Contains</button>
            <button className={f.mode === "text" ? "on" : ""} onClick={() => set("mode", "text")} title="MongoDB text index: whole words, ranked by relevance">Text index</button>
          </div>
        </div>
        <button onClick={syncGcve} disabled={syncing} title="Reads the recent feed from db.gcve.eu and adds vulnerabilities not yet in the platform">{syncing ? "Syncing…" : "Sync GCVE feed"}</button>
        <button className="primary" onClick={() => setAdding(true)}>Add threat</button>
      </div>

      <div className="filters">
        <div className="chips" aria-label="Severity">
          {SEVERITIES.map((s) => (
            <button key={s} className={"chip sev-" + s.toLowerCase() + (f.severity === s ? " on" : "")} onClick={() => toggle("severity", s)}>{s}</button>
          ))}
        </div>
        <div className="chips" aria-label="Verdict">
          {VERDICTS.map((v) => (
            <button key={v} className={"chip " + verdictClass(v) + (f.verdict === v ? " on" : "")} onClick={() => toggle("verdict", v)}>{v}</button>
          ))}
          <button className={"chip" + (f.reviewed === "false" ? " on" : "")} onClick={() => toggle("reviewed", "false")}>Unreviewed</button>
        </div>
        <select value={f.category} onChange={(e) => set("category", e.target.value)} aria-label="Category">
          <option value="">All categories</option>
          {meta.categories.map((c) => <option key={c}>{c}</option>)}
        </select>
        <select value={f.source} onChange={(e) => set("source", e.target.value)} aria-label="Source">
          <option value="">All sources</option>
          {meta.sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <select value={f.mode === "text" && f.search ? "relevance" : f.sort} onChange={(e) => set("sort", e.target.value)} disabled={f.mode === "text" && !!f.search} aria-label="Sort">
          <option value="newest">Newest first</option>
          <option value="severity">Most severe first</option>
          <option value="confidence">Highest confidence</option>
          <option value="relevance">Best match</option>
        </select>
        {(activeFilters.length > 0 || f.search) && <button className="link" onClick={clear}>Clear all</button>}
      </div>

      {error && <p className="error">{error}</p>}
      <p className="muted count">{loading ? "Searching…" : `${data.total} threat${data.total === 1 ? "" : "s"} found`}</p>

      <div className={"list" + (loading ? " busy" : "")}>
        {data.items.map((t) => (
          <button key={t.id} className={"row sev-" + t.severity.toLowerCase() + (selected?.id === t.id ? " active" : "")} onClick={() => setSelected(t)}>
            <span className="row-main">
              <span className="row-title">{t.title}</span>
              <span className="row-meta">{t.category} from {t.source?.name || "unknown source"}, {fmtDate(t.createdAt)}</span>
            </span>
            <span className="row-side">
              <span className="muted">{t.indicators.length} IOC{t.indicators.length === 1 ? "" : "s"}</span>
              <span className={verdictClass(t.classification.verdict)}>{t.classification.verdict}{t.classification.reviewed ? "" : "?"}</span>
            </span>
          </button>
        ))}
        {!loading && data.items.length === 0 && (
          <div className="empty"><p>No threats match these filters.</p><button className="link" onClick={clear}>Clear filters</button></div>
        )}
      </div>

      {data.pages > 1 && (
        <div className="pager">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span>Page {page} of {data.pages}</span>
          <button disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      )}

      {selected && <Drawer key={selected.id} threat={selected} onClose={() => setSelected(null)} onSaved={saved} notify={notify} />}
      {adding && <AddThreat categories={meta.categories} sources={meta.sources} onClose={() => setAdding(false)}
        onCreated={() => { setAdding(false); setTick((x) => x + 1); notify("Threat added and auto-classified"); }} />}
    </div>
  );
}

function Drawer({ threat, onClose, onSaved, notify }) {
  const c = threat.classification;
  const [verdict, setVerdict] = useState(c.verdict);
  const [confidence, setConfidence] = useState(c.confidence ?? 50);
  const [note, setNote] = useState("");
  const [suggestion, setSuggestion] = useState(null);
  const [busy, setBusy] = useState(false);
  const dirty = verdict !== c.verdict || confidence !== c.confidence || note.trim() !== "";

  const getSuggestion = async () => {
    try { setSuggestion(await api(`/threats/${threat.id}/suggest`, { method: "POST" })); }
    catch (e) { notify(e.message, "err"); }
  };
  const apply = () => { setVerdict(suggestion.verdict); setConfidence(suggestion.confidence); };
  const save = async () => {
    setBusy(true);
    try {
      const updated = await api(`/threats/${threat.id}/classify`, { method: "PATCH", body: { verdict, confidence, note } });
      onSaved(updated);
      notify(`Classified as ${verdict}`);
    } catch (e) { notify(e.message, "err"); }
    setBusy(false);
  };
  const copy = (value) => navigator.clipboard?.writeText(value).then(() => notify("Copied " + value.slice(0, 40)));

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" aria-label="Threat details">
        <button className="close" onClick={onClose} aria-label="Close">Close</button>
        <span className={"sev-tag sev-" + threat.severity.toLowerCase()}>{threat.severity}</span>
        <h2>{threat.title}</h2>
        <p>{threat.description}</p>
        <p className="tags">{threat.tags.map((t) => <span key={t} className="tag">{t}</span>)}</p>

        <h4>Source</h4>
        {threat.source ? (
          <p>
            <a href={threat.source.website} target="_blank" rel="noreferrer">{threat.source.name}</a>{" "}
            <span className="muted">{threat.source.type}, tier {threat.source.tier}</span>{" "}
            <span className="meter"><span style={{ width: `${threat.source.reliability}%` }} /></span> {threat.source.reliability}
          </p>
        ) : <p className="muted">No source recorded.</p>}
        {threat.referenceUrl && <p><strong>Reference:</strong> <a href={threat.referenceUrl} target="_blank" rel="noreferrer">{threat.referenceUrl}</a></p>}
        {threat.affected && <p><strong>Affected:</strong> <span className="muted">{threat.affected}</span></p>}
        {threat.actor && <p><strong>Actor:</strong> {threat.actor.name} <span className="muted">({threat.actor.motivation})</span></p>}

        <h4>Indicators</h4>
        {threat.indicators.length === 0 ? <p className="muted">None recorded.</p> : (
          <ul className="iocs">
            {threat.indicators.map((i) => (
              <li key={i.value}><span className="ioc-type">{i.type}</span><code>{i.value}</code>
                <button className="link" onClick={() => copy(i.value)}>Copy</button></li>
            ))}
          </ul>
        )}

        <h4>Classification {c.reviewed ? "" : <span className="muted">(automatic, not reviewed)</span>}</h4>
        <div className="seg" role="group" aria-label="Verdict">
          {VERDICTS.map((v) => <button key={v} className={(verdict === v ? "on " : "") + verdictClass(v)} onClick={() => setVerdict(v)}>{v}</button>)}
        </div>
        <label className="range">Confidence <strong>{confidence}%</strong>
          <input type="range" min="0" max="100" value={confidence} onChange={(e) => setConfidence(+e.target.value)} />
        </label>
        <textarea rows="2" placeholder="Reason for this verdict (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
        <div className="actions">
          <button onClick={getSuggestion}>Suggest verdict</button>
          <button className="primary" disabled={busy || !dirty && c.reviewed} onClick={save}>{busy ? "Saving…" : "Save classification"}</button>
        </div>

        {suggestion && (
          <div className="suggest">
            <p><span className={verdictClass(suggestion.verdict)}>{suggestion.verdict}</span> at {suggestion.confidence}% confidence (score {suggestion.score})</p>
            <ul>{suggestion.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
            <button className="link" onClick={apply}>Use this suggestion</button>
          </div>
        )}

        {c.history?.length > 0 && (
          <>
            <h4>History</h4>
            <ul className="history">
              {[...c.history].reverse().map((h, i) => (
                <li key={i}><span className={verdictClass(h.verdict)}>{h.verdict}</span> {h.confidence}% on {fmtDate(h.at)}{h.note ? `: ${h.note}` : ""}</li>
              ))}
            </ul>
          </>
        )}
      </aside>
    </>
  );
}

function AddThreat({ categories, sources, onClose, onCreated }) {
  const [form, setForm] = useState({ title: "", description: "", severity: "Medium", category: "", source: "", tags: "", indicators: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const up = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/threats", { method: "POST", body: { ...form, indicators: form.indicators.split("\n").map((s) => s.trim()).filter(Boolean) } });
      onCreated();
    } catch (err) { setError(err.message); setBusy(false); }
  };

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <form className="modal" onSubmit={submit}>
        <h2>Add a threat report</h2>
        <label>Title<input value={form.title} onChange={up("title")} required /></label>
        <label>Description<textarea rows="3" value={form.description} onChange={up("description")} required /></label>
        <div className="two">
          <label>Severity<select value={form.severity} onChange={up("severity")}>{SEVERITIES.map((s) => <option key={s}>{s}</option>)}</select></label>
          <label>Category<input list="cats" value={form.category} onChange={up("category")} required /></label>
        </div>
        <datalist id="cats">{categories.map((c) => <option key={c} value={c} />)}</datalist>
        <label>Source<input list="srcs" value={form.source} onChange={up("source")} placeholder="Existing or new source" /></label>
        <datalist id="srcs">{sources.map((s) => <option key={s.id} value={s.name} />)}</datalist>
        <label>Tags (comma separated)<input value={form.tags} onChange={up("tags")} /></label>
        <label>Indicators (one per line: IP, domain, URL, hash or email)<textarea rows="3" value={form.indicators} onChange={up("indicators")} /></label>
        {error && <p className="error">{error}</p>}
        <div className="actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button className="primary" disabled={busy}>{busy ? "Adding…" : "Add threat"}</button>
        </div>
      </form>
    </>
  );
}
