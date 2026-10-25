import { useEffect, useState } from "react";
import { BadgeCheck, Clock3, LoaderCircle, LockKeyhole, LogOut, ShieldCheck, UserRoundPlus } from "lucide-react";
import api, { getErrorMessage } from "./api.js";
import LocationFields from "./LocationFields.jsx";

const emptyRegistration = {
  full_name: "", email: "", phone: "", password: "", role: "seller_electronics", state: "Bihar", district: "",
  bar_council_number: "", experience_years: "", consultation_fee: "", specialization: "Civil",
};
const roleNames = {
  seller_electronics: "Electronics seller",
  seller_medicine: "Medical seller / chemist",
  advocate: "Advocate",
};

function RegistrationForm() {
  const [mode, setMode] = useState("register");
  const [form, setForm] = useState(emptyRegistration);
  const [login, setLogin] = useState({ email: "", password: "" });
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("samadhanmart-user") || "null"); }
    catch { return null; }
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (user?.is_admin) window.location.replace("/admin");
  }, [user]);

  async function register(event) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    const payload = { ...form };
    if (payload.role === "advocate") {
      payload.experience_years = Number(payload.experience_years);
      payload.consultation_fee = Number(payload.consultation_fee);
    } else {
      delete payload.bar_council_number;
      delete payload.experience_years;
      delete payload.consultation_fee;
      delete payload.specialization;
    }
    try {
      const { data } = await api.post("/auth/register", payload);
      setNotice(data.message);
      setMode("login");
      setLogin({ email: form.email, password: "" });
    } catch (requestError) { setError(getErrorMessage(requestError)); }
    finally { setBusy(false); }
  }

  async function signIn(event) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      const { data } = await api.post("/auth/login", login);
      localStorage.setItem("samadhanmart-token", data.access_token);
      localStorage.setItem("samadhanmart-user", JSON.stringify(data));
      setUser(data);
      if (data.is_admin) window.location.assign("/admin");
    } catch (requestError) { setError(getErrorMessage(requestError)); }
    finally { setBusy(false); }
  }

  function logout() {
    localStorage.removeItem("samadhanmart-token");
    localStorage.removeItem("samadhanmart-user");
    setUser(null);
    setMode("login");
  }

  if (user && !user.is_admin) {
    return <section className="panel approval-result">
      <span className="icon-tile mint"><BadgeCheck size={21} /></span>
      <div><span className="eyebrow muted">ACCOUNT STATUS</span><h2>Approved by admin</h2><p>Your {roleNames[user.role] || "account"} is approved. You can now use the SamadhanMart marketplace.</p></div>
      <button className="button secondary" onClick={logout}><LogOut size={15} /> Sign out</button>
    </section>;
  }

  return (
    <div className="account-grid">
      <section className="panel account-panel">
        <div className="panel-heading"><span className="icon-tile mint"><UserRoundPlus size={20} /></span><div><h3>Join SamadhanMart</h3><p>Seller and advocate accounts are reviewed by an admin.</p></div></div>
        <div className="account-tabs"><button className={mode === "register" ? "selected" : ""} onClick={() => { setMode("register"); setError(""); }}>Request registration</button><button className={mode === "login" ? "selected" : ""} onClick={() => { setMode("login"); setError(""); }}>Seller / advocate sign in</button></div>
        {error && <p className="form-message error" role="alert">{error}</p>}
        {notice && <p className="form-message success" role="status">{notice}</p>}
        {mode === "register" ? <form className="form-grid account-form" onSubmit={register}>
          <label className="field full">I want to join as<select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}><option value="seller_electronics">Electronics seller</option><option value="seller_medicine">Medical seller / chemist</option><option value="advocate">Advocate</option></select></label>
          <label className="field full">Full name / business name<input required minLength="2" maxLength="120" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
          <label className="field">Email address<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
          <label className="field">Phone / WhatsApp<input required type="tel" pattern="^\+?[0-9\s()\-]{7,20}$" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
          <label className="field full">Password <span className="optional">12 CHARACTERS MIN.</span><input required type="password" minLength="12" maxLength="128" autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
          <LocationFields className="full location-form-row" state={form.state} district={form.district} onChange={(location) => setForm({ ...form, ...location })} />
          {form.role === "advocate" && <>
            <label className="field full">Bar Council ID<input required maxLength="80" value={form.bar_council_number} onChange={(e) => setForm({ ...form, bar_council_number: e.target.value })} /></label>
            <label className="field">Years of experience<input required type="number" min="0" max="70" value={form.experience_years} onChange={(e) => setForm({ ...form, experience_years: e.target.value })} /></label>
            <label className="field">Consultation fee (₹)<input required type="number" min="0" step="0.01" value={form.consultation_fee} onChange={(e) => setForm({ ...form, consultation_fee: e.target.value })} /></label>
            <label className="field full">Specialization<select value={form.specialization} onChange={(e) => setForm({ ...form, specialization: e.target.value })}><option>Civil</option><option>Criminal</option><option>Corporate</option><option>Land Disputes</option></select></label>
          </>}
          <p className="approval-explainer full"><Clock3 size={15} /> Your account stays pending until an administrator reviews your details.</p>
          <button className="button primary full" disabled={busy}>{busy ? <LoaderCircle size={16} className="spin" /> : <ShieldCheck size={16} />} Request approval</button>
        </form> : <form className="form-grid account-form" onSubmit={signIn}>
          <label className="field full">Email address<input required type="email" value={login.email} onChange={(e) => setLogin({ ...login, email: e.target.value })} /></label>
          <label className="field full">Password<input required type="password" autoComplete="current-password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} /></label>
          <button className="button primary full" disabled={busy}>{busy ? <LoaderCircle size={16} className="spin" /> : <LockKeyhole size={16} />} Sign in</button>
        </form>}
      </section>
      <aside className="account-aside">
        <span className="icon-tile lavender"><ShieldCheck size={21} /></span>
        <h3>Trusted starts with the right checks.</h3>
        <p>Every seller and advocate registration is reviewed before their account can provide services on the marketplace.</p>
        <div className="approval-step"><span>1</span><div><strong>Send your request</strong><small>Tell us about yourself and your service.</small></div></div>
        <div className="approval-step"><span>2</span><div><strong>Admin reviews your details</strong><small>Advocate registrations include Bar Council ID review.</small></div></div>
        <div className="approval-step"><span>3</span><div><strong>See your approval status</strong><small>After approval, sign in to access your role.</small></div></div>
      </aside>
    </div>
  );
}

export default function AccountPortal() {
  return <section className="account-section">
    <div className="directory-toolbar"><div><span className="eyebrow muted">JOIN THE LOCAL MARKETPLACE</span><h3>Seller & advocate access</h3></div></div>
    <RegistrationForm />
  </section>;
}
