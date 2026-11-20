import { useEffect, useState } from "react";
import { api, fmtBytes } from "./api.js";

export default function Lab71({ notify }) {
  const [schema, setSchema] = useState(null);
  const [sizes, setSizes] = useState(null);
  const [bench, setBench] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = () => {
    api("/lab71/schema").then((d) => setSchema(d.relationships)).catch((e) => setError(e.message));
    api("/lab71/sizes").then(setSizes).catch((e) => setError(e.message));
  };
  useEffect(load, []);

  const run = async (label, fn) => {
    setBusy(label);
    try { await fn(); } catch (e) { notify(e.message, "err"); }
    setBusy("");
  };
  const rebuild = () => run("build", async () => {
    const r = await api("/lab71/build-embedded", { method: "POST" });
    notify(`threats_embedded rebuilt with ${r.documents} documents`);
    load();
  });
  const benchmark = () => run("bench", async () => setBench(await api("/lab71/benchmark", { params: { runs: 30 } })));

  if (error) return <p className="error">{error}</p>;
  if (!schema || !sizes) return <p className="muted">Analysing the schema…</p>;
  const maxMs = bench ? Math.max(...Object.values(bench.reads).map((r) => r.medianMs)) : 1;

  return (
    <div className="stack">
      <section className="lead">
        <div>
          <h1>Lab 7.1: how the threat schema is modelled</h1>
          <p className="muted">Each relationship is either embedded in the threat document or referenced by id. Open a row to see why, and what the alternative would look like.</p>
        </div>
      </section>

      <section className="panel">
        <h3>Embedding and referencing decisions</h3>
        {schema.map((r) => (
          <details key={r.relationship} className="rel">
            <summary>
              <span>{r.relationship}</span>
              <span className={"pill " + (r.pattern === "Embedded" ? "v-benign" : "v-suspicious")}>{r.pattern}</span>
            </summary>
            <p><strong>Field:</strong> <code>{r.field}</code></p>
            <p><strong>Why:</strong> {r.why}</p>
            <p className="muted">{r.evidence}</p>
            {r.alternative && (
              <>
                <p><strong>If it were embedded instead, each threat would also contain:</strong></p>
                <pre>{JSON.stringify(r.alternative, null, 2)}</pre>
              </>
            )}
          </details>
        ))}
      </section>

      <section className="panel">
        <h3>Document sizes with $bsonSize</h3>
        <div className="scroll">
          <table className="table">
            <thead><tr><th>Collection</th><th>Documents</th><th>Average</th><th>Largest</th><th>Of the 16 MB limit</th></tr></thead>
            <tbody>
              {sizes.collections.map((c) => (
                <tr key={c.collection}>
                  <td><code>{c.collection}</code></td><td>{c.documents.toLocaleString()}</td>
                  <td>{fmtBytes(c.avgBytes)}</td><td>{fmtBytes(c.maxBytes)}</td>
                  <td>{c.percentOfLimit}% <span className={c.status === "OK" ? "ok" : "bad"}>{c.status === "OK" ? "safe" : c.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted">The largest document in every collection stays far below {fmtBytes(sizes.limitBytes)}, because indicators are small and classification history is capped at 20 entries.</p>
      </section>

      <section className="panel">
        <h3>Activity: embed the source and decide which sources are an actual threat</h3>
        <p>
          <code>threats_embedded</code> stores a copy of the source inside each threat, plus a stored flag
          <code> assessment.actual_threat</code> that is true when the verdict is Malicious and the source reliability is at least 75.
        </p>
        <div className="actions left">
          <button onClick={rebuild} disabled={!!busy}>{busy === "build" ? "Rebuilding…" : "Rebuild embedded collection"}</button>
          <button className="primary" onClick={benchmark} disabled={!!busy}>{busy === "bench" ? "Running 30 rounds…" : "Run benchmark"}</button>
        </div>

        {bench && (
          <>
            <h4>Query: malicious threats from trusted sources (median of {bench.runs} runs)</h4>
            {Object.entries(bench.reads).map(([name, r]) => (
              <div key={name} className="bench">
                <span>{name}</span>
                <span className="bar-track"><span className="bar-fill" style={{ width: `${(r.medianMs / maxMs) * 100}%` }} /></span>
                <span>{r.medianMs} ms</span>
                <span className="muted">{r.results} results</span>
              </div>
            ))}
            <h4>Write: change the reliability of {bench.writes.source}</h4>
            <p>
              Referenced design updates <strong>{bench.writes.referenced.documentsTouched}</strong> document ({bench.writes.referenced.ms} ms).
              Embedded design updates <strong>{bench.writes.embedded.documentsTouched}</strong> documents ({bench.writes.embedded.ms} ms).
              The benchmark restores the original value afterwards.
            </p>
            <div className="grid2">
              <div><h4>What becomes faster</h4><ul>{bench.faster.map((t) => <li key={t}>{t}</li>)}</ul></div>
              <div><h4>What becomes harder</h4><ul>{bench.harder.map((t) => <li key={t}>{t}</li>)}</ul></div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
