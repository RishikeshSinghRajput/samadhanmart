import { useEffect, useState } from "react";
import { ArrowRight, BadgeCheck, Check, ChevronDown, CircleCheck, LoaderCircle, ShieldCheck, Smartphone } from "lucide-react";
import api, { getErrorMessage } from "./api.js";
import LocationFields from "./LocationFields.jsx";

const initialForm = { seller_name: "", seller_email: "", seller_phone: "", title: "", description: "", category: "Smartphones", price: "", serial_imei: "", state: "Bihar", district: "Siwan" };

export default function ElectronicsModule({ onJoin }) {
  const [account] = useState(() => {
    try { return JSON.parse(localStorage.getItem("samadhanmart-user") || "null"); }
    catch { return null; }
  });
  const [form, setForm] = useState(initialForm);
  const [items, setItems] = useState([]);
  const [filterLocation, setFilterLocation] = useState({ state: "", district: "" });
  const [loadingItems, setLoadingItems] = useState(true);
  const [challenge, setChallenge] = useState(null);
  const [otps, setOtps] = useState({ EMAIL: "", WHATSAPP: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadItems(location = filterLocation) {
    try {
      const params = {};
      if (location.state) params.state = location.state;
      if (location.district) params.district = location.district;
      const { data } = await api.get("/electronics", { params });
      setItems(data);
    } catch (requestError) {
      setError(getErrorMessage(requestError, "Could not load local listings."));
    } finally {
      setLoadingItems(false);
    }
  }
  useEffect(() => { loadItems(); }, [filterLocation]);

  async function createListing(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const { data } = await api.post("/electronics/create", {
        ...form,
        price: Number(form.price),
      });
      setChallenge(data);
      setOtps(data.development_otps || { EMAIL: "", WHATSAPP: "" });
      setNotice(data.development_otps ? "Demo codes ready — enter both below to publish your listing." : data.message);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function verifyListing(event) {
    event.preventDefault();
    if (!challenge || otps.EMAIL.length !== 6 || otps.WHATSAPP.length !== 6) return;
    setBusy(true);
    setError("");
    try {
      await api.post("/electronics/verify", {
        item_id: challenge.item_id,
        email_otp: otps.EMAIL,
        whatsapp_otp: otps.WHATSAPP,
      });
      setNotice("Verified! Your item is now visible to local buyers.");
      setChallenge(null);
      setOtps({ EMAIL: "", WHATSAPP: "" });
      setForm(initialForm);
      await loadItems();
    } catch (requestError) {
      setError(getErrorMessage(requestError, "That code could not be verified."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="module-layout">
      <div className="panel listing-panel">
        <div className="panel-heading">
          <span className="icon-tile mint"><Smartphone size={20} /></span>
          <div><h3>List an electronic</h3><p>Sell to someone right here in your district.</p></div>
        </div>
        <div className={account?.role === "seller_electronics" && account.approval_status === "APPROVED" ? "seller-approval-hint approved-hint" : "seller-approval-hint"}>
          <ShieldCheck size={16} />
          <span>{account?.role === "seller_electronics" && account.approval_status === "APPROVED"
            ? "Approved by admin. Your listing still needs email and WhatsApp verification."
            : "Seller accounts need admin approval before you can list."}</span>
          {!(account?.role === "seller_electronics" && account.approval_status === "APPROVED") && <button type="button" onClick={onJoin}>Request approval</button>}
        </div>
        {!challenge ? (
          <form className="form-grid" onSubmit={createListing}>
            <label className="field full">Your name<input required minLength="2" maxLength="120" value={form.seller_name} onChange={(e) => setForm({ ...form, seller_name: e.target.value })} placeholder="e.g. Rajesh Kumar" /></label>
            <label className="field">Email address<input type="email" required value={form.seller_email} onChange={(e) => setForm({ ...form, seller_email: e.target.value })} placeholder="you@example.com" /></label>
            <label className="field">WhatsApp number<input type="tel" required pattern="^\+?[0-9\s()\-]{7,20}$" value={form.seller_phone} onChange={(e) => setForm({ ...form, seller_phone: e.target.value })} placeholder="+91 98765 43210" /></label>
            <label className="field full">Item name<input required minLength="2" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Samsung Galaxy A54, 128 GB" /></label>
            <label className="field">Category<span className="select-wrap"><select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}><option>Smartphones</option><option>Laptops</option><option>Televisions</option><option>Home appliances</option><option>Other electronics</option></select><ChevronDown size={16} /></span></label>
            <label className="field">Asking price (₹)<input type="number" min="1" step="0.01" required value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="12,500" /></label>
            <label className="field full">A few details<textarea required minLength="5" rows="2" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Condition, age, what's included…" /></label>
            <label className="field">Serial / IMEI <span className="optional">OPTIONAL</span><input value={form.serial_imei} onChange={(e) => setForm({ ...form, serial_imei: e.target.value })} placeholder="For buyer confidence" /></label>
            <LocationFields className="full location-form-row" state={form.state} district={form.district} onChange={(location) => setForm({ ...form, ...location })} />
            {error && <p className="form-message error full" role="alert">{error}</p>}
            {notice && <p className="form-message success full" role="status">{notice}</p>}
            <button className="button primary full" type="submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <ShieldCheck size={17} />} Verify & list my item <ArrowRight size={16} /></button>
            <p className="secure-note full"><ShieldCheck size={14} /> We verify every listing with a one-time code to help keep this marketplace trusted.</p>
          </form>
        ) : (
          <form className="verify-box" onSubmit={verifyListing}>
            <span className="verify-icon"><BadgeCheck size={27} /></span>
            <h3>One quick check</h3>
            <p>Enter the separate 6-digit codes sent to your email and WhatsApp. Both are needed to publish your listing.</p>
            {Object.entries(challenge.dispatch_statuses || {}).map(([channel, result]) => <span className="dispatch-chip" key={channel}><Check size={13} /> {channel}: {result}</span>)}
            <label className="field code-field">Email verification code<input autoFocus inputMode="numeric" autoComplete="one-time-code" maxLength="6" pattern="[0-9]{6}" required value={otps.EMAIL} onChange={(e) => setOtps({ ...otps, EMAIL: e.target.value.replace(/\D/g, "").slice(0, 6) })} placeholder="000000" /></label>
            <label className="field code-field">WhatsApp verification code<input inputMode="numeric" autoComplete="one-time-code" maxLength="6" pattern="[0-9]{6}" required value={otps.WHATSAPP} onChange={(e) => setOtps({ ...otps, WHATSAPP: e.target.value.replace(/\D/g, "").slice(0, 6) })} placeholder="000000" /></label>
            {error && <p className="form-message error" role="alert">{error}</p>}
            {notice && <p className="form-message success" role="status">{notice}</p>}
            <button className="button primary" disabled={busy || otps.EMAIL.length !== 6 || otps.WHATSAPP.length !== 6}>{busy ? <LoaderCircle className="spin" size={17} /> : <CircleCheck size={17} />} Verify my listing</button>
            <button className="text-button" type="button" onClick={() => { setChallenge(null); setError(""); setNotice(""); }}>Back to listing details</button>
          </form>
        )}
      </div>
      <div className="catalog-column">
        <div className="catalog-intro"><div><span className="eyebrow muted">GOOD FINDS, CLOSE BY</span><h3>From your neighbours</h3></div><span className="count-pill">{items.length} items</span></div>
        <LocationFields className="catalog-location-filter" state={filterLocation.state} district={filterLocation.district} onChange={setFilterLocation} required={false} />
        {error && !challenge && <p className="form-message error" role="alert">{error}</p>}
        {loadingItems ? <div className="loading-state"><LoaderCircle className="spin" size={20} /> Finding verified local listings…</div> : items.length ? <div className="electronics-list">{items.map((item) => (
          <article className="item-card" key={item.item_id}>
            <div className="product-placeholder"><Smartphone size={27} /></div>
            <div className="product-copy"><span className="product-category">{item.category} · {item.district}</span><h4>{item.title}</h4><p>{item.description}</p><strong>₹{Number(item.price).toLocaleString("en-IN")}</strong></div>
            <span className="verified-mark" title="Verified listing"><BadgeCheck size={18} /></span>
          </article>
        ))}</div> : <div className="empty-state"><span className="empty-icon"><Smartphone size={22} /></span><strong>Your next great find is nearby.</strong><span>Verified local listings will show up here.</span></div>}
        <div className="trust-card"><ShieldCheck size={18} /><span><strong>Every seller is verified</strong><small>Listings are checked before they go live.</small></span></div>
      </div>
    </section>
  );
}
