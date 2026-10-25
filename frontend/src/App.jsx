import { useState } from "react";
import { ArrowUpRight, HeartPulse, Scale, ShoppingBag, Store, UserRoundPlus } from "lucide-react";
import ElectronicsModule from "./ElectronicsModule.jsx";
import MedicineStore from "./MedicineStore.jsx";
import AdvocateBooking from "./AdvocateBooking.jsx";
import AccountPortal from "./AccountPortal.jsx";
import AdminPortal from "./admin/AdminPortal.jsx";

const modules = [
  { id: "electronics", label: "Electronics", icon: ShoppingBag },
  { id: "medicines", label: "Medicines", icon: HeartPulse },
  { id: "advocates", label: "Legal help", icon: Scale },
  { id: "account", label: "Seller / Advocate", icon: UserRoundPlus },
];

export default function App() {
  const [active, setActive] = useState("electronics");

  if (window.location.pathname === "/admin") return <AdminPortal />;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#" onClick={() => setActive("electronics")} aria-label="SamadhanMart home">
          <span className="brand-mark"><Store size={20} strokeWidth={2.4} /></span>
          <span>samadhan<span className="brand-accent">mart</span><small>YOUR DISTRICT, SORTED</small></span>
        </a>
        <nav className="main-nav" aria-label="Marketplace sections">
          {modules.map(({ id, label, icon: Icon }) => (
            <button key={id} className={active === id ? "nav-link active" : "nav-link"} onClick={() => setActive(id)}>
              <Icon size={17} /> {label}
            </button>
          ))}
        </nav>
        <button className="district-pill"><span className="status-dot" /> Bihar <span className="district-name">· Sheohar</span></button>
      </header>

      <main>
        <section className="welcome-band">
          <div className="welcome-copy">
            <span className="eyebrow"><span className="status-dot" /> MADE FOR YOUR NEIGHBOURHOOD</span>
            <h1>Good things are <em>closer</em> than you think.</h1>
            <p>Shop local, find the right care, and get trusted advice — all from the people who know your district.</p>
          </div>
          <div className="welcome-note"><span className="note-icon"><ArrowUpRight size={19} /></span><span>Rooted in Bihar.<br /><strong>Here for you.</strong></span></div>
          <span className="hero-orbit orbit-one" /><span className="hero-orbit orbit-two" />
        </section>
        <div className="section-heading">
          <div><span className="eyebrow muted">THE SAMADHANMART DIRECTORY</span><h2>What can we help with?</h2></div>
          <span className="trusted-label"><span className="status-dot" /> Local. Verified. Here for you.</span>
        </div>
        {active === "electronics" && <ElectronicsModule onJoin={() => setActive("account")} />}
        {active === "medicines" && <MedicineStore />}
        {active === "advocates" && <AdvocateBooking />}
        {active === "account" && <AccountPortal />}
      </main>
      <footer className="footer"><span>© 2025 SamadhanMart</span><span>Built with care for Bihar’s local communities</span></footer>
    </div>
  );
}
