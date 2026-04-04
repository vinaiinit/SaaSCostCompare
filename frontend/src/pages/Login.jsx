import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authAPI, contactAPI } from '../api';

const insightsData = [
  { stat: '68%', insight: 'of enterprises overpay for cloud licences by at least 20% compared to negotiated peer benchmarks.', category: 'Cloud Licensing' },
  { stat: '41%', insight: 'of SaaS tools purchased by enterprises are duplicated by another tool already in the portfolio.', category: 'Portfolio Overlap' },
  { stat: '3.2x', insight: 'return on investment organisations typically see from a single benchmarking engagement within 12 months.', category: 'ROI' },
  { stat: '29%', insight: 'of enterprise Salesforce customers are on a tier above what their usage data justifies.', category: 'Salesforce' },
  { stat: '54%', insight: 'of Microsoft EA renewals are signed without peer benchmark data — leaving money on the table.', category: 'Microsoft' },
];

function InsightsCarousel() {
  const [current, setCurrent] = useState(0);
  const total = insightsData.length;

  const next = useCallback(() => setCurrent((prev) => (prev + 1) % (total - 2)), [total]);
  const prev = () => setCurrent((p) => (p - 1 + (total - 2)) % (total - 2));

  useEffect(() => {
    const timer = setInterval(next, 4000);
    return () => clearInterval(timer);
  }, [next]);

  const visible = [
    insightsData[current % total],
    insightsData[(current + 1) % total],
    insightsData[(current + 2) % total],
  ];

  return (
    <section id="insights" className="py-24 bg-[#001f4d] text-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <p className="text-xs font-bold tracking-widest uppercase text-blue-300 mb-3">Market Intelligence</p>
          <h2 className="text-4xl font-extrabold mb-4">What Our Research Shows</h2>
          <p className="text-blue-200 max-w-2xl mx-auto">
            Powered by over 50 years of collective expertise in technology and cost benchmarking, and informed by real-time deal data across ANZ, UK, and North America.
          </p>
        </div>

        <div className="relative">
          <div className="grid md:grid-cols-3 gap-8">
            {visible.map(({ stat, insight, category }) => (
              <div
                key={category}
                className="bg-white/10 border border-white/20 rounded-xl p-6 hover:bg-white/15 transition-all duration-500"
              >
                <p className="text-xs font-bold tracking-widest uppercase text-blue-300 mb-3">{category}</p>
                <p className="text-4xl font-extrabold text-white mb-3">{stat}</p>
                <p className="text-sm text-blue-100 leading-relaxed">{insight}</p>
              </div>
            ))}
          </div>

          {/* Navigation arrows */}
          <button
            onClick={prev}
            className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-4 w-10 h-10 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center transition"
          >
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            onClick={next}
            className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-4 w-10 h-10 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center transition"
          >
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {/* Dots */}
        <div className="flex justify-center gap-2 mt-8">
          {Array.from({ length: total - 2 }).map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrent(i)}
              className={`w-2.5 h-2.5 rounded-full transition ${i === current ? 'bg-blue-300' : 'bg-white/30 hover:bg-white/50'}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function ContactSection() {
  const [form, setForm] = useState({ name: '', email: '', company: '', message: '' });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await contactAPI.submit(form.name, form.email, form.company, form.message);
      setSubmitted(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  return (
    <section id="contact" className="py-24 bg-slate-50">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid md:grid-cols-2 gap-16">
          {/* Left — info */}
          <div>
            <p className="text-xs font-bold tracking-widest uppercase text-[#003366] mb-3">Get In Touch</p>
            <h2 className="text-4xl font-extrabold text-slate-900 leading-tight mb-6">
              Let's Talk About Your<br />SaaS Spend
            </h2>
            <p className="text-slate-600 leading-relaxed mb-8">
              Whether you're preparing for a major vendor renewal, exploring cost optimisation, or just
              want to understand how your SaaS spend compares — we're here to help.
            </p>

            <div className="space-y-5">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-[#003366]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-[#003366]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-slate-900 text-sm">Email Us</p>
                  <p className="text-slate-600 text-sm">info@saascostcompare.com</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-[#003366]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-[#003366]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-slate-900 text-sm">Location</p>
                  <p className="text-slate-600 text-sm">Sydney, Australia</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-[#003366]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-[#003366]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-slate-900 text-sm">Response Time</p>
                  <p className="text-slate-600 text-sm">We typically respond within 24 hours</p>
                </div>
              </div>
            </div>
          </div>

          {/* Right — form */}
          <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">
            {submitted ? (
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-[#003366] mb-2">Message Sent</h3>
                <p className="text-sm text-slate-500">Thank you for reaching out. We'll get back to you shortly.</p>
              </div>
            ) : (
              <>
                <h3 className="text-xl font-bold text-[#003366] mb-1">Send Us a Message</h3>
                <p className="text-sm text-slate-500 mb-6">Fill out the form below and we'll be in touch.</p>

                {error && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">{error}</div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Name</label>
                      <input
                        type="text"
                        value={form.name}
                        onChange={update('name')}
                        className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003366] focus:border-transparent"
                        placeholder="Your name"
                        required
                        disabled={loading}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Email</label>
                      <input
                        type="email"
                        value={form.email}
                        onChange={update('email')}
                        className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003366] focus:border-transparent"
                        placeholder="you@company.com"
                        required
                        disabled={loading}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Company</label>
                    <input
                      type="text"
                      value={form.company}
                      onChange={update('company')}
                      className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003366] focus:border-transparent"
                      placeholder="Your company name"
                      disabled={loading}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Message</label>
                    <textarea
                      value={form.message}
                      onChange={update('message')}
                      rows={4}
                      className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003366] focus:border-transparent resize-none"
                      placeholder="Tell us about your SaaS spend or what you'd like to discuss..."
                      required
                      disabled={loading}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-[#003366] hover:bg-[#004080] text-white font-semibold py-3 rounded-lg transition disabled:opacity-50"
                  >
                    {loading ? 'Sending...' : 'Send Message'}
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await authAPI.login(email, password);
      const token = response.data.access_token;
      localStorage.setItem('token', token);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please check your email and password.');
    } finally {
      setLoading(false);
    }
  };

  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-white font-sans">

      {/* ── NAVBAR ── */}
      <header className="fixed top-0 inset-x-0 z-50 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#003366] rounded flex items-center justify-center">
              <span className="text-white text-xs font-bold">SC</span>
            </div>
            <span className="text-xl font-bold text-[#003366] tracking-tight">SaaSCostCompare</span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            <button onClick={() => scrollTo('about')} className="hover:text-[#003366] transition">About</button>
            <button onClick={() => scrollTo('services')} className="hover:text-[#003366] transition">Services</button>
            <button onClick={() => scrollTo('how-it-works')} className="hover:text-[#003366] transition">How It Works</button>
            <button onClick={() => scrollTo('insights')} className="hover:text-[#003366] transition">Insights</button>
            <button onClick={() => scrollTo('contact')} className="hover:text-[#003366] transition">Contact</button>
          </nav>
          <div className="flex items-center gap-3">
            <button
              onClick={() => scrollTo('login-form')}
              className="text-sm font-medium text-[#003366] hover:underline"
            >
              Sign In
            </button>
            <Link
              to="/register"
              className="text-sm font-medium bg-[#003366] text-white px-4 py-2 rounded hover:bg-[#004080] transition"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* ── HERO ── */}
      <section className="pt-24 bg-gradient-to-br from-[#001f4d] via-[#003366] to-[#004a99] text-white">
        <div className="max-w-7xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-16 items-center">

          {/* Left — copy */}
          <div>
            <p className="text-xs font-bold tracking-widest uppercase text-blue-300 mb-4">
              Enterprise SaaS Intelligence
            </p>
            <h1 className="text-5xl font-extrabold leading-tight mb-6">
              Know Exactly How Much You Can<br />
              <span className="text-blue-300">Save on SaaS Costs.</span>
            </h1>
            <p className="text-lg text-blue-100 leading-relaxed mb-8">
              SaaSCostCompare delivers independent benchmarking and peer comparisons
              so your organisation can negotiate smarter, cut waste, and justify
              every dollar spent on enterprise software.
            </p>
            <div className="flex flex-wrap gap-4">
              <button
                onClick={() => scrollTo('services')}
                className="bg-blue-400 hover:bg-blue-300 text-[#001f4d] font-bold px-6 py-3 rounded transition"
              >
                Explore Services
              </button>
              <button
                onClick={() => scrollTo('how-it-works')}
                className="border border-blue-300 text-blue-200 hover:bg-white/10 font-medium px-6 py-3 rounded transition"
              >
                See How It Works
              </button>
            </div>
          </div>

          {/* Right — login form */}
          <div id="login-form" className="bg-white text-slate-900 rounded-2xl shadow-2xl p-8">
            <h2 className="text-2xl font-bold text-[#003366] mb-1">Welcome Back</h2>
            <p className="text-sm text-slate-500 mb-6">Sign in to your benchmarking portal</p>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003366] focus:border-transparent"
                  placeholder="you@company.com"
                  required
                  disabled={loading}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003366] focus:border-transparent"
                  placeholder="••••••••"
                  required
                  disabled={loading}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#003366] hover:bg-[#004080] text-white font-semibold py-3 rounded-lg transition disabled:opacity-50"
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            <div className="text-center mt-4">
              <Link to="/forgot-password" className="text-sm text-[#003366] font-medium hover:underline">
                Forgot your password?
              </Link>
            </div>

            <p className="text-center text-sm text-slate-500 mt-3">
              New to SaaSCostCompare?{' '}
              <Link to="/register" className="text-[#003366] font-semibold hover:underline">
                Create an account
              </Link>
            </p>

            <div className="mt-6 pt-5 border-t border-slate-100 flex items-center justify-center gap-2 text-xs text-slate-400">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              Enterprise-grade encryption &amp; data security
            </div>
          </div>
        </div>

        {/* Wave divider */}
        <svg viewBox="0 0 1440 60" className="w-full block" preserveAspectRatio="none" style={{ height: 60 }}>
          <path d="M0,30 C360,60 1080,0 1440,30 L1440,60 L0,60 Z" fill="white" />
        </svg>
      </section>


      {/* ── INSIGHTS / WHY US ── */}
      <InsightsCarousel />

      {/* ── ABOUT ── */}
      <section id="about" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-2 gap-16 items-center">
          <div>
            <p className="text-xs font-bold tracking-widest uppercase text-[#003366] mb-3">Who We Are</p>
            <h2 className="text-4xl font-extrabold text-slate-900 leading-tight mb-6">
              Independent Benchmarking<br />You Can Trust
            </h2>
            <p className="text-slate-600 leading-relaxed mb-4">
              SaaSCostCompare is an independent benchmarking and advisory firm helping
              enterprise technology buyers make data-driven decisions about their SaaS
              portfolio. We combine anonymised peer data from organisations of similar
              scale, size and domain to surface insights that vendor-supplied research
              simply cannot provide.
            </p>
            <p className="text-slate-600 leading-relaxed mb-8">
              Founded by former enterprise technology and benchmarking leaders, we understand
              the pressure to optimise spend without sacrificing capability. Our reports give
              your CFO and CIO the evidence they need to negotiate, consolidate, and invest
              with confidence.
            </p>
            <div className="flex flex-col gap-3">
              {[
                'Vendor-neutral, conflict-free analysis',
                'Peer benchmarks from at least 10 enterprise organisations',
                'Covers AWS, Microsoft, Google, Salesforce, SAP, Pega & more',
              ].map((point) => (
                <div key={point} className="flex items-start gap-3">
                  <div className="mt-1 w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg className="w-3 h-3 text-[#003366]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span className="text-slate-700 text-sm">{point}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-5">
            {[
              { num: '500+', label: 'Organisations', sub: 'in our benchmark panel' },
              { num: '$2.4B+', label: 'Spend Analysed', sub: 'across all categories' },
              { num: '32%', label: 'Avg. Savings', sub: 'identified per engagement' },
              { num: '6', label: 'Vendor Categories', sub: 'with deep benchmarks' },
            ].map(({ num, label, sub }) => (
              <div key={label} className="bg-slate-50 border border-slate-200 rounded-xl p-6">
                <p className="text-3xl font-extrabold text-[#003366] mb-1">{num}</p>
                <p className="font-semibold text-slate-800 text-sm">{label}</p>
                <p className="text-xs text-slate-500 mt-1">{sub}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SERVICES ── */}
      <section id="services" className="py-24 bg-slate-50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-xs font-bold tracking-widest uppercase text-[#003366] mb-3">What We Offer</p>
            <h2 className="text-4xl font-extrabold text-slate-900 mb-4">Our Services</h2>
            <p className="text-slate-500 max-w-2xl mx-auto">
              From one-off cost audits to ongoing benchmarking subscriptions, we give enterprise
              technology buyers the intelligence to act.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                ),
                title: 'SaaS Cost Benchmarking',
                desc: 'Receive a detailed benchmark showing how your SaaS costs compare with peers of similar size, industry, and revenue at the SKU level / line item level as well as at aggregated level. This data backed benchmarking is a critical element leveraged by enterprises to negotiate optimum prices with SaaS vendors.',
                tag: 'Most Popular',
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                ),
                title: 'Contract & Renewal Advisory',
                desc: 'Armed with benchmark data, our advisors help you prepare for vendor negotiations — identifying leverage points before your next renewal cycle.',
                tag: 'Advisory',
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                ),
                title: 'Portfolio Optimisation',
                desc: 'A holistic view of your entire SaaS portfolio — identifying overlapping tools, shadow IT spend, and consolidation paths that reduce cost without reducing capability.',
                tag: 'Strategic',
              },
            ].map(({ icon, title, desc, tag }) => (
              <div key={title} className="bg-white rounded-xl border border-slate-200 p-7 hover:shadow-lg transition group">
                <div className="flex items-start justify-between mb-5">
                  <div className="w-12 h-12 bg-[#003366]/10 rounded-lg flex items-center justify-center group-hover:bg-[#003366] transition">
                    <svg className="w-6 h-6 text-[#003366] group-hover:text-white transition" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      {icon}
                    </svg>
                  </div>
                  <span className="text-xs font-semibold text-[#003366] bg-blue-50 px-2 py-0.5 rounded-full">{tag}</span>
                </div>
                <h3 className="text-base font-bold text-slate-900 mb-2">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section id="how-it-works" className="py-24 bg-white">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-xs font-bold tracking-widest uppercase text-[#003366] mb-3">The Process</p>
            <h2 className="text-4xl font-extrabold text-slate-900 mb-4">How It Works</h2>
            <p className="text-slate-500 max-w-xl mx-auto">
              From data upload to actionable benchmark report in minutes — not weeks.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { step: '01', title: 'Secure Data Upload', desc: 'Upload the details of your current SaaS subscription securely onto our platform. You can upload any of the following — your SaaS invoice, or contract documents along with any amendments or simply a tabulated listing of the SKUs that are part of your SaaS subscription along with their volume and SKU level / line item level pricing.' },
              { step: '02', title: 'Intelligent Data Ingestion', desc: 'Our engine parses your data and categorises it into logical groups for precise analysis.' },
              { step: '03', title: 'Benchmarking Feasibility Assessment', desc: 'Before you pay, we verify our data\'s relevance. We scan our database for peer data (based on your SKU mix, volumes, industry, and region) updated within the last 12 months. You\'ll see exactly what percentage of your spend we can benchmark with high confidence.' },
              { step: '04', title: 'Transparent Fee', desc: 'Review the feasibility report and move forward only if you\'re satisfied with the data coverage. Complete your purchase through our secure payment gateway to unlock full insights.' },
              { step: '05', title: 'Peer Benchmarking', desc: 'The engine compares your pricing against anonymised peer data from organisations of similar size and industry. We identify exactly where you are overpaying, and where your pricing is in-line with the market.' },
              { step: '06', title: 'View & Download Your Report', desc: 'View a detailed benchmark report with recommendations, comparable spend ranges, and negotiation guidance. You can also download the report.' },
            ].map(({ step, title, desc }, i) => (
              <div key={step} className="relative">
                {i < 5 && i !== 2 && (
                  <div className="hidden md:block absolute top-6 left-full w-full h-0.5 bg-slate-200 z-0" style={{ width: 'calc(100% - 2rem)', left: '3rem' }} />
                )}
                <div className="relative z-10">
                  <div className="w-12 h-12 bg-[#003366] text-white rounded-full flex items-center justify-center font-bold text-sm mb-5">
                    {step}
                  </div>
                  <h3 className="font-bold text-slate-900 mb-2">{title}</h3>
                  <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CONTACT ── */}
      <ContactSection />

      {/* ── CTA ── */}
      <section className="py-20 bg-white border-t border-slate-100">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-4xl font-extrabold text-[#003366] mb-4">
            Ready to benchmark your SaaS spend?
          </h2>
          <p className="text-slate-500 mb-8 text-lg">
            Join 500+ organisations that trust SaaSCostCompare to cut waste and negotiate smarter.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/register"
              className="bg-[#003366] hover:bg-[#004080] text-white font-bold px-8 py-4 rounded-lg transition text-sm"
            >
              Create Free Account
            </Link>
            <button
              onClick={() => scrollTo('login-form')}
              className="border-2 border-[#003366] text-[#003366] font-bold px-8 py-4 rounded-lg hover:bg-blue-50 transition text-sm"
            >
              Sign In to Portal
            </button>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="bg-slate-900 text-slate-400 py-16">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-10 mb-12">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-7 h-7 bg-blue-500 rounded flex items-center justify-center">
                  <span className="text-white text-xs font-bold">SC</span>
                </div>
                <span className="text-white font-bold">SaaSCostCompare</span>
              </div>
              <p className="text-sm leading-relaxed">
                Independent SaaS benchmarking and cost intelligence for enterprise technology buyers.
              </p>
            </div>
            <div>
              <p className="text-white font-semibold mb-4 text-sm">Services</p>
              <ul className="space-y-2 text-sm">
                {['Cost Benchmarking', 'Peer Comparison', 'Portfolio Review', 'Renewal Advisory'].map((s) => (
                  <li key={s}><button className="hover:text-white transition">{s}</button></li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-white font-semibold mb-4 text-sm">Vendors Covered</p>
              <ul className="space-y-2 text-sm">
                {['AWS', 'Microsoft', 'Google Cloud', 'Salesforce', 'SAP', 'Pega'].map((v) => (
                  <li key={v}><span className="hover:text-white transition cursor-default">{v}</span></li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-white font-semibold mb-4 text-sm">Company</p>
              <ul className="space-y-2 text-sm">
                {['About Us', 'Research', 'Careers', 'Contact', 'Privacy Policy', 'Terms of Service'].map((item) => (
                  <li key={item}><button className="hover:text-white transition">{item}</button></li>
                ))}
              </ul>
            </div>
          </div>
          <div className="border-t border-slate-800 pt-8 flex flex-col sm:flex-row justify-between items-center gap-4 text-xs">
            <p>© {new Date().getFullYear()} SaaSCostCompare. All rights reserved.</p>
            <p>Independent benchmarking. Vendor-neutral. Conflict-free.</p>
          </div>
        </div>
      </footer>

    </div>
  );
}
