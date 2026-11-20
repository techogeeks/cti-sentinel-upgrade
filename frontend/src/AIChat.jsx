import { useEffect, useState } from "react";
import { api } from "./api.js";

const ideas = [
  "Explain what MongoDB replica-set failover means",
  "How do I interpret write-concern latency in Lab 9?",
  "Explain vector search and retrieval-augmented generation",
];

const isLabCommand = message => /^(?:\/run|run lab) \d{1,2}[.-][12]$/i.test(message.trim());

export default function AIChat() {
  const [status, setStatus] = useState(null);
  const [model, setModel] = useState("");
  const [checking, setChecking] = useState(true);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [conversation, setConversation] = useState("");

  async function refresh() {
    setChecking(true);
    try {
      const data = await api("/ai/status");
      setStatus(data);
      const names = data.models || [];
      setModel(previous => names.includes(previous) ? previous : (data.model || ""));
      setError("");
    } catch (err) {
      setStatus(null);
      setError("Can't contact CTI Sentinel API: " + err.message);
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => { refresh(); }, []);
  const ready = !!status?.configured;
  const models = status?.models || [];

  function newConversation() {
    setMessages([]);
    setConversation("");
    setDraft("");
    setError("");
    setNotice("");
  }
  function changeModel(value) {
    setModel(value);
    newConversation();
  }

  async function send(e, suggestion) {
    e?.preventDefault?.();
    const message = (suggestion ?? draft).trim();
    if (!message || busy || (!isLabCommand(message) && (!ready || checking))) return;
    setBusy(true);
    setError("");
    setNotice("");
    setDraft("");
    setMessages(old => [...old, { role: "user", content: message }]);
    try {
      const data = await api("/ai/chat", { method: "POST", body: {
        message, model, conversation_id: conversation || undefined,
      }});
      if (data.lab_result) {
        setMessages(old => [...old, {
          role: "result", content: JSON.stringify(data.lab_result, null, 2),
          label: `LAB ${data.chapter}.${data.lab} RESULT`,
        }]);
        return;
      }
      setConversation(data.conversation_id);
      setMessages(old => [...old, { role: "assistant", content: data.answer, model: data.model }]);
      if (data.warning) setNotice(data.warning);
    } catch (err) {
      setError(err.message);
      setDraft(message);
    } finally {
      setBusy(false);
    }
  }

  return <div className="chat-layout">
    <div className="page-heading"><div>
      <div className="eyebrow">INTELLIGENCE / LOCAL AI</div>
      <h1>Ollama AI Assistant</h1>
      <p>Run a language model on your laptop. No NVIDIA key, account or cloud inference required.</p>
    </div><button className="quiet-btn" onClick={newConversation} disabled={busy}>+ New conversation</button></div>

    <div className="ai-provider-bar">
      <div className="ai-provider-tabs"><div className="ai-provider-tab selected"><span className="ai-provider-dot"/> OLLAMA <small>LOCAL MODEL</small></div></div>
      <div className="ai-provider-controls">
        <label className="ai-model-label"><span>MODEL</span>
          <select aria-label="Ollama model" value={models.includes(model) ? model : ""} disabled={busy || !models.length}
            onChange={e => changeModel(e.target.value)}>
            {!models.length && <option value="">No models installed</option>}
            {models.map(name => <option key={name} value={name}>{name}</option>)}
          </select>
        </label>
        <span className={`ai-provider-state ${ready ? "ready" : "offline"}`}>
          <span className="ai-provider-dot"/>{checking ? "Checking…" : ready ? "Ready" : status?.available ? "No models" : "Offline"}
        </span>
        <button type="button" className="quiet-btn ai-refresh" onClick={refresh} disabled={checking || busy}>Refresh</button>
      </div>
    </div>

    <section className="chat-surface">
      <div className="chat-feed" aria-live="polite">
        {!messages.length && <div className="chat-welcome"><div className="chat-glyph">✧</div>
          <h2>Your local cybersecurity copilot</h2>
          <p>Ask about MongoDB Chapters 1–18, replica sets, sharding, security, or threat intelligence.</p>
          <div className="prompt-grid">{ideas.map(s => <button key={s} disabled={busy || !ready} onClick={() => send(null, s)}>{s} <span>↗</span></button>)}</div>
        </div>}
        {messages.map((item, i) => <div className={`chat-bubble ${item.role}`} key={i}>
          <div className="chat-role">{item.role === "user" ? "YOU" : item.label || `OLLAMA · ${item.model || model}`}</div>
          {item.role === "result" ? <pre style={{overflowX: "auto"}}>{item.content}</pre> : <div>{item.content}</div>}
        </div>)}
        {busy && <div className="chat-bubble assistant">{isLabCommand(messages.at(-1)?.content || "") ? "Running lab…" : `Generating with ${model}…`}</div>}
      </div>
      {!checking && !ready && <div className="notice ai-setup-notice" role="status">
        <strong>Ollama setup required</strong>
        <p>{status?.error || "The backend can't reach the local model."}</p>
        <p>Install <a href="https://ollama.com/download/windows" target="_blank" rel="noreferrer">Ollama for Windows</a>, open a new PowerShell terminal, and run:</p>
        <code>ollama pull qwen2.5:3b</code>
        <p>Then click <b>Refresh</b>. Ollama must be running in the background.</p>
      </div>}
      {error && <div className="notice error-notice" role="alert">{error}</div>}
      {notice && <div className="notice ai-setup-notice" role="status">{notice}</div>}
      <form onSubmit={send} className="chat-composer">
        <input aria-label="Chat message" value={draft} onChange={e => setDraft(e.target.value)} maxLength={6000}
          disabled={busy}
          placeholder="Ask about MongoDB or type run lab 10.1"/>
        <button className="action-primary" type="submit" disabled={busy || !draft.trim() || (!isLabCommand(draft) && (checking || !ready))}>{busy ? "Working…" : "Send →"}</button>
      </form>
      <p className="small-note">Use <code>run lab 11.1</code> to run the shard-key exercise. Open Assignments for lab prerequisites.</p>
    </section>
  </div>;
}
