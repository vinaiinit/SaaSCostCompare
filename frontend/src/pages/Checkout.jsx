import { useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { loadStripe } from '@stripe/stripe-js';
import { EmbeddedCheckoutProvider, EmbeddedCheckout } from '@stripe/react-stripe-js';
import { subscriptionAPI } from '../api';

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

export default function CheckoutPage() {
  const [searchParams] = useSearchParams();
  const priceId = searchParams.get('price_id');
  const planName = searchParams.get('plan') || 'Plan';

  const fetchClientSecret = useCallback(async () => {
    const res = await subscriptionAPI.createCheckoutSession(priceId);
    return res.data.client_secret;
  }, [priceId]);

  if (!priceId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-gray-500 mb-4">No plan selected.</p>
          <Link to="/pricing" className="text-blue-600 hover:underline">
            View pricing plans
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-blue-900">
            SaaS<span className="text-blue-600">Bench</span>
          </Link>
          <Link to="/pricing" className="text-sm text-gray-500 hover:text-gray-700">
            Back to Pricing
          </Link>
        </div>
      </nav>

      <div className="max-w-3xl mx-auto py-12 px-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Subscribe to {planName.charAt(0).toUpperCase() + planName.slice(1)}
        </h1>
        <p className="text-gray-500 mb-8">
          Complete your payment below. You can cancel anytime.
        </p>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-1">
          <EmbeddedCheckoutProvider stripe={stripePromise} options={{ fetchClientSecret }}>
            <EmbeddedCheckout />
          </EmbeddedCheckoutProvider>
        </div>
      </div>
    </div>
  );
}
