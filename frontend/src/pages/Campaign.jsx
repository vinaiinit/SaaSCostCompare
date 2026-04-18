import { useState } from 'react';
import { Link } from 'react-router-dom';
import { campaignAPI } from '../api';

const VENDORS = [
  'Microsoft (M365/Azure)',
  'Salesforce',
  'SAP',
  'Oracle',
  'Google Cloud',
  'AWS',
];

const INDUSTRIES = [
  'Technology',
  'Financial Services',
  'Healthcare',
  'Manufacturing',
  'Retail',
  'Telecom',
  'Energy',
  'Education',
  'Government',
  'Other',
];

export default function Campaign() {
  const [vendor, setVendor] = useState('');
  const [files, setFiles] = useState(null);
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [industry, setIndustry] = useState('');
  const [companySize, setCompanySize] = useState('');
  const [uploading, setUploading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!vendor) { setError('Please select a vendor.'); return; }
    if (!files || files.length === 0) { setError('Please select a file to upload.'); return; }

    setUploading(true);
    setError('');
    try {
      await campaignAPI.submit(
        Array.from(files),
        vendor,
        email || null,
        company || null,
        industry || null,
        companySize ? parseInt(companySize) : null,
      );
      setSubmitted(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-white font-sans">

      {/* Navbar */}
      <header className="fixed top-0 inset-x-0 z-50 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#003366] rounded flex items-center justify-center">
              <span className="text-white text-xs font-bold">SC</span>
            </div>
            <span className="text-xl font-bold text-[#003366] tracking-tight">SaaSCostCompare</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            <button onClick={() => scrollTo('how-it-works')} className="hover:text-[#003366] transition">How It Works</button>
            <button onClick={() => scrollTo('privacy')} className="hover:text-[#003366] transition">Privacy</button>
            <button onClick={() => scrollTo('upload')} className="hover:text-[#003366] transition">Contribute</button>
          </nav>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-[#003366] hover:underline">Sign In</Link>
            <Link to="/register" className="text-sm font-medium bg-[#003366] text-white px-4 py-2 rounded hover:bg-[#004080] transition">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-24 bg-gradient-to-br from-[#001f4d] via-[#003366] to-[#004a99] text-white">
        <div className="max-w-7xl mx-auto px-6 py-20">
          <div className="max-w-3xl mx-auto text-center">
            <p className="text-xs font-bold tracking-widest uppercase text-blue-300 mb-4">
              Data Collection Campaign
            </p>
            <h1 className="text-5xl font-extrabold leading-tight mb-6">
              Are You Overpaying<br />
              <span className="text-blue-300">for Enterprise SaaS?</span>
            </h1>
            <p className="text-lg text-blue-100 leading-relaxed mb-8">
              Share your contract data anonymously and get a free benchmark report
              showing exactly how your SaaS costs compare with peers in your industry.
              The more companies participate, the better the benchmarks for everyone.
            </p>
            <div className="flex flex-wrap gap-4 justify-center">
              <button
                onClick={() => scrollTo('upload')}
                className="bg-blue-400 hover:bg-blue-300 text-[#001f4d] font-bold px-8 py-4 rounded-lg transition text-sm"
              >
                Contribute Your Data
              </button>
              <button
                onClick={() => scrollTo('how-it-works')}
                className="border border-blue-300 text-blue-200 hover:bg-white/10 font-medium px-8 py-4 rounded-lg transition text-sm"
              >
                Learn More
              </button>
            </div>
          </div>
        </div>
        <svg viewBox="0 0 1440 60" className="w-full block" preserveAspectRatio="none" style={{ height: 60 }}>
          <path d="M0,30 C360,60 1080,0 1440,30 L1440,60 L0,60 Z" fill="white" />
        </svg>
      </section>

      {/* Value Proposition */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-extrabold text-slate-900 mb-4">Why Participate?</h2>
            <p className="text-slate-500 max-w-2xl mx-auto">
              Think of it as Glassdoor for SaaS contracts. Anonymous. Free. Mutually beneficial.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />,
                title: 'Free Benchmark Report',
                desc: 'See how your costs compare against peers. Know your percentile ranking for each vendor — are you paying above or below market?',
              },
              {
                icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />,
                title: 'Fully Anonymous',
                desc: 'Your company name is never exposed. We only use aggregate statistics — percentiles, medians, and ranges. No individual data is ever shared.',
              },
              {
                icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />,
                title: 'Network Effect',
                desc: 'Every upload improves the benchmarks. Early participants get lifetime access to continuously improving data as more companies join.',
              },
            ].map(({ icon, title, desc }) => (
              <div key={title} className="bg-slate-50 rounded-xl border border-slate-200 p-7 hover:shadow-lg transition group">
                <div className="w-12 h-12 bg-[#003366]/10 rounded-lg flex items-center justify-center mb-5 group-hover:bg-[#003366] transition">
                  <svg className="w-6 h-6 text-[#003366] group-hover:text-white transition" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    {icon}
                  </svg>
                </div>
                <h3 className="text-base font-bold text-slate-900 mb-2">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-20 bg-slate-50">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-14">
            <p className="text-xs font-bold tracking-widest uppercase text-[#003366] mb-3">Simple Process</p>
            <h2 className="text-3xl font-extrabold text-slate-900 mb-4">How It Works</h2>
          </div>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              { step: '01', title: 'Select Vendor', desc: 'Choose which vendor contract you want to benchmark.' },
              { step: '02', title: 'Upload Data', desc: 'Upload your contract CSV, invoice PDF, or pricing schedule. Takes 2 minutes.' },
              { step: '03', title: 'We Extract & Anonymize', desc: 'Our engine parses line items and normalizes pricing. Your company name is never stored with the data.' },
              { step: '04', title: 'Get Your Report', desc: 'Once we have enough peer data, you receive your free benchmark report with percentile rankings.' },
            ].map(({ step, title, desc }) => (
              <div key={step} className="text-center">
                <div className="w-12 h-12 bg-[#003366] text-white rounded-full flex items-center justify-center font-bold text-sm mb-4 mx-auto">
                  {step}
                </div>
                <h3 className="font-bold text-slate-900 mb-2 text-sm">{title}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Vendors covered */}
      <section className="py-16 bg-white">
        <div className="max-w-5xl mx-auto px-6 text-center">
          <p className="text-xs font-bold tracking-widest uppercase text-[#003366] mb-3">Currently Benchmarking</p>
          <h2 className="text-3xl font-extrabold text-slate-900 mb-8">Vendors We Cover</h2>
          <div className="flex flex-wrap justify-center gap-4">
            {VENDORS.map((v) => (
              <div key={v} className="bg-slate-50 border border-slate-200 rounded-lg px-6 py-4 text-sm font-semibold text-slate-700">
                {v}
              </div>
            ))}
          </div>
          <p className="text-sm text-slate-500 mt-6">
            More vendors coming soon based on participant demand.
          </p>
        </div>
      </section>

      {/* Upload Form */}
      <section id="upload" className="py-20 bg-gradient-to-br from-[#001f4d] via-[#003366] to-[#004a99] text-white">
        <div className="max-w-2xl mx-auto px-6">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-extrabold mb-4">Contribute Your Data</h2>
            <p className="text-blue-200">
              Upload your SaaS contract data below. Your company information is optional
              and only used for better peer matching — never shared externally.
            </p>
          </div>

          {submitted ? (
            <div className="bg-white rounded-2xl shadow-2xl p-10 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold text-[#003366] mb-2">Thank You!</h3>
              <p className="text-slate-600 mb-4">
                Your contract data has been submitted. We'll process it and add it to our benchmark database.
              </p>
              <p className="text-sm text-slate-500 mb-6">
                {email
                  ? `We'll notify you at ${email} when your benchmark report is ready.`
                  : 'Create a free account to track your benchmark status and receive your report.'}
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={() => { setSubmitted(false); setFiles(null); setVendor(''); }}
                  className="border-2 border-[#003366] text-[#003366] font-semibold px-6 py-3 rounded-lg hover:bg-blue-50 transition text-sm"
                >
                  Upload Another Vendor
                </button>
                <Link
                  to="/register"
                  className="bg-[#003366] text-white font-semibold px-6 py-3 rounded-lg hover:bg-[#004080] transition text-sm text-center"
                >
                  Create Free Account
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-2xl p-8 text-slate-900">
              <h3 className="text-xl font-bold text-[#003366] mb-6">Upload Contract Data</h3>

              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
              )}

              {/* Vendor selection */}
              <div className="mb-5">
                <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">
                  Select Vendor *
                </label>
                <div className="flex flex-wrap gap-2">
                  {VENDORS.map((v) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setVendor(v)}
                      className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                        vendor === v
                          ? 'bg-[#003366] text-white border-[#003366]'
                          : 'bg-white text-slate-700 border-slate-300 hover:border-[#003366]'
                      }`}
                    >
                      {v}
                    </button>
                  ))}
                </div>
              </div>

              {/* File upload */}
              <div className="mb-5">
                <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">
                  Upload File *
                </label>
                <div className={`border-2 border-dashed rounded-lg p-6 transition text-center ${
                  files ? 'border-green-300 bg-green-50' : 'border-slate-300 hover:border-[#003366]'
                }`}>
                  <label className="cursor-pointer block">
                    {files ? (
                      <div>
                        <svg className="mx-auto h-8 w-8 text-green-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <p className="text-sm font-medium text-green-800">
                          {Array.from(files).map(f => f.name).join(', ')}
                        </p>
                        <p className="text-xs text-green-600 mt-1">Click to change</p>
                      </div>
                    ) : (
                      <div>
                        <svg className="mx-auto h-8 w-8 text-slate-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        <p className="text-sm text-slate-600">Click to select CSV, PDF, or ZIP</p>
                        <p className="text-xs text-slate-400 mt-1">Max 50MB</p>
                      </div>
                    )}
                    <input
                      type="file"
                      accept=".csv,.pdf,.zip"
                      multiple
                      onChange={(e) => setFiles(e.target.files)}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>

              {/* Optional info */}
              <div className="mb-5 p-4 bg-slate-50 border border-slate-200 rounded-lg">
                <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-3">
                  Optional — helps us match you with better peers
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Email</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@company.com"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003366] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Company Name</label>
                    <input
                      type="text"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      placeholder="Acme Corp"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003366] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Industry</label>
                    <select
                      value={industry}
                      onChange={(e) => setIndustry(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003366] focus:border-transparent bg-white"
                    >
                      <option value="">Select...</option>
                      {INDUSTRIES.map((ind) => (
                        <option key={ind} value={ind}>{ind}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Company Size (employees)</label>
                    <input
                      type="number"
                      value={companySize}
                      onChange={(e) => setCompanySize(e.target.value)}
                      placeholder="e.g. 500"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003366] focus:border-transparent"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={uploading || !vendor || !files}
                className="w-full bg-[#003366] hover:bg-[#004080] text-white font-semibold py-3 rounded-lg transition disabled:opacity-50 text-sm"
              >
                {uploading ? 'Uploading...' : 'Submit Contract Data'}
              </button>

              <p className="text-xs text-slate-400 text-center mt-3">
                By submitting, you agree that your anonymized cost data may be used in aggregate benchmarks.
              </p>
            </form>
          )}
        </div>
      </section>

      {/* Privacy & Trust */}
      <section id="privacy" className="py-20 bg-white">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-14">
            <p className="text-xs font-bold tracking-widest uppercase text-[#003366] mb-3">Your Data is Safe</p>
            <h2 className="text-3xl font-extrabold text-slate-900 mb-4">Privacy & Security</h2>
          </div>
          <div className="grid md:grid-cols-2 gap-8">
            {[
              {
                title: 'Anonymized by Default',
                desc: 'Company names are never tied to cost data in our database. Benchmarks use aggregated percentiles only — no one can trace a data point back to your organization.',
              },
              {
                title: 'Encrypted at Rest & in Transit',
                desc: 'All uploads are stored in AWS S3 with server-side encryption. Data in transit is protected with TLS. Your files are isolated in organization-specific folders.',
              },
              {
                title: 'Minimum Aggregation Threshold',
                desc: 'We never publish benchmarks with fewer than 5 contributing organizations. This ensures no individual company\'s data can be reverse-engineered from the results.',
              },
              {
                title: 'You Control Your Data',
                desc: 'Request deletion of your data at any time by contacting us. We\'ll remove your contract records from our database within 48 hours.',
              },
            ].map(({ title, desc }) => (
              <div key={title} className="flex items-start gap-4">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-green-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 mb-1">{title}</h3>
                  <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-slate-50 border-t border-slate-200">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-extrabold text-[#003366] mb-4">
            Ready to find out if you're overpaying?
          </h2>
          <p className="text-slate-500 mb-8">
            It takes 2 minutes to upload your contract data. Get your free benchmark report when enough peers participate.
          </p>
          <button
            onClick={() => scrollTo('upload')}
            className="bg-[#003366] hover:bg-[#004080] text-white font-bold px-8 py-4 rounded-lg transition text-sm"
          >
            Upload Your Contract Data
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-blue-500 rounded flex items-center justify-center">
                <span className="text-white text-xs font-bold">SC</span>
              </div>
              <span className="text-white font-bold text-sm">SaaSCostCompare</span>
            </div>
            <p>&copy; {new Date().getFullYear()} SaaSCostCompare. All rights reserved.</p>
            <p>Independent benchmarking. Vendor-neutral. Conflict-free.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
