import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authAPI, orgAPI } from '../api';

export default function Register() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: org, 2: user
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Org form
  const [orgName, setOrgName] = useState('');
  const [domain, setDomain] = useState('');
  const [revenue, setRevenue] = useState('');
  const [size, setSize] = useState('');
  const [orgId, setOrgId] = useState(null);

  // User form
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');

  const handleOrgSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Validate inputs
    if (!orgName.trim() || !domain.trim() || !revenue || !size) {
      setError('Please fill in all fields');
      setLoading(false);
      return;
    }

    try {
      console.log('Creating org:', { orgName, domain, revenue: parseFloat(revenue), size: parseInt(size) });
      const response = await orgAPI.create(orgName, domain, parseFloat(revenue), parseInt(size));
      console.log('Org created:', response.data);
      setOrgId(response.data.id);
      setStep(2);
    } catch (err) {
      console.error('Org creation error:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to create organization.');
    } finally {
      setLoading(false);
    }
  };

  const handleUserSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      console.log('Registering user:', { email, fullName, orgId });
      const registerResp = await authAPI.register(email, password, fullName, orgId);
      console.log('Registration response:', registerResp);
      
      // Auto-login
      const loginResponse = await authAPI.login(email, password);
      console.log('Login response:', loginResponse);
      localStorage.setItem('token', loginResponse.data.access_token);
      navigate('/dashboard');
    } catch (err) {
      console.error('Registration/login error:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Registration failed.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-primary-600 mb-2">SaaSCostCompare</h1>
          <p className="text-slate-600">Optimize your SaaS spending with AI-powered insights</p>
        </div>

        {/* Card */}
        <div className="card p-8">
          <h2 className="text-2xl font-bold mb-2 text-slate-900">
            {step === 1 ? 'Create Organization' : 'Create Account'}
          </h2>
          <p className="text-slate-600 text-sm mb-6">
            Step {step} of 2
          </p>

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}


          {step === 1 ? (
            <form onSubmit={handleOrgSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Organization Name</label>
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className="input-field"
                  placeholder="Acme Corp"
                  required
                  disabled={loading}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Industry</label>
                <select
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  className="input-field"
                  required
                  disabled={loading}
                >
                  <option value="">Select industry</option>
                  {['Technology', 'Financial Services', 'Healthcare', 'Manufacturing', 'Retail & E-Commerce', 'Media & Entertainment', 'Education', 'Government & Public Sector', 'Energy & Utilities', 'Telecommunications', 'Professional Services', 'Real Estate', 'Transportation & Logistics', 'Non-Profit', 'Other'].map((ind) => (
                    <option key={ind} value={ind}>{ind}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Annual Revenue (USD)</label>
                <select
                  value={revenue}
                  onChange={(e) => setRevenue(e.target.value)}
                  className="input-field"
                  required
                  disabled={loading}
                >
                  <option value="">Select revenue range</option>
                  {[
                    { label: 'Under $1M', value: 500000 },
                    { label: '$1M – $5M', value: 3000000 },
                    { label: '$5M – $10M', value: 7500000 },
                    { label: '$10M – $25M', value: 17500000 },
                    { label: '$25M – $50M', value: 37500000 },
                    { label: '$50M – $100M', value: 75000000 },
                    { label: '$100M – $250M', value: 175000000 },
                    { label: '$250M – $500M', value: 375000000 },
                    { label: '$500M – $1B', value: 750000000 },
                    { label: 'Over $1B', value: 1500000000 },
                  ].map(({ label, value }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Number of Employees</label>
                <select
                  value={size}
                  onChange={(e) => setSize(e.target.value)}
                  className="input-field"
                  required
                  disabled={loading}
                >
                  <option value="">Select company size</option>
                  {[
                    { label: '1 – 10', value: 5 },
                    { label: '11 – 50', value: 30 },
                    { label: '51 – 200', value: 125 },
                    { label: '201 – 500', value: 350 },
                    { label: '501 – 1,000', value: 750 },
                    { label: '1,001 – 5,000', value: 3000 },
                    { label: '5,001 – 10,000', value: 7500 },
                    { label: '10,001 – 50,000', value: 30000 },
                    { label: 'Over 50,000', value: 75000 },
                  ].map(({ label, value }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>

              {loading && (
                <div className="flex items-center justify-center gap-2 py-2">
                  <div className="animate-spin w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full"></div>
                  <span className="text-sm text-slate-600">Creating organization...</span>
                </div>
              )}

              <button
                type="submit"
                className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={loading}
              >
                {loading ? 'Creating...' : 'Next'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleUserSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="input-field"
                  placeholder="John Doe"
                  required
                  disabled={loading}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field"
                  placeholder="john@company.com"
                  required
                  disabled={loading}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field"
                  placeholder="••••••••"
                  required
                  disabled={loading}
                />
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="flex-1 btn-secondary disabled:opacity-50"
                  disabled={loading}
                >
                  Back
                </button>
                <button
                  type="submit"
                  className="flex-1 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={loading}
                >
                  {loading ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          )}

          <div className="mt-6">
            <p className="text-center text-slate-600">
              Already have an account?{' '}
              <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
                Sign in here
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
