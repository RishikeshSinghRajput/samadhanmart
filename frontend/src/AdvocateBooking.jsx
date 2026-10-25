import { useEffect, useState } from "react";
import { ArrowRight, BadgeCheck, CalendarDays, Clock3, LoaderCircle, Scale, ShieldCheck } from "lucide-react";
import api, { getErrorMessage } from "./api.js";
import LocationFields from "./LocationFields.jsx";

const specializations = ["All specializations", "Civil", "Criminal", "Corporate", "Land Disputes"];

export default function AdvocateBooking() {
  const [advocates, setAdvocates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [specialization, setSpecialization] = useState("");
  const [location, setLocation] = useState({ state: "", district: "" });
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ client_name: "", client_email: "", client_phone: "", slot_start: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadAdvocates(filter = specialization, filters = location) {
    setLoading(true);
    try {
      const params = {};
      if (filter) params.specialization = filter;
      if (filters.state) params.state = filters.state;
      if (filters.district) params.district = filters.district;
      const { data } = await api.get("/advocates", { params });
      setAdvocates(data);
    } catch (requestError) { setError(getErrorMessage(requestError, "Could not load advocates.")); }
    finally { setLoading(false); }
  }
  useEffect(() => { loadAdvocates(); }, [specialization, location]);

  async function book(event) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      const { data } = await api.post("/advocates/book", {
        advocate_id: selected.advocate_id, ...form,
        slot_start: new Date(form.slot_start).toISOString(),
      });
      setNotice(`Consultation booked for ${new Date(data.slot_start).toLocaleString()}.`);
      setSelected(null);
    } catch (requestError) { setError(getErrorMessage(requestError)); }
    finally { setBusy(false); }
  }

  const minimumSlot = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  return (
    <section className="directory-section">
      <div className="module-banner legal-banner"><span className="banner-icon"><Scale size={22} /></span><div><h3>The right guidance makes all the difference.</h3><p>Meet verified advocates who understand your local community and the issues that matter here.</p></div><span className="banner-side"><ShieldCheck size={15} /> BAR COUNCIL CHECKED</span></div>
      <div className="directory-toolbar"><div><span className="eyebrow muted">YOUR LOCAL LEGAL DIRECTORY</span><h3>Find your advocate</h3></div><label className="filter-select"><span className="sr-only">Filter by specialization</span><select value={specialization} onChange={(e) => setSpecialization(e.target.value === "All specializations" ? "" : e.target.value)}>{specializations.map((value) => <option key={value} value={value === "All specializations" ? "" : value}>{value}</option>)}</select></label></div>
      <LocationFields className="directory-location-filter" state={location.state} district={location.district} onChange={setLocation} required={false} />
      {notice && <p className="form-message success" role="status">{notice}</p>}
      {error && !selected && <p className="form-message error" role="alert">{error}</p>}
      {loading ? <div className="loading-state"><LoaderCircle className="spin" size={20} /> Finding verified advocates…</div> : advocates.length ? <div className="advocate-grid">{advocates.map((advocate) => (
        <article className="advocate-card" key={advocate.advocate_id}>
          <div className="advocate-top"><div className="avatar">{advocate.full_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</div><span className="verified-label"><BadgeCheck size={14} /> VERIFIED</span></div>
          <span className="specialization-tag">{advocate.specialization}</span><h3>{advocate.full_name}</h3><p className="bar-number">BAR COUNCIL · {advocate.bar_council_number}</p>
          <div className="advocate-facts"><span><Clock3 size={14} /> {advocate.experience_years} years’ experience</span><span>{advocate.district}, {advocate.state}</span></div>
          <div className="advocate-footer"><span><small>CONSULTATION</small><strong>₹{Number(advocate.consultation_fee).toLocaleString("en-IN")}</strong></span><button className="button primary" onClick={() => { setSelected(advocate); setError(""); setNotice(""); }}>Book a slot <ArrowRight size={14} /></button></div>
        </article>
      ))}</div> : <div className="empty-state"><span className="empty-icon"><Scale size={23} /></span><strong>No advocates found for this search.</strong><span>Try another specialization or check back soon.</span></div>}
      {selected && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelected(null); }}><section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="booking-title">
        <button className="modal-close" onClick={() => setSelected(null)} aria-label="Close">×</button>
        <span className="icon-tile lavender"><CalendarDays size={20} /></span><h2 id="booking-title">Book a consultation</h2><p className="modal-subtitle">With {selected.full_name} · ₹{Number(selected.consultation_fee).toLocaleString("en-IN")} per session</p>
        <form className="modal-form" onSubmit={book}>
          <label className="field">Your name<input required minLength="2" value={form.client_name} onChange={(e) => setForm({ ...form, client_name: e.target.value })} /></label>
          <label className="field">Email address<input required type="email" value={form.client_email} onChange={(e) => setForm({ ...form, client_email: e.target.value })} /></label>
          <label className="field">Phone number<input required type="tel" pattern="^\+?[0-9\s()\-]{7,20}$" value={form.client_phone} onChange={(e) => setForm({ ...form, client_phone: e.target.value })} /></label>
          <label className="field full">Preferred date & time<input required type="datetime-local" min={minimumSlot} value={form.slot_start} onChange={(e) => setForm({ ...form, slot_start: e.target.value })} /></label>
          {error && <p className="form-message error full" role="alert">{error}</p>}
          <button className="button primary full" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <CalendarDays size={17} />} Reserve this slot</button>
        </form>
      </section></div>}
    </section>
  );
}
