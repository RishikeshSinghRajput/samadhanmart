import { useEffect, useState } from "react";
import { Activity, BadgeCheck, BriefcaseBusiness, Check, LoaderCircle, LockKeyhole, LogOut, ShieldCheck, Store, X } from "lucide-react";
import api, { getErrorMessage } from "../api.js";

const roleNames = {
  seller_electronics: "Electronics seller",
  seller_medicine: "Medical seller / chemist",
  advocate: "Advocate",
};

function AdminSignIn({ onSignedIn }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function signIn(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/auth/login", form);
      if (data.role !== "admin" || data.is_admin !== true) {
        throw new Error("This account does not have administrator access.");
      }
      localStorage.setItem("samadhanmart-token", data.access_token);
      localStorage.setItem("samadhanmart-user", JSON.stringify(data));
      onSignedIn(data);
    } catch (requestError) {
      setError(requestError.response ? getErrorMessage(requestError) : requestError.message || getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  return <section className="panel admin-login">
    <span className="icon-tile mint"><ShieldCheck size={21} /></span>
    <span className="eyebrow muted">RESTRICTED ADMINISTRATION</span>
    <h2>Admin sign in</h2>
    <p>Only manually provisioned administrator accounts can access approvals and activity.</p>
    {error && <p className="form-message error" role="alert">{error}</p>}
    <form className="form-grid" onSubmit={signIn}>
      <label className="field full">Admin email<input required type="email" autoComplete="username" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
      <label className="field full">Password<input required type="password" autoComplete="current-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
      <button className="button primary full" disabled={busy}>{busy ? <LoaderCircle size={16} className="spin" /> : <LockKeyhole size={16} />} Sign in</button>
    </form>
  </section>;
}

function AdminDashboard({ user, onLogout }) {
  const [requests, setRequests] = useState([]);
  const [activities, setActivities] = useState([]);
  const [filter, setFilter] = useState("PENDING");
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const token = localStorage.getItem("samadhanmart-token");

  async function loadDashboard() {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [requestResult, activityResult] = await Promise.all([
        api.get("/admin/requests", { params: filter ? { approval_status: filter } : {}, headers }),
        api.get("/admin/activity?limit=100", { headers }),
      ]);
      setRequests(requestResult.data);
      setActivities(activityResult.data);
      setError("");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      if (requestError.response?.status === 401 || requestError.response?.status === 403) onLogout();
    }
  }

  useEffect(() => { loadDashboard(); }, [filter]);

  async function decide(request, decision) {
    setBusyId(request.user_id);
    setError("");
    setNotice("");
    try {
      await api.post(`/admin/requests/${request.user_id}/decision`, { decision }, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setNotice(`${request.full_name} — ${roleNames[request.role] || request.role} ${decision.toLowerCase()} by admin.`);
      await loadDashboard();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyId(null);
    }
  }

  return <section className="admin-dashboard">
    <div className="admin-welcome">
      <div><span className="eyebrow"><ShieldCheck size={13} /> ADMIN CONSOLE</span><h2>Welcome, {user.full_name}</h2><p>Review registration requests and follow activity across SamadhanMart.</p></div>
      <button className="button secondary" onClick={onLogout}><LogOut size={15} /> Sign out</button>
    </div>
    {error && <p className="form-message error" role="alert">{error}</p>}
    {notice && <p className="form-message success" role="status">{notice}</p>}
    <div className="admin-layout">
      <section className="panel admin-requests">
        <div className="admin-section-heading"><div><span className="eyebrow muted">ACCOUNT REVIEW</span><h3>Registration requests</h3></div><select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="PENDING">Pending</option><option value="APPROVED">Approved</option><option value="REJECTED">Rejected</option><option value="">All requests</option></select></div>
        {requests.length ? <div className="request-list">{requests.map((request) => <article className="request-card" key={request.user_id}>
          <div className="request-top"><span className="request-avatar"><BriefcaseBusiness size={17} /></span><span className={`approval-status ${request.approval_status.toLowerCase()}`}>{request.approval_status}</span></div>
          <h4>{request.full_name}</h4><p className="request-role">{roleNames[request.role]}</p>
          <div className="request-details"><span>{request.email}</span><span>{request.phone}</span><span>{request.state}, {request.district}</span></div>
          {request.advocate && <div className="advocate-review"><strong>Advocate profile</strong><span>Bar Council: {request.advocate.bar_council_number}</span><span>{request.advocate.experience_years} years · {request.advocate.specialization} · ₹{Number(request.advocate.consultation_fee).toLocaleString("en-IN")}</span></div>}
          {request.approval_note && <p className="approval-note">Admin note: {request.approval_note}</p>}
          {request.approval_status === "PENDING" && <div className="request-actions"><button className="button primary" disabled={busyId === request.user_id} onClick={() => decide(request, "APPROVED")}><Check size={14} /> Approve</button><button className="button reject" disabled={busyId === request.user_id} onClick={() => decide(request, "REJECTED")}><X size={14} /> Reject</button></div>}
        </article>)}</div> : <div className="empty-state compact-empty"><span className="empty-icon"><BadgeCheck size={20} /></span><strong>No {filter.toLowerCase()} requests.</strong><span>Registration submissions will appear here.</span></div>}
      </section>
      <section className="panel activity-panel">
        <div className="admin-section-heading"><div><span className="eyebrow muted">AUDIT TRAIL</span><h3><Activity size={16} /> Recent activity</h3></div></div>
        {activities.length ? <div className="activity-list">{activities.map((activity) => <article className="activity-row" key={activity.activity_id}><span className="activity-dot" /><div><strong>{activity.action.replaceAll("_", " ").toLowerCase()}</strong><p>{activity.description}</p><small>{new Date(activity.created_at).toLocaleString()}</small></div></article>)}</div> : <div className="empty-state compact-empty"><strong>No activity recorded yet.</strong></div>}
      </section>
    </div>
  </section>;
}

export default function AdminPortal() {
  const [user, setUser] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("samadhanmart-user") || "null");
      return saved?.role === "admin" && saved?.is_admin === true ? saved : null;
    } catch {
      return null;
    }
  });

  function logout() {
    localStorage.removeItem("samadhanmart-token");
    localStorage.removeItem("samadhanmart-user");
    setUser(null);
  }

  return <div className="app-shell admin-shell">
    <header className="topbar">
      <a className="brand" href="/" aria-label="SamadhanMart home"><span className="brand-mark"><Store size={20} strokeWidth={2.4} /></span><span>samadhan<span className="brand-accent">mart</span><small>ADMINISTRATION</small></span></a>
      <a className="button secondary" href="/">Back to marketplace</a>
    </header>
    <main className="admin-main">{user ? <AdminDashboard user={user} onLogout={logout} /> : <AdminSignIn onSignedIn={setUser} />}</main>
  </div>;
}
