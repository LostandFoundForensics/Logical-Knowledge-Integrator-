import { useState, useCallback } from "react";

// ── Design tokens ─────────────────────────────────────────────────────────────
// Palette: near-black workspace, deep slate panels, amber accent (evidentiary),
// muted steel for secondary text. JetBrains Mono for hashes/IDs, Inter for UI.
// Signature: truncated hash-chain visualization in the audit log — each entry
// shows a ◆ chain link connecting to the previous entry_hash, making the
// integrity chain visually legible rather than just a list of strings.

const C = {
  bg: "#0F1117",
  panel: "#1C2130",
  panelBorder: "#2A3A52",
  accent: "#D4A843",
  accentDim: "#8A6A20",
  textPrimary: "#E8EDF3",
  textMuted: "#6B7A90",
  textDim: "#3D4F66",
  danger: "#C0392B",
  dangerBg: "#2D1010",
  success: "#27AE60",
  successBg: "#0D2D1A",
  warning: "#E67E22",
  warningBg: "#2D1E08",
  draft: "#5B8CDB",
  observed: "#D4A843",
};

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: ${C.bg}; color: ${C.textPrimary}; font-family: 'Inter', sans-serif; font-size: 14px; }
  ::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: ${C.panel}; }
  ::-webkit-scrollbar-thumb { background: ${C.panelBorder}; border-radius: 3px; }
  .mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; }
  .app { display: flex; height: 100vh; overflow: hidden; }
  .sidebar { width: 220px; flex-shrink: 0; background: ${C.panel}; border-right: 1px solid ${C.panelBorder}; display: flex; flex-direction: column; }
  .sidebar-header { padding: 20px 16px 12px; border-bottom: 1px solid ${C.panelBorder}; }
  .sidebar-title { font-size: 13px; font-weight: 600; color: ${C.accent}; letter-spacing: 0.08em; text-transform: uppercase; }
  .sidebar-subtitle { font-size: 11px; color: ${C.textMuted}; margin-top: 2px; }
  .nav-item { display: flex; align-items: center; gap: 10px; padding: 10px 16px; cursor: pointer; color: ${C.textMuted}; transition: all 0.15s; border-left: 3px solid transparent; font-size: 13px; }
  .nav-item:hover { background: rgba(212,168,67,0.06); color: ${C.textPrimary}; }
  .nav-item.active { background: rgba(212,168,67,0.1); color: ${C.accent}; border-left-color: ${C.accent}; font-weight: 500; }
  .nav-section { padding: 16px 16px 6px; font-size: 10px; font-weight: 600; color: ${C.textDim}; letter-spacing: 0.12em; text-transform: uppercase; }
  .main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  .topbar { padding: 14px 24px; border-bottom: 1px solid ${C.panelBorder}; display: flex; align-items: center; justify-content: space-between; background: ${C.panel}; flex-shrink: 0; }
  .topbar-title { font-size: 16px; font-weight: 600; }
  .content { flex: 1; overflow-y: auto; padding: 24px; }
  .statusbar { padding: 8px 24px; border-top: 1px solid ${C.panelBorder}; display: flex; align-items: center; gap: 16px; background: ${C.panel}; flex-shrink: 0; font-size: 11px; color: ${C.textMuted}; }
  .status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
  .btn { padding: 7px 14px; border-radius: 5px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid; transition: all 0.15s; white-space: nowrap; font-family: 'Inter', sans-serif; }
  .btn-primary { background: ${C.accent}; color: #0F1117; border-color: ${C.accent}; }
  .btn-primary:hover { background: #E5B84F; }
  .btn-secondary { background: transparent; color: ${C.textPrimary}; border-color: ${C.panelBorder}; }
  .btn-secondary:hover { border-color: ${C.accent}; color: ${C.accent}; }
  .btn-danger { background: transparent; color: ${C.danger}; border-color: ${C.danger}; }
  .btn-danger:hover { background: ${C.dangerBg}; }
  .btn-sm { padding: 4px 10px; font-size: 12px; }
  .btn-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
  .card { background: ${C.panel}; border: 1px solid ${C.panelBorder}; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
  .card-title { font-size: 13px; font-weight: 600; color: ${C.textMuted}; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 14px; }
  .banner { padding: 10px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 13px; font-weight: 500; display: flex; align-items: center; gap: 10px; }
  .banner-warning { background: ${C.warningBg}; border: 1px solid ${C.warning}; color: ${C.warning}; }
  .banner-danger { background: ${C.dangerBg}; border: 1px solid ${C.danger}; color: ${C.danger}; }
  .banner-success { background: ${C.successBg}; border: 1px solid ${C.success}; color: ${C.success}; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: 10px 12px; font-size: 11px; font-weight: 600; color: ${C.textMuted}; text-transform: uppercase; letter-spacing: 0.08em; border-bottom: 1px solid ${C.panelBorder}; }
  td { padding: 12px 12px; border-bottom: 1px solid rgba(42,58,82,0.5); font-size: 13px; vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(212,168,67,0.03); }
  .badge { display: inline-flex; align-items: center; gap: 5px; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .badge-draft { background: rgba(91,140,219,0.15); color: ${C.draft}; border: 1px solid rgba(91,140,219,0.3); }
  .badge-observed { background: rgba(212,168,67,0.15); color: ${C.observed}; border: 1px solid rgba(212,168,67,0.3); }
  .badge-staged { background: rgba(107,122,144,0.15); color: ${C.textMuted}; border: 1px solid rgba(107,122,144,0.3); }
  .badge-copied { background: rgba(39,174,96,0.12); color: #4EC97B; border: 1px solid rgba(39,174,96,0.3); }
  .badge-hashed { background: rgba(212,168,67,0.12); color: ${C.accent}; border: 1px solid rgba(212,168,67,0.3); }
  .badge-excluded { background: rgba(107,122,144,0.1); color: ${C.textDim}; border: 1px solid rgba(42,58,82,0.5); }
  .badge-mismatch { background: ${C.dangerBg}; color: ${C.danger}; border: 1px solid ${C.danger}; }
  .badge-certain { background: rgba(39,174,96,0.12); color: #4EC97B; }
  .badge-likely { background: rgba(212,168,67,0.12); color: ${C.accent}; }
  .badge-uncertain { background: rgba(192,57,43,0.12); color: ${C.danger}; }
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 100; backdrop-filter: blur(2px); }
  .modal { background: ${C.panel}; border: 1px solid ${C.panelBorder}; border-radius: 10px; padding: 28px; max-width: 480px; width: 90%; }
  .modal-title { font-size: 16px; font-weight: 600; margin-bottom: 12px; }
  .modal-body { color: ${C.textMuted}; font-size: 13px; line-height: 1.6; margin-bottom: 20px; }
  .modal-actions { display: flex; justify-content: flex-end; gap: 10px; }
  .form-group { margin-bottom: 16px; }
  .form-label { font-size: 12px; font-weight: 600; color: ${C.textMuted}; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; display: block; }
  input, select, textarea { width: 100%; padding: 9px 12px; background: ${C.bg}; border: 1px solid ${C.panelBorder}; border-radius: 5px; color: ${C.textPrimary}; font-size: 13px; font-family: 'Inter', sans-serif; outline: none; transition: border-color 0.15s; }
  input:focus, select:focus, textarea:focus { border-color: ${C.accent}; }
  textarea { resize: vertical; min-height: 80px; }
  select option { background: ${C.panel}; }
  .hash-chain-entry { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; border-bottom: 1px solid rgba(42,58,82,0.4); }
  .hash-chain-entry:last-child { border-bottom: none; }
  .chain-link { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; width: 20px; padding-top: 3px; }
  .chain-dot { width: 10px; height: 10px; border-radius: 50%; background: ${C.accent}; flex-shrink: 0; }
  .chain-line { width: 2px; flex: 1; background: linear-gradient(${C.accent}, ${C.panelBorder}); margin-top: 3px; min-height: 20px; }
  .chain-entry-content { flex: 1; }
  .chain-action { font-size: 13px; font-weight: 600; color: ${C.textPrimary}; }
  .chain-ts { font-size: 11px; color: ${C.textMuted}; margin-top: 2px; }
  .chain-hash { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: ${C.textDim}; margin-top: 4px; display: flex; align-items: center; gap: 6px; }
  .chain-hash-connected { color: ${C.accentDim}; }
  .kv-row { display: flex; gap: 8px; padding: 8px 0; border-bottom: 1px solid rgba(42,58,82,0.3); }
  .kv-key { font-size: 12px; color: ${C.textMuted}; width: 140px; flex-shrink: 0; }
  .kv-val { font-size: 13px; word-break: break-all; }
  .section-header { font-size: 20px; font-weight: 600; margin-bottom: 6px; }
  .section-desc { font-size: 13px; color: ${C.textMuted}; margin-bottom: 20px; }
  .empty-state { text-align: center; padding: 48px 24px; color: ${C.textMuted}; }
  .empty-icon { font-size: 32px; margin-bottom: 12px; }
  .empty-text { font-size: 14px; }
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }
  .stat-card { background: ${C.bg}; border: 1px solid ${C.panelBorder}; border-radius: 6px; padding: 16px; }
  .stat-value { font-size: 28px; font-weight: 600; color: ${C.accent}; }
  .stat-label { font-size: 11px; color: ${C.textMuted}; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.06em; }
  .artifact-type-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
  .artifact-type-btn { background: ${C.bg}; border: 1px solid ${C.panelBorder}; border-radius: 6px; padding: 16px 12px; text-align: center; cursor: pointer; transition: all 0.15s; }
  .artifact-type-btn:hover { border-color: ${C.accent}; background: rgba(212,168,67,0.06); }
  .artifact-type-icon { font-size: 22px; margin-bottom: 8px; }
  .artifact-type-label { font-size: 12px; font-weight: 500; text-transform: capitalize; }
`;

// ── Mock in-memory state (mirrors what the Python backend would persist) ──────
const initialDataset = {
  dataset_id: "ds-" + Math.random().toString(36).slice(2, 10),
  name: "iOS Messages Validation Set",
  created_utc: new Date().toISOString(),
  created_by: "Investigator",
  mode: "normal",
  status: "draft",
};

const ARTIFACT_ICONS = {
  message: "💬", call: "📞", photo_video: "📸", app_install: "📦",
  notification: "🔔", location_event: "📍", web_visit: "🌐", custom: "🗂️",
};

const ARTIFACT_TYPES = ["message","call","photo_video","app_install","notification","location_event","web_visit","custom"];

// ── Utility components ─────────────────────────────────────────────────────────
function Badge({ type }) {
  const cls = {
    draft_truth: "badge-draft", observed_truth: "badge-observed",
    staged: "badge-staged", copied: "badge-copied", hashed: "badge-hashed",
    excluded: "badge-excluded", hash_mismatch: "badge-mismatch", missing: "badge-mismatch",
    certain: "badge-certain", likely: "badge-likely", uncertain: "badge-uncertain",
  }[type] || "badge-staged";
  return <span className={`badge ${cls}`}>{type?.replace(/_/g," ")}</span>;
}

function Modal({ title, body, confirmLabel, cancelLabel, danger, onConfirm, onCancel, children }) {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">{title}</div>
        {body && <div className="modal-body">{body}</div>}
        {children}
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onCancel}>{cancelLabel || "Cancel"}</button>
          <button className={`btn ${danger ? "btn-danger" : "btn-primary"}`} onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ icon, text }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <div className="empty-text">{text}</div>
    </div>
  );
}

// ── Screens ────────────────────────────────────────────────────────────────────

function DatasetHome({ dataset, truthRecords, intakeRecords, onNavigate, onVerifyDataset }) {
  const draft = truthRecords.filter(r => r.state === "draft_truth").length;
  const observed = truthRecords.filter(r => r.state === "observed_truth").length;
  const hashed = intakeRecords.filter(r => r.state === "hashed").length;

  return (
    <div>
      <div className="section-header">Dataset Home</div>
      <div className="section-desc">{dataset.name}</div>

      {dataset.mode === "quarantine" && (
        <div className="banner banner-danger">
          🔒 QUARANTINE MODE — Integrity checks failed. Evidence intake is view-only; validation and court-safe exports are disabled.
        </div>
      )}
      {draft > 0 && dataset.mode !== "quarantine" && (
        <div className="banner banner-warning">
          ⚠ {draft} draft truth record{draft !== 1 ? "s" : ""} pending approval. Court-safe validation is blocked until all drafts are resolved.
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-card"><div className="stat-value">{observed}</div><div className="stat-label">Observed Truth</div></div>
        <div className="stat-card"><div className="stat-value" style={{color:C.draft}}>{draft}</div><div className="stat-label">Draft Truth</div></div>
        <div className="stat-card"><div className="stat-value">{intakeRecords.length}</div><div className="stat-label">Evidence Inputs</div></div>
        <div className="stat-card"><div className="stat-value" style={{color:C.success}}>{hashed}</div><div className="stat-label">Hashed Inputs</div></div>
      </div>

      <div className="btn-row">
        <button className="btn btn-secondary" onClick={() => onNavigate("evidence")}>Evidence Inputs</button>
        <button className="btn btn-secondary" onClick={() => onNavigate("truth")}>Truth Ledger</button>
        <button className="btn btn-secondary" onClick={onVerifyDataset}>Verify Dataset Integrity</button>
      </div>

      <div className="card">
        <div className="card-title">Dataset Info</div>
        {[
          ["Dataset ID", dataset.dataset_id],
          ["Status", dataset.status],
          ["Integrity Mode", dataset.mode],
          ["Created By", dataset.created_by],
          ["Created", new Date(dataset.created_utc).toLocaleString()],
        ].map(([k, v]) => (
          <div className="kv-row" key={k}>
            <div className="kv-key">{k}</div>
            <div className="kv-val mono">{v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EvidenceInputs({ dataset, records, onAddFile, onAddFolder, onAddIOS, onAddAndroid, onCopy, onExclude, onHash, onVerify }) {
  const [selected, setSelected] = useState(new Set());
  const quarantine = dataset.mode === "quarantine";

  const toggle = (id) => setSelected(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const anyMissingOrMismatch = records.some(r => r.state === "hash_mismatch" || r.state === "missing");

  return (
    <div>
      <div className="section-header">Evidence Inputs</div>
      <div className="section-desc">Manage and track evidence files and folders in this dataset.</div>

      {quarantine && <div className="banner banner-danger">🔒 QUARANTINE MODE — Evidence intake is view-only.</div>}
      {anyMissingOrMismatch && !quarantine && (
        <div className="banner banner-danger">⚠ Evidence integrity issues detected. Use Verify Evidence Integrity to view details.</div>
      )}

      <div className="btn-row">
        <button className="btn btn-secondary" disabled={quarantine} onClick={onAddFile}>+ Add Evidence File</button>
        <button className="btn btn-secondary" disabled={quarantine} onClick={onAddFolder}>+ Add Evidence Folder</button>
        <button className="btn btn-secondary" disabled={quarantine} onClick={onAddIOS}>+ Add iOS Backup Folder</button>
        <button className="btn btn-secondary" disabled={quarantine} onClick={onAddAndroid}>+ Add Android Pull Folder</button>
      </div>

      <div className="btn-row">
        <button className="btn btn-secondary btn-sm" disabled={selected.size === 0 || quarantine}
                onClick={() => onCopy([...selected])}>Copy Into Dataset</button>
        <button className="btn btn-secondary btn-sm" disabled={selected.size === 0}
                onClick={() => onHash([...selected])}>Hash Now (Selected)</button>
        <button className="btn btn-secondary btn-sm" disabled={selected.size === 0 || quarantine}
                onClick={() => onExclude([...selected])}>Exclude Selected</button>
        <button className="btn btn-secondary btn-sm" onClick={onVerify}>Verify Evidence Integrity</button>
      </div>

      <div className="card" style={{padding: 0, overflow: "hidden"}}>
        {records.length === 0 ? (
          <EmptyState icon="📁" text="No evidence inputs yet. Add files or folders above." />
        ) : (
          <table>
            <thead>
              <tr>
                <th style={{width: 36}}></th>
                <th>Intake ID</th>
                <th>State</th>
                <th>Source Type</th>
                <th>Source Path</th>
                <th>Size</th>
                <th>SHA-256</th>
              </tr>
            </thead>
            <tbody>
              {records.map(rec => (
                <tr key={rec.intake_id}>
                  <td>
                    <input type="checkbox" checked={selected.has(rec.intake_id)}
                           onChange={() => toggle(rec.intake_id)} style={{width:"auto"}} />
                  </td>
                  <td className="mono" style={{color: C.textMuted}}>{rec.intake_id}</td>
                  <td><Badge type={rec.state} /></td>
                  <td style={{color: C.textMuted, fontSize: 12}}>{rec.source_type.replace(/_/g," ")}</td>
                  <td style={{maxWidth: 200, overflow:"hidden", textOverflow:"ellipsis", color: C.textMuted, fontSize: 12}}
                      title={rec.source_path}>{rec.source_path.split("/").pop() || rec.source_path}</td>
                  <td className="mono" style={{color: C.textMuted}}>{rec.bytes ? `${(rec.bytes/1024).toFixed(1)}KB` : "—"}</td>
                  <td className="mono" style={{color: rec.hash.sha256 ? C.accent : C.textDim}}>
                    {rec.hash.sha256 ? rec.hash.sha256.slice(0,12) + "…" : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function TruthLedger({ dataset, records, onAdd, onApprove, onRevoke, onDelete, onVerify }) {
  const quarantine = dataset.mode === "quarantine";
  const hasDraft = records.some(r => r.state === "draft_truth");

  return (
    <div>
      <div className="section-header">Truth Ledger</div>
      <div className="section-desc">Manually entered and approved truth records for this dataset.</div>

      {quarantine && <div className="banner banner-danger">🔒 QUARANTINE MODE — Approval and validation are disabled.</div>}
      {hasDraft && !quarantine && (
        <div className="banner banner-warning">⚠ Draft truth exists. Court-safe validation is blocked until all drafts are resolved.</div>
      )}

      <div className="btn-row">
        <button className="btn btn-primary" onClick={onAdd}>+ Add Truth Manually</button>
        <button className="btn btn-secondary" onClick={onVerify}>Verify Truth Ledger Integrity</button>
      </div>

      <div className="card" style={{padding: 0, overflow: "hidden"}}>
        {records.length === 0 ? (
          <EmptyState icon="📋" text="No truth records yet. Add truth manually above." />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Type</th>
                <th>Timestamp</th>
                <th>Participants</th>
                <th>Confidence</th>
                <th>Source</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map(rec => (
                <tr key={rec.record_id}>
                  <td><Badge type={rec.state} /></td>
                  <td>
                    <span style={{marginRight: 6}}>{ARTIFACT_ICONS[rec.artifact_type]}</span>
                    <span style={{fontSize: 12, color: C.textMuted}}>{rec.artifact_type.replace(/_/g," ")}</span>
                  </td>
                  <td className="mono" style={{fontSize: 12, color: C.textMuted}}>
                    {rec.timestamp?.value}<br/>
                    <span style={{color: C.textDim}}>{rec.timestamp?.timezone}</span>
                  </td>
                  <td style={{fontSize: 12}}>
                    {rec.participants?.map(p => (
                      <div key={p.id} style={{color: C.textMuted}}>{p.label}</div>
                    ))}
                  </td>
                  <td><Badge type={rec.confidence} /></td>
                  <td style={{fontSize: 12, color: C.textMuted}}>{rec.source?.method?.replace(/_/g," ")}</td>
                  <td>
                    <div style={{display:"flex",gap:6}}>
                      {rec.state === "draft_truth" && (
                        <>
                          <button className="btn btn-secondary btn-sm" disabled={quarantine}
                                  onClick={() => onApprove(rec.record_id)}>Approve</button>
                          <button className="btn btn-danger btn-sm"
                                  onClick={() => onDelete(rec.record_id)}>Delete</button>
                        </>
                      )}
                      {rec.state === "observed_truth" && (
                        <button className="btn btn-secondary btn-sm" onClick={() => onRevoke(rec.record_id)}>Revoke</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function AuditLogView({ entries }) {
  return (
    <div>
      <div className="section-header">Audit Log</div>
      <div className="section-desc">Hash-chained append-only record of all actions. Every entry links to its predecessor via SHA-256.</div>

      <div className="card">
        {entries.length === 0 ? (
          <EmptyState icon="🔗" text="No audit entries yet." />
        ) : (
          <div>
            {[...entries].reverse().map((entry, i) => (
              <div className="hash-chain-entry" key={i}>
                <div className="chain-link">
                  <div className="chain-dot" />
                  {i < entries.length - 1 && <div className="chain-line" />}
                </div>
                <div className="chain-entry-content">
                  <div className="chain-action">{entry.action}</div>
                  <div className="chain-ts">{new Date(entry.timestamp_utc).toLocaleString()}</div>
                  {entry.details && Object.keys(entry.details).length > 0 && (
                    <div style={{fontSize: 11, color: C.textMuted, marginTop: 4}}>
                      {Object.entries(entry.details).slice(0,3).map(([k,v]) => (
                        <span key={k} style={{marginRight: 12}}>{k}: <span className="mono" style={{color: C.textDim}}>{typeof v === "object" ? "…" : String(v).slice(0,30)}</span></span>
                      ))}
                    </div>
                  )}
                  <div className="chain-hash">
                    <span style={{color: C.textDim}}>this: </span>
                    <span className="chain-hash-connected">{entry.entry_hash?.slice(0,16)}…</span>
                    {entry.prev_hash !== "GENESIS" && (
                      <>
                        <span style={{color: C.textDim}}>← prev: </span>
                        <span>{entry.prev_hash?.slice(0,16)}…</span>
                      </>
                    )}
                    {entry.prev_hash === "GENESIS" && (
                      <span style={{color: C.accent}}>◆ GENESIS</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Add Truth Form ─────────────────────────────────────────────────────────────
function AddTruthForm({ onSave, onCancel }) {
  const [step, setStep] = useState("choose");
  const [artifactType, setArtifactType] = useState(null);
  const [form, setForm] = useState({
    timestamp_value: "", timestamp_tz: "UTC+00:00",
    participant1_id: "person_a", participant1_label: "Device Owner",
    participant2_id: "person_b", participant2_label: "",
    direction: "unknown", confidence: "certain",
    content_body: "", content_url: "", content_duration: "",
    notes: "", asserted_by: "Investigator",
  });
  const [saveMode, setSaveMode] = useState("draft");
  const [gate, setGate] = useState(false);

  const set = (k, v) => setForm(f => ({...f, [k]: v}));

  const handleSave = () => {
    if (saveMode === "approve") { setGate(true); return; }
    doSave("draft_truth");
  };

  const doSave = (state) => {
    const participants = [
      {id: form.participant1_id, label: form.participant1_label},
    ];
    if (form.participant2_label) participants.push({id: form.participant2_id, label: form.participant2_label});

    let content = {};
    if (artifactType === "message") content = {body: form.content_body};
    else if (artifactType === "call") content = {duration_seconds: parseInt(form.content_duration)||null, call_type:"unknown"};
    else if (artifactType === "web_visit") content = {url: form.content_url, visit_kind:"unknown"};

    onSave({
      record_id: "rec-" + Math.random().toString(36).slice(2, 10),
      state,
      artifact_type: artifactType,
      timestamp: {value: form.timestamp_value, timezone: form.timestamp_tz},
      participants,
      confidence: form.confidence,
      direction: form.direction,
      content,
      attachments: [],
      source: {method: "manual_entry", reference: null},
      assertion: {
        asserted_by: form.asserted_by,
        asserted_utc: new Date().toISOString(),
        approved_by: state === "observed_truth" ? form.asserted_by : null,
        approved_utc: state === "observed_truth" ? new Date().toISOString() : null,
      },
      notes: form.notes,
    });
  };

  if (step === "choose") {
    return (
      <div>
        <div className="section-header">Add Truth — Choose Type</div>
        <div className="section-desc">Select the type of artifact you are recording as truth.</div>
        <div className="artifact-type-grid">
          {ARTIFACT_TYPES.map(t => (
            <div className="artifact-type-btn" key={t} onClick={() => { setArtifactType(t); setStep("form"); }}>
              <div className="artifact-type-icon">{ARTIFACT_ICONS[t]}</div>
              <div className="artifact-type-label">{t.replace(/_/g," ")}</div>
            </div>
          ))}
        </div>
        <div className="btn-row" style={{marginTop: 20}}>
          <button className="btn btn-secondary" onClick={onCancel}>Cancel</button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {gate && (
        <Modal
          title="Approve as Observed Truth"
          body="You are asserting this record as observed truth. This does not infer parser accuracy. Continue?"
          confirmLabel="Approve"
          onConfirm={() => { setGate(false); doSave("observed_truth"); }}
          onCancel={() => setGate(false)}
        />
      )}
      <div className="section-header">{ARTIFACT_ICONS[artifactType]} Truth Entry — {artifactType.replace(/_/g," ")}</div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:20}}>
        <div className="form-group">
          <label className="form-label">Timestamp (Local)</label>
          <input type="datetime-local" value={form.timestamp_value} onChange={e => set("timestamp_value", e.target.value)} />
        </div>
        <div className="form-group">
          <label className="form-label">Timezone</label>
          <input placeholder="UTC-06:00" value={form.timestamp_tz} onChange={e => set("timestamp_tz", e.target.value)} />
        </div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:20}}>
        <div className="form-group">
          <label className="form-label">Participant 1 Label</label>
          <input value={form.participant1_label} onChange={e => set("participant1_label", e.target.value)} placeholder="Device Owner" />
        </div>
        <div className="form-group">
          <label className="form-label">Participant 2 Label</label>
          <input value={form.participant2_label} onChange={e => set("participant2_label", e.target.value)} placeholder="Contact X" />
        </div>
      </div>
      {(artifactType === "message" || artifactType === "call") && (
        <div className="form-group">
          <label className="form-label">Direction</label>
          <select value={form.direction} onChange={e => set("direction", e.target.value)}>
            {artifactType === "call"
              ? ["incoming","outgoing","missed","unknown"].map(d => <option key={d} value={d}>{d}</option>)
              : ["incoming","outgoing","unknown"].map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
      )}
      {artifactType === "message" && (
        <div className="form-group">
          <label className="form-label">Message Body *</label>
          <textarea value={form.content_body} onChange={e => set("content_body", e.target.value)} placeholder="Message content…" />
        </div>
      )}
      {artifactType === "call" && (
        <div className="form-group">
          <label className="form-label">Duration (seconds)</label>
          <input type="number" min="0" value={form.content_duration} onChange={e => set("content_duration", e.target.value)} placeholder="0" />
        </div>
      )}
      {artifactType === "web_visit" && (
        <div className="form-group">
          <label className="form-label">URL *</label>
          <input value={form.content_url} onChange={e => set("content_url", e.target.value)} placeholder="https://…" />
        </div>
      )}
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:20}}>
        <div className="form-group">
          <label className="form-label">Confidence</label>
          <select value={form.confidence} onChange={e => set("confidence", e.target.value)}>
            {["certain","likely","uncertain"].map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Asserted By</label>
          <input value={form.asserted_by} onChange={e => set("asserted_by", e.target.value)} />
        </div>
      </div>
      <div className="form-group">
        <label className="form-label">Notes</label>
        <textarea value={form.notes} onChange={e => set("notes", e.target.value)} placeholder="Optional notes…" rows={3} />
      </div>
      <div className="btn-row">
        <button className="btn btn-secondary" onClick={onCancel}>Cancel</button>
        <button className="btn btn-secondary" onClick={() => { setSaveMode("draft"); handleSave(); }}>Save as Draft Truth</button>
        <button className="btn btn-primary" onClick={() => { setSaveMode("approve"); handleSave(); }}>Save and Approve as Observed Truth</button>
      </div>
    </div>
  );
}

// ── Add Input Modal ─────────────────────────────────────────────────────────────
function AddInputModal({ sourceType, onConfirm, onCancel }) {
  const [path, setPath] = useState("");
  const [notes, setNotes] = useState("");
  const labels = {
    file: "File Path", folder: "Folder Path",
    ios: "iOS Backup Folder Path", android: "Android Pull Folder Path",
  };
  return (
    <Modal title={`Add Evidence — ${labels[sourceType]}`}
           body="This will stage the input. No copying or hashing will occur until you explicitly trigger those actions."
           confirmLabel="Add Input" onConfirm={() => onConfirm(path, notes)} onCancel={onCancel}>
      <div className="form-group">
        <label className="form-label">{labels[sourceType]}</label>
        <input value={path} onChange={e => setPath(e.target.value)} placeholder="/path/to/evidence" />
      </div>
      <div className="form-group">
        <label className="form-label">Notes (optional)</label>
        <input value={notes} onChange={e => setNotes(e.target.value)} />
      </div>
    </Modal>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────────
export default function TruthloomApp() {
  const [nav, setNav] = useState("home");
  const [dataset, setDataset] = useState(initialDataset);
  const [truthRecords, setTruthRecords] = useState([]);
  const [intakeRecords, setIntakeRecords] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [modal, setModal] = useState(null);
  const [notification, setNotification] = useState(null);
  const [addingTruth, setAddingTruth] = useState(false);

  const notify = (msg, type="success") => {
    setNotification({msg, type});
    setTimeout(() => setNotification(null), 3500);
  };

  const sha256sim = (s) => {
    let h = 0;
    for (let i = 0; i < s.length; i++) h = Math.imul(31, h) + s.charCodeAt(i) | 0;
    return Math.abs(h).toString(16).padStart(8,"0").repeat(8).slice(0,64);
  };

  const appendAudit = useCallback((action, details={}) => {
    setAuditLog(prev => {
      const prevHash = prev.length > 0 ? prev[prev.length-1].entry_hash : "GENESIS";
      const ts = new Date().toISOString();
      const entry = {timestamp_utc: ts, action, details, prev_hash: prevHash};
      const canonical = JSON.stringify(entry, Object.keys(entry).sort());
      const entryHash = sha256sim(canonical);
      return [...prev, {...entry, entry_hash: entryHash}];
    });
  }, []);

  // Evidence input actions
  const addInput = (sourceType) => setModal({type: "add_input", sourceType});
  const handleAddInputConfirm = (path, notes) => {
    const intake_id = `in_${Math.random().toString(36).slice(2,10)}`;
    const rec = {intake_id, state:"staged", source_type: modal.sourceType === "ios" ? "ios_backup_folder" : modal.sourceType === "android" ? "android_pull_folder" : "generic_files",
                 source_path: path||"/path/to/evidence", copy_policy:"copy_preserve_tree",
                 dataset_path:null, bytes:null, hash:{sha256:null}, added_utc:new Date().toISOString(), notes};
    setIntakeRecords(prev => [...prev, rec]);
    appendAudit("ADD_INPUT_" + (modal.sourceType === "ios" ? "IOS_BACKUP_FOLDER" : modal.sourceType === "android" ? "ANDROID_PULL_FOLDER" : "FILE").toUpperCase(),
                {intake_id, path});
    setModal(null);
    notify(`Input staged: ${intake_id}`);
  };

  const handleCopy = (ids) => {
    if (dataset.mode === "quarantine") { notify("Cannot copy in quarantine mode","danger"); return; }
    setIntakeRecords(prev => prev.map(r => ids.includes(r.intake_id)
      ? {...r, state:"copied", dataset_path:`inputs/evidence/${r.intake_id}/`, bytes:Math.floor(Math.random()*1024*1024)+1024, copied_utc:new Date().toISOString()} : r));
    appendAudit("COPY_INPUTS", {intake_ids: ids});
    notify(`Copied ${ids.length} input(s) into dataset`);
  };

  const handleHash = (ids) => {
    setIntakeRecords(prev => prev.map(r => {
      if (!ids.includes(r.intake_id) || !r.dataset_path) return r;
      const sha = sha256sim(r.intake_id + r.source_path + Date.now());
      return {...r, state:"hashed", hash:{sha256:sha}, hashed_utc:new Date().toISOString()};
    }));
    appendAudit("HASH_INPUTS", {intake_ids: ids});
    notify(`Hashed ${ids.length} input(s)`);
  };

  const handleExclude = (ids) => {
    if (dataset.mode === "quarantine") { notify("Cannot exclude in quarantine mode","danger"); return; }
    setIntakeRecords(prev => prev.map(r => ids.includes(r.intake_id)
      ? {...r, state:"excluded", excluded_utc:new Date().toISOString()} : r));
    appendAudit("EXCLUDE_INPUTS", {excluded: ids});
    notify(`Excluded ${ids.length} input(s)`);
  };

  const handleVerifyEvidence = () => {
    const mismatches = intakeRecords.filter(r => r.state === "hashed" && Math.random() < 0.05);
    appendAudit("VERIFY_EVIDENCE_INTEGRITY", {ok: mismatches.length === 0});
    if (mismatches.length > 0) {
      setModal({type:"quarantine_confirm", reason: "Evidence hash mismatch detected"});
    } else {
      notify("Evidence integrity verified — no issues found");
    }
  };

  const handleVerifyDataset = () => {
    appendAudit("VERIFY_DATASET_INTEGRITY", {ok: dataset.mode !== "quarantine"});
    notify("Dataset integrity verified — all chains intact");
  };

  const handleVerifyLedger = () => {
    appendAudit("VERIFY_LEDGER_INTEGRITY", {ok: true});
    notify("Truth ledger integrity verified");
  };

  const enterQuarantine = () => {
    setDataset(d => ({...d, mode:"quarantine"}));
    appendAudit("ENTER_QUARANTINE_CONFIRMED", {reason: modal?.reason});
    setModal(null);
    notify("Dataset entered QUARANTINE MODE","danger");
  };

  // Truth actions
  const handleApprove = (record_id) => {
    setModal({type:"approve", record_id});
  };

  const confirmApprove = () => {
    const rid = modal.record_id;
    setTruthRecords(prev => prev.map(r => r.record_id === rid
      ? {...r, state:"observed_truth", assertion:{...r.assertion, approved_by:"Investigator", approved_utc:new Date().toISOString()}} : r));
    appendAudit("APPROVE_TRUTH", {record_id: rid});
    setModal(null);
    notify("Record approved as Observed Truth");
  };

  const handleRevoke = (record_id) => {
    setModal({type:"revoke", record_id});
  };

  const confirmRevoke = () => {
    const rid = modal.record_id;
    setTruthRecords(prev => prev.map(r => r.record_id === rid
      ? {...r, state:"draft_truth", assertion:{...r.assertion, approved_by:null, approved_utc:null}} : r));
    appendAudit("REVOKE_TRUTH", {record_id: rid});
    setModal(null);
    notify("Record revoked to Draft Truth");
  };

  const handleDelete = (record_id) => {
    setTruthRecords(prev => prev.filter(r => r.record_id !== record_id));
    appendAudit("DELETE_DRAFT_TRUTH", {record_id});
    notify("Draft truth record deleted");
  };

  const handleSaveTruth = (rec) => {
    setTruthRecords(prev => [...prev, rec]);
    appendAudit("ADD_TRUTH_RECORD", {record_id: rec.record_id, artifact_type: rec.artifact_type, "timestamp.value": rec.timestamp.value});
    if (rec.state === "observed_truth") appendAudit("APPROVE_TRUTH", {record_id: rec.record_id});
    setAddingTruth(false);
    notify(`Truth record saved as ${rec.state.replace(/_/g," ")}`);
    setNav("truth");
  };

  const navItems = [
    {id:"home", label:"Dataset Home", icon:"🏠"},
    {id:"evidence", label:"Evidence Inputs", icon:"📁"},
    {id:"truth", label:"Truth Ledger", icon:"📋"},
    {id:"audit", label:"Audit Log", icon:"🔗"},
  ];

  const topbarTitles = {
    home:"Dataset Home", evidence:"Evidence Inputs", truth:"Truth Ledger", audit:"Audit Log", add_truth:"Add Truth Record",
  };

  return (
    <>
      <style>{styles}</style>
      <div className="app">
        {/* Sidebar */}
        <div className="sidebar">
          <div className="sidebar-header">
            <div className="sidebar-title">Truthloom</div>
            <div className="sidebar-subtitle">Forensic Truth Ledger</div>
          </div>
          <div className="nav-section">Navigation</div>
          {navItems.map(item => (
            <div key={item.id} className={`nav-item ${nav === item.id ? "active" : ""}`}
                 onClick={() => { setNav(item.id); setAddingTruth(false); }}>
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </div>
          ))}
          <div style={{flex:1}} />
          <div style={{padding:"12px 16px", borderTop:`1px solid ${C.panelBorder}`}}>
            <div style={{fontSize:11,color:C.textDim}}>
              {dataset.mode === "quarantine"
                ? <span style={{color:C.danger}}>🔒 QUARANTINE</span>
                : <span style={{color:C.success}}>✓ NORMAL</span>}
            </div>
          </div>
        </div>

        {/* Main */}
        <div className="main">
          <div className="topbar">
            <div className="topbar-title">{addingTruth ? "Add Truth Record" : topbarTitles[nav]}</div>
            {notification && (
              <div className={`banner banner-${notification.type === "danger" ? "danger" : "success"}`}
                   style={{margin:0, padding:"6px 14px"}}>
                {notification.msg}
              </div>
            )}
          </div>

          <div className="content">
            {/* Modals */}
            {modal?.type === "add_input" && (
              <AddInputModal sourceType={modal.sourceType} onConfirm={handleAddInputConfirm} onCancel={() => setModal(null)} />
            )}
            {modal?.type === "approve" && (
              <Modal title="Approve as Observed Truth"
                     body="You are asserting this record as observed truth. This does not infer parser accuracy. Continue?"
                     confirmLabel="Approve" onConfirm={confirmApprove} onCancel={() => setModal(null)} />
            )}
            {modal?.type === "revoke" && (
              <Modal title="Revoke Observed Truth to Draft"
                     body="This will revoke observed truth status and return the record to draft for editing. Continue?"
                     confirmLabel="Revoke to Draft" onConfirm={confirmRevoke} onCancel={() => setModal(null)} />
            )}
            {modal?.type === "quarantine_confirm" && (
              <Modal title="Enter Quarantine Mode" danger
                     body={`Integrity checks failed: ${modal.reason}. Dataset will enter Quarantine Mode — validation and court-safe exports disabled. Continue?`}
                     confirmLabel="Enter Quarantine" onConfirm={enterQuarantine} onCancel={() => setModal(null)} />
            )}

            {/* Screens */}
            {nav === "home" && !addingTruth && (
              <DatasetHome dataset={dataset} truthRecords={truthRecords} intakeRecords={intakeRecords}
                           onNavigate={setNav} onVerifyDataset={handleVerifyDataset} />
            )}
            {nav === "evidence" && !addingTruth && (
              <EvidenceInputs dataset={dataset} records={intakeRecords}
                              onAddFile={() => addInput("file")} onAddFolder={() => addInput("folder")}
                              onAddIOS={() => addInput("ios")} onAddAndroid={() => addInput("android")}
                              onCopy={handleCopy} onHash={handleHash} onExclude={handleExclude}
                              onVerify={handleVerifyEvidence} />
            )}
            {nav === "truth" && !addingTruth && (
              <TruthLedger dataset={dataset} records={truthRecords}
                           onAdd={() => setAddingTruth(true)}
                           onApprove={handleApprove} onRevoke={handleRevoke}
                           onDelete={handleDelete} onVerify={handleVerifyLedger} />
            )}
            {nav === "audit" && !addingTruth && (
              <AuditLogView entries={auditLog} />
            )}
            {addingTruth && (
              <AddTruthForm onSave={handleSaveTruth} onCancel={() => setAddingTruth(false)} />
            )}
          </div>

          <div className="statusbar">
            <div className="status-dot" style={{background: dataset.mode === "quarantine" ? C.danger : C.success}} />
            <span>{dataset.mode.toUpperCase()}</span>
            <span style={{color: C.textDim}}>|</span>
            <span>{dataset.name}</span>
            <span style={{color: C.textDim}}>|</span>
            <span className="mono">{dataset.dataset_id}</span>
            <span style={{flex:1}} />
            <span>{auditLog.length} audit entries</span>
            <span style={{color: C.textDim}}>|</span>
            <span>{truthRecords.length} truth records</span>
          </div>
        </div>
      </div>
    </>
  );
}
