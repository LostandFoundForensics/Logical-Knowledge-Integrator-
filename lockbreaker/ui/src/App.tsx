import { useEffect, useMemo, useState } from "react";
import "./styles.css";

const LB_API = (import.meta as any).env?.VITE_LOCKBREAKER_API_BASE ?? "http://localhost:8100";
const RUNNER_API = (import.meta as any).env?.VITE_LOCKBREAKER_RUNNER_BASE ?? "http://localhost:9100";

async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(`${LB_API}${path}`, { credentials: "include" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiPost<T>(base: string, path: string, body: any): Promise<T> {
  const r = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

type Profile = {
  id: string; name: string; category: string;
  description: string; legal?: { allowed_with?: string[] };
};

type Finding = {
  item: string; value: string; method: string;
  complexity?: string; court_note?: string;
};

export default function LockBreakerApp() {
  const [step, setStep] = useState(1);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [profileId, setProfileId] = useState("");
  const [caseId, setCaseId] = useState("");
  const [evidenceId, setEvidenceId] = useState("");
  const [filename, setFilename] = useState("");
  const [sha256, setSha256] = useState("");
  const [authBasis, setAuthBasis] = useState("court_order");
  const [authRef, setAuthRef] = useState("");
  const [authNotes, setAuthNotes] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [maxRuntime, setMaxRuntime] = useState(1440);
  const [jobId, setJobId] = useState("");
  const [jobStatus, setJobStatus] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<{ profiles: Profile[] }>("/api/v1/profiles")
      .then(d => setProfiles(d.profiles ?? []))
      .catch(() => setProfiles([]));
  }, []);

  const selectedProfile = useMemo(
    () => profiles.find(p => p.id === profileId) ?? null,
    [profiles, profileId]
  );

  const canSubmit = useMemo(
    () => sha256.trim().length >= 32 && authRef.trim().length >= 3 && !!profileId,
    [sha256, authRef, profileId]
  );

  async function createJob() {
    setError("");
    try {
      const body = {
        submitted_by: "examiner@local",
        evidence: { case_id: caseId, evidence_id: evidenceId, filename, sha256 },
        authorization: { basis: authBasis, reference_id: authRef, notes: authNotes },
        attack_profile: profileId,
        examiner_inputs: { owner_name: ownerName || undefined, max_runtime_minutes: maxRuntime },
        max_runtime_minutes: maxRuntime,
      };
      const status = await apiPost<any>(LB_API, "/api/v1/jobs", body);
      setJobId(status.job_id);
      setJobStatus(status);
      setStep(4);
    } catch (e: any) {
      setError(String(e.message ?? e));
    }
  }

  async function runJob() {
    setError("");
    try {
      await apiPost<any>(LB_API, `/api/v1/jobs/${jobId}/run`, {});
      setJobStatus((s: any) => ({ ...s, status: "running" }));
      setStep(5);
    } catch (e: any) {
      setError(String(e.message ?? e));
    }
  }

  async function runDry() {
    await apiPost<any>(LB_API, `/api/v1/jobs/${jobId}/run-dry`, {});
    await refreshStatus();
  }

  async function refreshStatus() {
    const s = await apiGet<any>(`/api/v1/jobs/${jobId}/status`);
    setJobStatus(s);
  }

  async function loadResult() {
    const r = await apiGet<any>(`/api/v1/jobs/${jobId}/result`);
    setResult(r);
    setStep(6);
  }

  return (
    <div className="container">
      <div className="lb-header">
        <div className="lb-wordmark">LockBreaker</div>
        <div className="lb-tagline">
          Mobile credential recovery · Authorized use only · Court-ready outputs
        </div>
      </div>

      {error && <div className="lb-error">{error}</div>}

      <div className="lb-stepper">
        {["Evidence","Profile","Authority","Review","Execute","Results"].map((label, i) => (
          <div key={i} className={`lb-step-dot ${step === i+1 ? "active" : step > i+1 ? "done" : ""}`}>
            <span>{i+1}</span><small>{label}</small>
          </div>
        ))}
      </div>

      {step === 1 && (
        <div className="card">
          <h2>1 — Evidence</h2>
          <div className="grid2">
            <label>Case ID<input value={caseId} onChange={e=>setCaseId(e.target.value)} placeholder="CASE-0001"/></label>
            <label>Evidence ID<input value={evidenceId} onChange={e=>setEvidenceId(e.target.value)} placeholder="EVID-0001"/></label>
            <label>Filename<input value={filename} onChange={e=>setFilename(e.target.value)} placeholder="backup.zip"/></label>
            <label>SHA256 (required)<input value={sha256} onChange={e=>setSha256(e.target.value)} placeholder="paste sha256 here" className={sha256.length > 0 && sha256.length < 32 ? "invalid" : ""}/></label>
          </div>
          <button onClick={()=>setStep(2)} disabled={sha256.length < 32 || !caseId}>Next →</button>
        </div>
      )}

      {step === 2 && (
        <div className="card">
          <h2>2 — Recovery Profile</h2>
          <p className="muted">Choose what LockBreaker will attempt to recover.</p>
          {profiles.length === 0 ? (
            <input value={profileId} onChange={e=>setProfileId(e.target.value)} placeholder="profile id (e.g., ios_encrypted_backup)"/>
          ) : (
            <select value={profileId} onChange={e=>setProfileId(e.target.value)}>
              <option value="">Select profile…</option>
              {profiles.map(p => <option key={p.id} value={p.id}>{p.name} ({p.category})</option>)}
            </select>
          )}
          {selectedProfile && (
            <div className="profile-card">
              <strong>{selectedProfile.name}</strong>
              <p>{selectedProfile.description}</p>
              {selectedProfile.legal?.allowed_with && (
                <p className="muted">Allowed with: {selectedProfile.legal.allowed_with.join(", ")}</p>
              )}
            </div>
          )}
          <label>Owner Name (optional — improves success rate)
            <input value={ownerName} onChange={e=>setOwnerName(e.target.value)} placeholder="e.g., Michael"/>
          </label>
          <label>Max Runtime (minutes)
            <input type="number" value={maxRuntime} onChange={e=>setMaxRuntime(Number(e.target.value))} min={1} max={10080}/>
          </label>
          <div className="row">
            <button className="secondary" onClick={()=>setStep(1)}>← Back</button>
            <button onClick={()=>setStep(3)} disabled={!profileId}>Next →</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="card">
          <h2>3 — Authorization</h2>
          <p className="muted">LockBreaker will not run without legal authority metadata. All fields are logged.</p>
          <label>Authorization Basis
            <select value={authBasis} onChange={e=>setAuthBasis(e.target.value)}>
              <option value="court_order">Court Order</option>
              <option value="warrant">Warrant</option>
              <option value="consent">Consent</option>
              <option value="owner_recovery">Owner Recovery</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label>Reference ID (required)
            <input value={authRef} onChange={e=>setAuthRef(e.target.value)} placeholder="ORDER-2025-123"/>
          </label>
          <label>Notes (optional)
            <input value={authNotes} onChange={e=>setAuthNotes(e.target.value)} placeholder="Scope notes…"/>
          </label>
          <div className="row">
            <button className="secondary" onClick={()=>setStep(2)}>← Back</button>
            <button onClick={createJob} disabled={!canSubmit}>Create Job →</button>
          </div>
          {!canSubmit && <p className="muted">Required: SHA256 + Authorization Reference ID + Profile.</p>}
        </div>
      )}

      {step === 4 && (
        <div className="card">
          <h2>4 — Review</h2>
          <div className="kv">
            <span>Job ID</span><span>{jobId}</span>
            <span>Profile</span><span>{profileId}</span>
            <span>Evidence</span><span>{filename} ({sha256.slice(0,16)}…)</span>
            <span>Authority</span><span>{authBasis} / {authRef}</span>
            <span>Runtime Limit</span><span>{maxRuntime} min</span>
          </div>
          <div className="row">
            <button className="secondary" onClick={()=>setStep(3)}>← Back</button>
            <button onClick={runDry}>Dry Run (test)</button>
            <button onClick={runJob}>▶ Run</button>
          </div>
        </div>
      )}

      {step === 5 && (
        <div className="card">
          <h2>5 — Execution</h2>
          <div className="kv">
            <span>Status</span><span>{jobStatus?.status ?? "—"}</span>
            <span>Stage</span><span>{jobStatus?.stage ?? "—"}</span>
            <span>Message</span><span>{jobStatus?.message ?? "—"}</span>
          </div>
          <div className="row">
            <button onClick={refreshStatus}>↻ Refresh</button>
            <button className="secondary" onClick={loadResult}>View Results</button>
          </div>
        </div>
      )}

      {step === 6 && (
        <div className="card">
          <h2>6 — Results</h2>
          {!result ? (
            <p className="muted">No result loaded.</p>
          ) : (
            <>
              <div className="kv">
                <span>Job</span><span>{result.job_id}</span>
                <span>Signed</span><span>{result.audit?.signed_at ?? "unsigned"}</span>
                <span>Algorithm</span><span>{result.audit?.signature_alg ?? "—"}</span>
              </div>
              <hr/>
              <h3>Findings</h3>
              {result.findings?.length > 0 ? (
                <table className="lb-table">
                  <thead><tr><th>Item</th><th>Value</th><th>Method</th><th>Complexity</th></tr></thead>
                  <tbody>
                    {result.findings.map((f: Finding, i: number) => (
                      <tr key={i}>
                        <td>{f.item}</td>
                        <td><code>{f.value}</code></td>
                        <td>{f.method}</td>
                        <td>{f.complexity ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="muted">No credentials recovered under authorized conditions.</p>
              )}
              <hr/>
              <details>
                <summary className="muted">Full signed result JSON</summary>
                <pre>{JSON.stringify(result, null, 2)}</pre>
              </details>
            </>
          )}
          <div className="row">
            <button className="secondary" onClick={()=>{ setStep(1); setJobId(""); setResult(null); }}>New Job</button>
          </div>
        </div>
      )}

      <p className="footer">
        LockBreaker — designed exclusively for authorized mobile forensics.
        All jobs require legal authority. All results are cryptographically signed.
      </p>
    </div>
  );
}
