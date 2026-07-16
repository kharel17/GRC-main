"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import "./landing.css";

/* ─────────────────────────────────────────────
   GRCGuard Landing Page — "Technical Precision"
   ───────────────────────────────────────────── */

export default function LandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="landing-page">
      {/* ───── NAVIGATION ───── */}
      <header className={`landing-nav ${scrolled ? "landing-nav--scrolled" : ""}`}>
        <div className="landing-nav__inner">
          <Link href="/" className="landing-nav__logo" aria-label="GRCGuard Home">
            <span className="landing-nav__logo-mark">GRC</span>
            <span className="landing-nav__logo-text">Guard</span>
          </Link>

          <nav className="landing-nav__links desktop-only" aria-label="Primary">
            <a href="#capabilities" className="landing-nav__link">Control Registry</a>
            <a href="#technical" className="landing-nav__link">Architecture</a>
            <a href="#roadmap" className="landing-nav__link">Roadmap</a>
          </nav>

          <div className="landing-nav__actions desktop-only">
            <Link href="/login" className="landing-btn landing-btn--ghost">Login</Link>
            <a href="#cta" className="landing-btn landing-btn--primary">Request Access</a>
          </div>

          <button
            className="landing-nav__hamburger mobile-only"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
            aria-expanded={mobileMenuOpen}
          >
            <span className={`landing-nav__hamburger-bar ${mobileMenuOpen ? "open" : ""}`} />
            <span className={`landing-nav__hamburger-bar ${mobileMenuOpen ? "open" : ""}`} />
            <span className={`landing-nav__hamburger-bar ${mobileMenuOpen ? "open" : ""}`} />
          </button>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="landing-nav__mobile-menu mobile-only">
            <a href="#capabilities" className="landing-nav__mobile-link" onClick={() => setMobileMenuOpen(false)}>Control Registry</a>
            <a href="#technical" className="landing-nav__mobile-link" onClick={() => setMobileMenuOpen(false)}>Architecture</a>
            <a href="#roadmap" className="landing-nav__mobile-link" onClick={() => setMobileMenuOpen(false)}>Roadmap</a>
            <div className="landing-nav__mobile-divider" />
            <Link href="/login" className="landing-nav__mobile-link" onClick={() => setMobileMenuOpen(false)}>Login</Link>
            <a href="#cta" className="landing-btn landing-btn--primary landing-btn--full" onClick={() => setMobileMenuOpen(false)}>Request Access</a>
          </div>
        )}
      </header>

      {/* ───── HERO ───── */}
      <section className="landing-hero">
        <div className="landing-container landing-hero__inner">
          <div className="landing-hero__content">
            <p className="landing-hero__eyebrow">
              <span className="landing-mono">ISO 27001</span> · <span className="landing-mono">SOC 2</span> · <span className="landing-mono">GDPR</span>
            </p>
            <h1 className="landing-hero__headline">
              Compliance infrastructure,
              <br />
              <span className="landing-hero__headline--accent">not compliance theater.</span>
            </h1>
            <p className="landing-hero__body">
              High-fidelity compliance orchestration for mission-critical
              infrastructure. Eliminate manual audits with real-time control
              monitoring and cryptographic evidence collection.
            </p>
            <div className="landing-hero__actions">
              <a href="#cta" className="landing-btn landing-btn--primary landing-btn--lg">
                Deploy Registry
              </a>
              <a href="#technical" className="landing-btn landing-btn--ghost landing-btn--lg">
                View Architecture →
              </a>
            </div>
          </div>

          <div className="landing-hero__visual">
            <div className="landing-ui-card">
              <div className="landing-ui-card__header">
                <span className="landing-mono landing-ui-card__title">control_registry.db</span>
                <span className="landing-ui-card__status landing-ui-card__status--live">● LIVE</span>
              </div>
              <div className="landing-ui-card__body">
                <div className="landing-ui-card__row">
                  <span className="landing-mono landing-ui-card__label">CTRL</span>
                  <span className="landing-mono">ISO_A5.1.01</span>
                  <span className="landing-ui-card__badge landing-ui-card__badge--pass">PASS</span>
                </div>
                <div className="landing-ui-card__row">
                  <span className="landing-mono landing-ui-card__label">CTRL</span>
                  <span className="landing-mono">ISO_A6.2.03</span>
                  <span className="landing-ui-card__badge landing-ui-card__badge--pass">PASS</span>
                </div>
                <div className="landing-ui-card__row">
                  <span className="landing-mono landing-ui-card__label">CTRL</span>
                  <span className="landing-mono">ISO_A8.1.12</span>
                  <span className="landing-ui-card__badge landing-ui-card__badge--warn">REVIEW</span>
                </div>
                <div className="landing-ui-card__row">
                  <span className="landing-mono landing-ui-card__label">CTRL</span>
                  <span className="landing-mono">ISO_A9.4.02</span>
                  <span className="landing-ui-card__badge landing-ui-card__badge--pass">PASS</span>
                </div>
                <div className="landing-ui-card__row">
                  <span className="landing-mono landing-ui-card__label">CTRL</span>
                  <span className="landing-mono">SOC2_CC6.1</span>
                  <span className="landing-ui-card__badge landing-ui-card__badge--pass">PASS</span>
                </div>
              </div>
              <div className="landing-ui-card__footer">
                <span className="landing-mono">Last sync: <span className="landing-hero__time">2026-07-16T14:32:00Z</span></span>
                <span className="landing-mono">SHA-256 verified ✓</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ───── THE PROBLEM ───── */}
      <section className="landing-section landing-problem">
        <div className="landing-container">
          <h2 className="landing-section__title">THE FRICTION OF LEGACY GRC</h2>
          <div className="landing-problem__grid">
            <div className="landing-problem__col">
              <h3 className="landing-problem__heading">Evidence Decay</h3>
              <p className="landing-problem__body">
                Manual screenshots rot the moment they are
                taken. GRCGuard confirms control adherence
                continuously, eliminating evidence artifacts
                that expire on arrival.
              </p>
              <ul className="landing-problem__list">
                <li>Spreadsheet-based control tracking</li>
                <li>Email-chain audit evidence</li>
                <li>Manual screenshot collection</li>
                <li>Quarterly compliance check-ins</li>
              </ul>
            </div>
            <div className="landing-problem__divider" />
            <div className="landing-problem__col">
              <h3 className="landing-problem__heading">Narrative Fatigue</h3>
              <p className="landing-problem__body">
                Stop writing descriptions for controls you have
                built. Our automated framework mapping engine
                derives control narratives from auditable
                infrastructure-as-code artifacts.
              </p>
              <ul className="landing-problem__list landing-problem__list--highlight">
                <li>Automated control registry</li>
                <li>Cryptographic evidence chain</li>
                <li>Continuous compliance monitoring</li>
                <li>Real-time framework mapping</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ───── CAPABILITIES ───── */}
      <section id="capabilities" className="landing-section landing-capabilities">
        <div className="landing-container">
          <h2 className="landing-section__title">PLATFORM CAPABILITIES</h2>
          <div className="landing-capabilities__grid">
            {/* Capability 1 */}
            <div className="landing-capability">
              <span className="landing-mono landing-capability__number">01</span>
              <h3 className="landing-capability__title">Real-Time Control Mapping</h3>
              <p className="landing-capability__body">
                Visualize your entire compliance posture
                through a live control graph that tracks control
                inheritance across frameworks. Maps ISO 27001
                Annex A controls to SOC 2 Trust Services Criteria
                and GDPR Articles automatically.
              </p>
              <a href="#cta" className="landing-capability__link landing-mono">
                EXPLORE REGISTRY →
              </a>
            </div>

            {/* Capability 2 */}
            <div className="landing-capability">
              <span className="landing-mono landing-capability__number">02</span>
              <h3 className="landing-capability__title">Audit-Ready Reporting</h3>
              <p className="landing-capability__body">
                Generate SOC 2, ISO 27001, and HIPAA reports
                in a single click with verified data lineage.
                Every report links back to source evidence with
                full cryptographic chain of custody.
              </p>
              <a href="#cta" className="landing-capability__link landing-mono">
                VIEW SAMPLE REPORT →
              </a>
            </div>

            {/* Capability 3 */}
            <div className="landing-capability">
              <span className="landing-mono landing-capability__number">03</span>
              <h3 className="landing-capability__title">Multi-Tenant Access</h3>
              <p className="landing-capability__body">
                Row-level data isolation ensures tenant boundaries
                are enforced at the database layer. Role-based access
                control supports auditor, admin, and viewer roles
                with granular permission scoping.
              </p>
              <a href="#cta" className="landing-capability__link landing-mono">
                VIEW ARCHITECTURE →
              </a>
            </div>

            {/* Capability 4 */}
            <div className="landing-capability">
              <span className="landing-mono landing-capability__number">04</span>
              <h3 className="landing-capability__title">Framework Mapping Engine</h3>
              <p className="landing-capability__body">
                Implement one control, satisfy many frameworks.
                Our mapping engine maintains a cross-reference
                database of 114 ISO 27001 controls, 17 SOC 2
                criteria, and 99 GDPR articles.
              </p>
              <a href="#cta" className="landing-capability__link landing-mono">
                EXPLORE MAPPINGS →
              </a>
            </div>
          </div>

          {/* Metric strip */}
          <div className="landing-metrics">
            <div className="landing-metric">
              <span className="landing-metric__label">LATENCY</span>
              <span className="landing-mono landing-metric__value">&lt; 140ms</span>
            </div>
            <div className="landing-metric">
              <span className="landing-metric__label">INTEGRATIONS</span>
              <span className="landing-mono landing-metric__value">2,481 Active</span>
            </div>
            <div className="landing-metric">
              <span className="landing-metric__label">CONTROLS MAPPED</span>
              <span className="landing-mono landing-metric__value">230+</span>
            </div>
            <div className="landing-metric">
              <span className="landing-metric__label">UPTIME</span>
              <span className="landing-mono landing-metric__value">99.98%</span>
            </div>
          </div>
        </div>
      </section>

      {/* ───── TECHNICAL CREDIBILITY ───── */}
      <section id="technical" className="landing-section landing-technical">
        <div className="landing-container">
          <h2 className="landing-section__title">TECHNICAL INTEGRITY</h2>
          <div className="landing-technical__grid">
            <div className="landing-technical__details">
              <div className="landing-technical__item">
                <span className="landing-mono landing-technical__number">01</span>
                <div>
                  <h3 className="landing-technical__heading">Database-Level Isolation</h3>
                  <p className="landing-technical__body">
                    Every tenant&apos;s data is isolated and siloed in a
                    tamper-proof ledger. Row-level security policies
                    enforce boundaries at the SQL layer, not the
                    application layer.
                  </p>
                </div>
              </div>
              <div className="landing-technical__item">
                <span className="landing-mono landing-technical__number">02</span>
                <div>
                  <h3 className="landing-technical__heading">SHA-256 Evidence Tokens</h3>
                  <p className="landing-technical__body">
                    Verify compliance without trusting anyone&apos;s data.
                    We use SHA-256 hashed evidence tokens to create an
                    immutable audit trail for every control assertion.
                  </p>
                </div>
              </div>
              <div className="landing-technical__item">
                <span className="landing-mono landing-technical__number">03</span>
                <div>
                  <h3 className="landing-technical__heading">ISO 27001 Annex A Coverage</h3>
                  <p className="landing-technical__body">
                    Full coverage of all 114 controls across 14 domains.
                    Each control maps to specific implementation guidance,
                    evidence requirements, and test procedures.
                  </p>
                </div>
              </div>
            </div>

            <div className="landing-technical__visual">
              <div className="landing-ui-card landing-ui-card--dark">
                <div className="landing-ui-card__header">
                  <span className="landing-mono landing-ui-card__title">evidence_ledger.log</span>
                </div>
                <div className="landing-ui-card__body landing-ui-card__body--log">
                  <div className="landing-log-line">
                    <span className="landing-mono landing-log-ts">2026-07-16</span>
                    <span className="landing-mono landing-log-id">EVD001</span>
                    <span className="landing-mono">initializing verify_scan: ISO-A5-01-1</span>
                  </div>
                  <div className="landing-log-line">
                    <span className="landing-mono landing-log-ts">2026-07-16</span>
                    <span className="landing-mono landing-log-id">CTRL01</span>
                    <span className="landing-mono">policy check: active → PASS</span>
                  </div>
                  <div className="landing-log-line">
                    <span className="landing-mono landing-log-ts">2026-07-16</span>
                    <span className="landing-mono landing-log-id">CTRL02</span>
                    <span className="landing-mono">access review: compliant → PASS</span>
                  </div>
                  <div className="landing-log-line">
                    <span className="landing-mono landing-log-ts">2026-07-16</span>
                    <span className="landing-mono landing-log-id">SHA256</span>
                    <span className="landing-mono">hash: 8f4e2a...c9d01b</span>
                  </div>
                  <div className="landing-log-line">
                    <span className="landing-mono landing-log-ts">2026-07-16</span>
                    <span className="landing-mono landing-log-id">EVDOK</span>
                    <span className="landing-mono">evidence captured: SUBMITTED_pendi...</span>
                  </div>
                  <div className="landing-log-line">
                    <span className="landing-mono landing-log-ts">2026-07-16</span>
                    <span className="landing-mono landing-log-id">AUDIT</span>
                    <span className="landing-mono">ledger sealed → immutable ✓</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ───── ROADMAP ───── */}
      <section id="roadmap" className="landing-section landing-roadmap">
        <div className="landing-container">
          <h2 className="landing-section__title">DEVELOPMENT ROADMAP</h2>
          <div className="landing-roadmap__timeline">
            <div className="landing-roadmap__track" />
            <div className="landing-roadmap__items">
              <div className="landing-roadmap__item landing-roadmap__item--shipped">
                <div className="landing-roadmap__dot" />
                <div className="landing-roadmap__card">
                  <span className="landing-mono landing-roadmap__date">Q1 2025</span>
                  <span className="landing-roadmap__badge landing-roadmap__badge--shipped">SHIPPED</span>
                  <p className="landing-roadmap__label">Core Control Registry &amp; Multi-tenant Infrastructure</p>
                </div>
              </div>
              <div className="landing-roadmap__item landing-roadmap__item--shipped">
                <div className="landing-roadmap__dot" />
                <div className="landing-roadmap__card">
                  <span className="landing-mono landing-roadmap__date">Q2 2025</span>
                  <span className="landing-roadmap__badge landing-roadmap__badge--shipped">SHIPPED</span>
                  <p className="landing-roadmap__label">ISO 27001 Framework Mapping &amp; Evidence Collection</p>
                </div>
              </div>
              <div className="landing-roadmap__item landing-roadmap__item--shipped">
                <div className="landing-roadmap__dot" />
                <div className="landing-roadmap__card">
                  <span className="landing-mono landing-roadmap__date">Q3 2025</span>
                  <span className="landing-roadmap__badge landing-roadmap__badge--shipped">SHIPPED</span>
                  <p className="landing-roadmap__label">Self-Healing Infrastructure Integrations</p>
                </div>
              </div>
              <div className="landing-roadmap__item landing-roadmap__item--active">
                <div className="landing-roadmap__dot" />
                <div className="landing-roadmap__card">
                  <span className="landing-mono landing-roadmap__date">Q4 2025</span>
                  <span className="landing-roadmap__badge landing-roadmap__badge--progress">IN PROGRESS</span>
                  <p className="landing-roadmap__label">Predictive Compliance AI &amp; GDPR Automation</p>
                </div>
              </div>
              <div className="landing-roadmap__item landing-roadmap__item--planned">
                <div className="landing-roadmap__dot" />
                <div className="landing-roadmap__card">
                  <span className="landing-mono landing-roadmap__date">Q1 2026</span>
                  <span className="landing-roadmap__badge landing-roadmap__badge--planned">PLANNED</span>
                  <p className="landing-roadmap__label">Post-Quantum Cryptographic Proofs</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ───── CLOSING CTA ───── */}
      <section id="cta" className="landing-cta">
        <div className="landing-container landing-cta__inner">
          <h2 className="landing-cta__headline">
            TRANSITION TO HIGH-FIDELITY
            <br />
            GOVERNANCE
          </h2>
          <p className="landing-cta__body">
            Stop fighting with spreadsheets. Start orchestrating your
            security posture with GRCGuard.
          </p>
          <div className="landing-cta__actions">
            <a href="mailto:access@grcguard.io" className="landing-btn landing-btn--primary-inv landing-btn--lg">
              Request Beta Access
            </a>
            <a href="#technical" className="landing-btn landing-btn--ghost-inv landing-btn--lg">
              Schedule Technical Demo
            </a>
          </div>
        </div>
      </section>

      {/* ───── FOOTER ───── */}
      <footer className="landing-footer">
        <div className="landing-container landing-footer__inner">
          <div className="landing-footer__brand">
            <span className="landing-nav__logo-mark">GRC</span>
            <span className="landing-nav__logo-text">Guard</span>
            <p className="landing-footer__tagline">
              Engineering precision into the fabric of
              <br />
              corporate governance and risk mitigation.
            </p>
          </div>
          <div className="landing-footer__cols">
            <div className="landing-footer__col">
              <h4 className="landing-footer__col-title">RESOURCES</h4>
              <a href="#" className="landing-footer__link">Documentation</a>
              <a href="#" className="landing-footer__link">System Status</a>
              <a href="#" className="landing-footer__link">Changelog</a>
            </div>
            <div className="landing-footer__col">
              <h4 className="landing-footer__col-title">COMPANY</h4>
              <a href="#technical" className="landing-footer__link">Architecture</a>
              <a href="#roadmap" className="landing-footer__link">Roadmap</a>
              <a href="#" className="landing-footer__link">About</a>
            </div>
            <div className="landing-footer__col">
              <h4 className="landing-footer__col-title">LEGAL</h4>
              <a href="#" className="landing-footer__link">Security Policy</a>
              <a href="#" className="landing-footer__link">Privacy</a>
              <a href="#" className="landing-footer__link">Terms</a>
            </div>
          </div>
        </div>
        <div className="landing-footer__bottom">
          <div className="landing-container">
            <p className="landing-mono">© 2025 GRCGUARD SYSTEMS. ALL RIGHTS RESERVED.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
