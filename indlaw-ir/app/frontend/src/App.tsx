import { useEffect, useState } from "react";
import { ArrowUpRight, BookOpen, Search, Send, ShieldCheck } from "lucide-react";
import "./styles.css";

type Evidence = {
  rank: number;
  title: string;
  section: string;
  text: string;
  source_url: string;
  programme: string;
  admission_year: number | null;
  retrieved_at: string;
  document_type: string;
  semantic_score?: number | null;
  bm25_score?: number | null;
  rrf_score?: number | null;
  final_evidence_score?: number | null;
  selection_reason?: string | null;
};
type Message = { role: "user" | "assistant"; content: string; evidence?: Evidence[]; context?: boolean; refused?: boolean };
type Page = "chat" | "search" | "about";
const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const examples = [
  "How do I apply for B.Tech in 2026?",
  "What is the first-semester B.Tech fee for 2026?",
  "Does the institute provide scholarships directly?",
];

function EvidenceCard({ item }: { item: Evidence }) {
  const [expanded, setExpanded] = useState(false);
  const excerpt = item.text.length > 410 ? `${item.text.slice(0, 410)}…` : item.text;
  return (
    <article className="evidence-card">
      <div className="evidence-top">
        <span className="source-number">{String(item.rank).padStart(2, "0")}</span>
        <span className="source-kind">{item.document_type.toUpperCase() || "SOURCE"}</span>
        {item.admission_year && <span className="source-year">Admission {item.admission_year}</span>}
      </div>
      <h4>{item.title}</h4>
      <p className="source-section">{item.section}{item.programme ? ` · ${item.programme}` : ""}</p>
      <p className="source-text">{expanded ? item.text : excerpt}</p>
      {item.text.length > 410 && <button className="plain-button" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>{expanded ? "Show less" : "Show full excerpt"}</button>}
      <div className="source-footer">
        <a href={item.source_url} target="_blank" rel="noopener noreferrer">Open official source <ArrowUpRight size={15} aria-hidden="true" /></a>
        <span>Checked {item.retrieved_at ? new Date(item.retrieved_at).toLocaleDateString() : "locally"}</span>
      </div>
      <details className="score-details"><summary>Retrieval details</summary><p>{item.selection_reason || "Selected evidence"}</p><p>Semantic {item.semantic_score?.toFixed(3) ?? "—"} · BM25 {item.bm25_score?.toFixed(2) ?? "—"} · RRF {item.rrf_score?.toFixed(4) ?? "—"}</p></details>
    </article>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>("chat");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [results, setResults] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(false);
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { fetch(`${API}/health`).then(r => setHealthy(r.ok)).catch(() => setHealthy(false)); }, []);

  async function submit(text = input) {
    const query = text.trim();
    if (!query || loading) return;
    setInput("");
    setError("");
    setLoading(true);
    try {
      if (page === "search") {
        const response = await fetch(`${API}/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query }) });
        if (!response.ok) throw new Error("Search is unavailable. Check that the local indexes are built.");
        const payload = await response.json();
        setResults(payload.results);
      } else {
        const conversation = messages.map(({ role, content }) => ({ role, content }));
        setMessages(m => [...m, { role: "user", content: query }]);
        const response = await fetch(`${API}/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: query, conversation }) });
        if (!response.ok) throw new Error("The assistant is unavailable. Check the backend terminal.");
        const payload = await response.json();
        setMessages(m => [...m, { role: "assistant", content: payload.answer, evidence: payload.evidence, context: payload.context_used, refused: payload.refused }]);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Request failed.");
    } finally { setLoading(false); }
  }

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="topbar">
      <div className="brand"><span className="brand-mark">II</span><span><strong>IIIT Kottayam</strong><small>Applicant assistant · local prototype</small></span></div>
      <div className="topbar-right"><span className={`health ${healthy === true ? "online" : healthy === false ? "offline" : ""}`} aria-live="polite"><i />{healthy === true ? "Ready" : healthy === false ? "Offline" : "Connecting"}</span><span className="engine-tag">BM25 + BGE + RRF</span></div>
    </header>
    <div className="workspace">
      <aside className="sidebar" aria-label="Workspace navigation">
        <div className="sidebar-label">WORKSPACE</div>
        <nav><button className={page === "chat" ? "active" : ""} aria-current={page === "chat" ? "page" : undefined} onClick={() => setPage("chat")}><BookOpen size={17} /> Ask a question</button><button className={page === "search" ? "active" : ""} aria-current={page === "search" ? "page" : undefined} onClick={() => setPage("search")}><Search size={17} /> Explore evidence</button><button className={page === "about" ? "active" : ""} aria-current={page === "about" ? "page" : undefined} onClick={() => setPage("about")}><ShieldCheck size={17} /> About this system</button></nav>
        <div className="sidebar-note"><ShieldCheck size={18} /><p>Answers use a curated set of public official sources. Always verify dates and fees on the linked page before acting.</p></div>
      </aside>
      <main id="main-content" className="main-content">
        {page === "chat" && <><div className="intro"><span className="eyebrow">OFFICIAL SOURCE RETRIEVAL</span><h1>Find the answer.<br /><em>See the source.</em></h1><p>Ask about B.Tech admissions, programmes, fees, and scholarships at IIIT Kottayam. If the available material does not support an answer, the assistant will say so.</p></div><div className="content-width">
          {messages.length === 0 && <section className="example-area" aria-label="Example questions"><h2>Start with a question</h2><div className="examples">{examples.map(example => <button key={example} onClick={() => void submit(example)}>{example}<ArrowUpRight size={16} /></button>)}</div></section>}
          <section className="messages" aria-live="polite">{messages.map((message, index) => <article className={`message ${message.role}`} key={index}><div className="message-byline">{message.role === "user" ? "YOU" : "ASSISTANT"}{message.context && <span>· Follow-up context used</span>}{message.refused && <span>· Not verified</span>}</div><p className="answer-copy">{message.content}</p>{message.role === "assistant" && message.evidence && message.evidence.length > 0 && <div className="source-list"><h3>Supporting sources</h3>{message.evidence.map((item, position) => <EvidenceCard key={`${index}-${position}`} item={item} />)}</div>}</article>)}{loading && <p className="loading" role="status">Checking official sources…</p>}</section>
        </div></>}
        {page === "search" && <div className="content-width section-page"><span className="eyebrow">RETRIEVAL EXPLORER</span><h1>Inspect the evidence</h1><p>Use the same curated index as the assistant. Scores are diagnostics, not a guarantee that an answer is correct.</p>{results.length > 0 ? <div className="source-list">{results.map((item, index) => <EvidenceCard key={index} item={item} />)}</div> : <div className="empty-panel">Run a search to inspect ranked official passages.</div>}</div>}
        {page === "about" && <div className="content-width section-page"><span className="eyebrow">HOW IT WORKS</span><h1>Grounded by design</h1><p>This local academic prototype indexes a curated allowlist of public IIIT Kottayam pages and PDFs. BM25 and BGE-base retrieve candidate passages; reciprocal-rank fusion combines them. Source and year checks precede any extractive answer.</p><div className="about-grid"><div><strong>Sources</strong><span>Official IIIT Kottayam pages and PDFs, collected locally</span></div><div><strong>Coverage</strong><span>Applicant questions: admissions, B.Tech programmes, fees, scholarships</span></div><div><strong>Limits</strong><span>Not an official institute service. Missing or contradictory evidence should lead to abstention.</span></div><div><strong>Privacy</strong><span>Downloaded content and generated indexes stay on this computer.</span></div></div></div>}
      </main>
    </div>
    {page !== "about" && <form className="composer" onSubmit={event => { event.preventDefault(); void submit(); }}><div className="composer-inner"><label htmlFor="question" className="sr-only">{page === "search" ? "Search official sources" : "Ask an applicant question"}</label><input id="question" value={input} onChange={event => setInput(event.target.value)} placeholder={page === "search" ? "Search official sources…" : "Ask about admissions, fees, eligibility…"} /><button disabled={loading || !input.trim()} aria-label={page === "search" ? "Search" : "Send question"} type="submit"><Send size={18} /></button></div>{error && <p className="error" role="alert">{error}</p>}<p>Local prototype · Verify important details with the institute</p></form>}
  </div>;
}
