import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { subscriptionAPI } from '../api';

const PLAN_DETAILS = [
  {
    id: 'free',
    name: 'Free',
    price: 0,
    period: '',
    description: 'Explore the platform',
    features: ['Upload contracts', 'AI extraction', 'Data coverage view'],
    cta: 'Get Started',
    highlight: false,
  },
  {
    id: 'starter',
    name: 'Starter',
    price: 499,
    period: '/month',
    description: 'For teams starting to benchmark',
    features: [
      'Everything in Free',
      '3 peer comparison reports/month',
      'Benchmark narratives',
      'PDF report download',
    ],
    cta: 'Subscribe',
    highlight: true,
  },
  {
    id: 'professional',
    name: 'Professional',
    price: 999,
    period: '/month',
    description: 'For serious cost optimization',
    features: [
      'Everything in Starter',
      '10 reports/month',
      'License analysis connectors',
      'Priority support',
    ],
    cta: 'Subscribe',
    highlight: false,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: -1,
    period: '',
    description: 'For large organizations',
    features: [
      'Everything in Professional',
      'Unlimited reports',
      'Dedicated account manager',
      'Custom integrations',
    ],
    cta: 'Contact Us',
    highlight: false,
  },
];

export default function Pricing() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [currentPlan, setCurrentPlan] = useState('free');
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('token');
    setIsLoggedIn(!!token);

    const fetchData = async () => {
      try {
        const [plansRes] = await Promise.all([
          subscriptionAPI.getPlans(),
        ]);
        setPlans(plansRes.data);

        if (token) {
          const statusRes = await subscriptionAPI.getStatus();
          setCurrentPlan(statusRes.data.plan);
        }
      } catch (err) {
        console.error('Failed to load plans:', err);
      }
    };
    fetchData();
  }, []);

  const handleSelectPlan = (planId) => {
    if (planId === 'enterprise') {
      navigate('/#contact');
      return;
    }
    if (planId === 'free') {
      if (isLoggedIn) {
        navigate('/dashboard');
      } else {
        navigate('/register');
      }
      return;
    }
    if (!isLoggedIn) {
      navigate('/register');
      return;
    }

    const plan = plans.find((p) => p.id === planId);
    if (plan && plan.stripe_price_id) {
      navigate(`/checkout?price_id=${plan.stripe_price_id}&plan=${planId}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Nav */}
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
                <Link to="/login" className="text-sm font-medium text-gray-600 hover:text-gray-900">
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Header */}
      <div className="text-center pt-20 pb-12 px-6">
        <h1 className="text-4xl font-extrabold text-gray-900 mb-4">
          Simple, Transparent Pricing
        </h1>
        <p className="text-lg text-gray-500 max-w-2xl mx-auto">
          Start free, upgrade when you need peer comparison reports. No hidden fees.
        </p>
      </div>

      {/* Plan cards */}
      <div className="max-w-7xl mx-auto px-6 pb-24">
        <div className="grid md:grid-cols-4 gap-6">
          {PLAN_DETAILS.map((plan) => {
            const isCurrent = currentPlan === plan.id;
            return (
              <div
                key={plan.id}
                className={`relative rounded-2xl border p-8 flex flex-col ${
                  plan.highlight
                    ? 'border-blue-600 bg-white shadow-xl ring-2 ring-blue-600'
                    : 'border-gray-200 bg-white shadow-sm'
                }`}
              >
                {plan.highlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                    Most Popular
                  </span>
                )}

                <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
                <p className="text-sm text-gray-500 mt-1 mb-6">{plan.description}</p>

                <div className="mb-6">
                  {plan.price === -1 ? (
                    <span className="text-3xl font-extrabold text-gray-900">Custom</span>
                  ) : (
                    <>
                      <span className="text-4xl font-extrabold text-gray-900">
                        ${plan.price}
                      </span>
                      <span className="text-gray-500 text-sm">{plan.period}</span>
                    </>
                  )}
                </div>

                <ul className="space-y-3 mb-8 flex-1">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm text-gray-600">
                      <svg className="w-5 h-5 text-green-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      {feature}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleSelectPlan(plan.id)}
                  disabled={isCurrent}
                  className={`w-full py-3 rounded-lg text-sm font-semibold transition ${
                    isCurrent
                      ? 'bg-gray-100 text-gray-400 cursor-default'
                      : plan.highlight
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-900 text-white hover:bg-gray-800'
                  }`}
                >
                  {isCurrent ? 'Current Plan' : plan.cta}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
