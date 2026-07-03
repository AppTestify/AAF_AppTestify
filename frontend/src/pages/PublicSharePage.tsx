import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchPublicShareSnapshot, type PublicShareSnapshot } from "../api";

export function PublicSharePage() {
  const { token } = useParams<{ token: string }>();
  const [snapshot, setSnapshot] = useState<PublicShareSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    fetchPublicShareSnapshot(token)
      .then(setSnapshot)
      .catch((e) => setError(e instanceof Error ? e.message : "Share link unavailable"))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="app">
        <div className="card empty-state">Loading shared run…</div>
      </div>
    );
  }

  if (error || !snapshot) {
    return (
      <div className="app">
        <div className="card">
          <h2>Share link unavailable</h2>
          <p style={{ color: "var(--muted)" }}>{error ?? "This link may have expired."}</p>
          <Link to="/login" className="btn btn-primary btn-sm">
            Sign in to Casantris
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <article className="card" style={{ maxWidth: "52rem", margin: "2rem auto" }}>
        <p className="gov-hub-eyebrow">Shared governance run</p>
        <h1>Run #{snapshot.run_id}</h1>
        <p className="field-hint">
          Finished {snapshot.finished_at ? new Date(snapshot.finished_at).toLocaleString() : "—"}
        </p>
        <div className="gov-recommendation-actions" style={{ marginBottom: "1rem" }}>
          <a href={snapshot.pdf_path} className="btn btn-primary btn-sm" target="_blank" rel="noreferrer">
            Download DF one-pager (PDF)
          </a>
        </div>
        <section className="card" style={{ marginBottom: "1rem" }}>
          <h2>Prompt</h2>
          <p>{snapshot.prompt}</p>
        </section>
        <section className="card" style={{ marginBottom: "1rem" }}>
          <h2>Orchestration</h2>
          <p>Recommended action: {snapshot.recommended_action ?? "—"}</p>
          <p>
            Consensus: {snapshot.consensus_score ?? "—"} · Utility: {snapshot.utility_score ?? "—"} · Xi:{" "}
            {snapshot.xi_score ?? "—"}
          </p>
        </section>
        {snapshot.incident_title ? (
          <section className="card" style={{ marginBottom: "1rem" }}>
            <h2>Incident</h2>
            <p>{snapshot.incident_title}</p>
          </section>
        ) : null}
        {snapshot.executive_title || snapshot.executive_content ? (
          <section className="card">
            <h2>Executive summary</h2>
            {snapshot.executive_title ? <p><strong>{snapshot.executive_title}</strong></p> : null}
            {snapshot.executive_content ? <p>{snapshot.executive_content}</p> : null}
          </section>
        ) : null}
      </article>
    </div>
  );
}
