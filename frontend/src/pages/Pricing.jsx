import { Link, useNavigate } from 'react-router-dom';

export default function Pricing() {
  const navigate = useNavigate();
  const isLoggedIn = !!localStorage.getItem('token');

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-blue-900">
            SaaS<span className="text-blue-600">Bench</span>
          </Link>
          <div className="flex items-center gap-4">
            {isLoggedIn ? (
              <button
                onClick={() => navigate('/dashboard')}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
              >
                Dashboard
              </button>
            ) : (
              <>
                <Link to="/login" className="text-sm font-medium text-gray-600 hover:text-gray-900">Sign In</Link>
                <Link to="/register" className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">Get Started</Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <div className="text-center pt-20 pb-12 px-6">
        <h1 className="text-4xl font-extrabold text-gray-900 mb-4">Simple, Transparent Pricing</h1>
        <p className="text-lg text-gray-500 max-w-2xl mx-auto">
          Upload your contracts for free. Pay only when you download a full peer comparison report.
        </p>
      </div>

      <div className="max-w-4xl mx-auto px-6 pb-24">
        <div className="grid md:grid-cols-2 gap-8">
          {/* Free */}
          <div className="rounded-2xl border border-gray-200 bg-white shadow-sm p-8 flex flex-col">
            <h3 className="text-lg font-bold text-gray-900">Free</h3>
            <p className="text-sm text-gray-500 mt-1 mb-6">Explore the platform</p>
            <div className="mb-6">
              <span className="text-4xl font-extrabold text-gray-900">$0</span>
            </div>
            <ul className="space-y-3 mb-8 flex-1">
              {['Upload contracts (CSV, PDF, Word)', 'AI-powered data extraction', 'Data coverage & feasibility check', 'View extracted line items'].map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                  <svg className="w-5 h-5 text-green-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {f}
                </li>
              ))}
            </ul>
            <button
              onClick={() => navigate(isLoggedIn ? '/dashboard' : '/register')}
              className="w-full py-3 rounded-lg text-sm font-semibold bg-gray-900 text-white hover:bg-gray-800 transition"
            >
              {isLoggedIn ? 'Go to Dashboard' : 'Get Started'}
            </button>
          </div>

          {/* Per Report */}
          <div className="relative rounded-2xl border border-blue-600 bg-white shadow-xl ring-2 ring-blue-600 p-8 flex flex-col">
            <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full">
              Pay Per Report
            </span>
            <h3 className="text-lg font-bold text-gray-900">Full Report</h3>
            <p className="text-sm text-gray-500 mt-1 mb-6">Complete peer comparison analysis</p>
            <div className="mb-6">
              <span className="text-4xl font-extrabold text-gray-900">$499</span>
              <span className="text-gray-500 text-sm"> /report</span>
            </div>
            <ul className="space-y-3 mb-8 flex-1">
              {[
                'Everything in Free',
                'Full peer benchmark comparison',
                'Cost optimization insights',
                'Negotiation recommendations',
                'Downloadable PDF report',
              ].map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                  <svg className="w-5 h-5 text-green-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {f}
                </li>
              ))}
            </ul>
            <button
              onClick={() => navigate(isLoggedIn ? '/dashboard' : '/register')}
              className="w-full py-3 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 transition"
            >
              {isLoggedIn ? 'Go to Dashboard' : 'Get Started'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
