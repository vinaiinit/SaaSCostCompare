import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { subscriptionAPI } from '../api';

export default function CheckoutReturn() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    if (!sessionId) {
      setStatus('error');
      return;
    }

    const checkStatus = async () => {
      try {
        const res = await subscriptionAPI.checkoutStatus(sessionId);
        setStatus(res.data.status === 'complete' ? 'success' : 'pending');
      } catch {
        setStatus('error');
      }
    };
    checkStatus();
  }, [sessionId]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-6">
      <div className="max-w-md w-full text-center">
        {status === 'loading' && (
          <div>
            <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-500">Confirming your subscription...</p>
          </div>
        )}

        {status === 'success' && (
          <div>
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Subscription Active!</h1>
            <p className="text-gray-500 mb-8">
              Your plan is now active. You can start generating peer comparison reports.
            </p>
            <Link
              to="/dashboard"
              className="inline-block px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition"
            >
              Go to Dashboard
            </Link>
          </div>
        )}

        {status === 'pending' && (
          <div>
            <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Processing</h1>
            <p className="text-gray-500 mb-8">
              Your payment is being processed. This usually takes a few seconds.
            </p>
            <Link
              to="/dashboard"
              className="inline-block px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition"
            >
              Go to Dashboard
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Something Went Wrong</h1>
            <p className="text-gray-500 mb-8">
              We couldn't confirm your subscription. Please try again or contact support.
            </p>
            <Link
              to="/pricing"
              className="inline-block px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition"
            >
              Back to Pricing
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
