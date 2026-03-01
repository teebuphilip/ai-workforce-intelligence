import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import useConfig from '../hooks/useConfig';

function AdminBilling() {
  const { user, isLoading, getAccessTokenSilently } = useAuth0();
  const config = useConfig();
  const { branding } = config;

  const [subscriptions, setSubscriptions] = useState([]);
  const [mrr, setMrr] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const roles = user?.['https://teebu.com/roles'] || user?.roles || [];
  const isAdmin = roles.includes('admin');

  useEffect(() => {
    if (!isAdmin) return;

    async function loadBilling() {
      try {
        const token = await getAccessTokenSilently();
        const res = await fetch('/api/admin/billing/subscriptions', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setSubscriptions(data.subscriptions || data || []);
        setMrr(data.mrr_usd ?? null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadBilling();
  }, [isAdmin, getAccessTokenSilently]);

  if (isLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAdmin) return <Navigate to="/dashboard" replace />;

  const statusColors = {
    active: 'bg-green-100 text-green-800',
    trialing: 'bg-blue-100 text-blue-800',
    past_due: 'bg-red-100 text-red-800',
    canceled: 'bg-gray-100 text-gray-600',
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Billing</h1>
          <p className="text-gray-500 mt-1">Stripe subscriptions and revenue overview</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded p-4 mb-6">
            Failed to load billing data: {error}
          </div>
        )}

        {mrr !== null && (
          <div className="bg-white rounded-lg shadow p-5 mb-6 inline-block">
            <p className="text-sm text-gray-500 uppercase tracking-wide">Monthly Recurring Revenue</p>
            <p className="text-3xl font-bold mt-1" style={{ color: branding.primary_color }}>
              ${mrr.toFixed(2)}
            </p>
          </div>
        )}

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Customer</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plan</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Next Billing</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {subscriptions.length === 0 && !error && (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-400">
                    No subscriptions found
                  </td>
                </tr>
              )}
              {subscriptions.map((sub) => (
                <tr key={sub.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">{sub.customer_email || sub.customer || '—'}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{sub.plan || '—'}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    {sub.amount_usd != null ? `$${sub.amount_usd.toFixed(2)}` : '—'}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      statusColors[sub.status] || 'bg-gray-100 text-gray-700'
                    }`}>
                      {sub.status || '—'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {sub.current_period_end
                      ? new Date(sub.current_period_end * 1000).toLocaleDateString()
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default AdminBilling;
