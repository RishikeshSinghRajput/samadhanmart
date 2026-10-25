import { useEffect, useRef, useState } from "react";
import { ArrowRight, FileUp, HeartPulse, LoaderCircle, MapPin, Pill, ShieldCheck } from "lucide-react";
import api, { getErrorMessage } from "./api.js";
import LocationFields from "./LocationFields.jsx";

export default function MedicineStore() {
  const [medicines, setMedicines] = useState([]);
  const [location, setLocation] = useState({ state: "", district: "" });
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ customer_name: "", customer_phone: "", customer_email: "", quantity: 1, is_chronic_refill: false, refill_interval_days: 30 });
  const [prescriptionPath, setPrescriptionPath] = useState("");
  const [fileName, setFileName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const inputRef = useRef(null);

  async function loadMedicines(filters = location) {
    setLoading(true);
    try {
      const params = {};
      if (filters.state) params.state = filters.state;
      if (filters.district) params.district = filters.district;
      const { data } = await api.get("/medicines", { params });
      setMedicines(data);
    }
    catch (requestError) { setError(getErrorMessage(requestError, "Could not load medicines.")); }
    finally { setLoading(false); }
  }
  useEffect(() => { loadMedicines(); }, [location]);

  async function uploadPrescription(file) {
    if (!file) return;
    setBusy(true); setError("");
    try {
      const data = new FormData();
      data.append("file", file);
      const result = await api.post("/medicines/prescriptions", data);
      setPrescriptionPath(result.data.prescription_path);
      setFileName(file.name);
    } catch (requestError) { setError(getErrorMessage(requestError, "Prescription upload failed.")); }
    finally { setBusy(false); }
  }

  async function placeOrder(event) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      const { data } = await api.post("/medicines/order", {
        medicine_id: selected.medicine_id, ...form, quantity: Number(form.quantity),
        prescription_path: prescriptionPath || null,
        refill_interval_days: form.is_chronic_refill ? Number(form.refill_interval_days) : null,
      });
      setNotice(`${data.message} Order #${data.order_id}.`);
      setSelected(null); setPrescriptionPath(""); setFileName("");
      await loadMedicines();
    } catch (requestError) { setError(getErrorMessage(requestError)); }
    finally { setBusy(false); }
  }

  return (
    <section className="store-section">
      <div className="module-banner medicine-banner"><span className="banner-icon"><HeartPulse size={22} /></span><div><h3>Care that’s close to home.</h3><p>Browse local chemist stock and request what you need. Prescription medicines need a valid prescription.</p></div><span className="banner-side"><MapPin size={15} /> YOUR DISTRICT</span></div>
      <LocationFields className="store-location-filter" state={location.state} district={location.district} onChange={setLocation} required={false} />
      {notice && <p className="form-message success" role="status">{notice}</p>}
      {error && !selected && <p className="form-message error" role="alert">{error}</p>}
      {loading ? <div className="loading-state"><LoaderCircle className="spin" size={20} /> Checking local chemist stock…</div> : medicines.length ? <div className="medicine-grid">{medicines.map((medicine) => (
        <article className="medicine-card" key={medicine.medicine_id}>
          <div className="medicine-art"><Pill size={29} /><span>{medicine.batch_number}</span></div>
          <div className="medicine-details"><span className="chemist-tag"><MapPin size={12} /> {medicine.chemist_name} · {medicine.district}, {medicine.state}</span><h3>{medicine.name}</h3><p>{medicine.description || "Genuine medicine, stocked by a local chemist."}</p><div className="medicine-bottom"><strong>₹{Number(medicine.price).toLocaleString("en-IN")}</strong><span>{medicine.stock} in stock</span></div>
            {medicine.prescription_required && <span className="rx-label">Prescription required</span>}
            <button className="button primary order-button" onClick={() => { setSelected(medicine); setError(""); setNotice(""); }}>Request from chemist <ArrowRight size={15} /></button>
          </div>
        </article>
      ))}</div> : <div className="empty-state"><span className="empty-icon"><HeartPulse size={23} /></span><strong>No medicines listed just yet.</strong><span>Check back as local chemists add their stock.</span></div>}
      {selected && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelected(null); }}><section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="order-title">
        <button className="modal-close" onClick={() => setSelected(null)} aria-label="Close">×</button>
        <span className="icon-tile soft-red"><Pill size={20} /></span><h2 id="order-title">Request {selected.name}</h2><p className="modal-subtitle">Your local chemist, {selected.chemist_name}, will confirm your order.</p>
        <form className="modal-form" onSubmit={placeOrder}>
          <label className="field">Your name<input required minLength="2" value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} /></label>
          <label className="field">Phone number<input required type="tel" pattern="^\+?[0-9\s()\-]{7,20}$" value={form.customer_phone} onChange={(e) => setForm({ ...form, customer_phone: e.target.value })} /></label>
          <label className="field">Email address<input required type="email" value={form.customer_email} onChange={(e) => setForm({ ...form, customer_email: e.target.value })} /></label>
          <label className="field">Quantity<input required type="number" min="1" max="100" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></label>
          <label className="refill-choice"><input type="checkbox" checked={form.is_chronic_refill} onChange={(e) => setForm({ ...form, is_chronic_refill: e.target.checked, refill_interval_days: e.target.checked ? 30 : null })} /><span>Request recurring refill<small>For a medicine prescribed for ongoing care.</small></span></label>
          {form.is_chronic_refill && <label className="field full">Remind my chemist every<select value={form.refill_interval_days} onChange={(e) => setForm({ ...form, refill_interval_days: Number(e.target.value) })}><option value="30">30 days</option><option value="60">60 days</option><option value="90">90 days</option></select></label>}
          {selected.prescription_required && <div className="upload-field"><span className="field-label">Prescription <b>REQUIRED</b></span><button type="button" className="upload-button" onClick={() => inputRef.current?.click()}><FileUp size={17} /> {fileName || "Upload prescription (PDF, JPG, PNG)"}</button><input ref={inputRef} type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" hidden onChange={(e) => uploadPrescription(e.target.files?.[0])} /><small>PDF, JPG or PNG · max 10 MB</small></div>}
          {error && <p className="form-message error" role="alert">{error}</p>}
          <button className="button primary" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <ShieldCheck size={17} />} Place medicine request</button>
        </form>
      </section></div>}
    </section>
  );
}
