import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';

function AdminTenants() {
  const { user, isLoading, getAccessTokenSilently } = useAuth0();
  const [tenants, setTenants] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const roles = user?.['https://teebu.com/roles'] || user?.roles || [];
  const isAdmin = roles.includes('admin');

  useEffect(() => {
    if (!isAdmin) return;

    async function loadTenants() {
      try {
        const token = await getAccessTokenSilently();
        const res = await fetch('/api/admin/tenants', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setTenants(data.tenants || data || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadTenants();
  }, [isAdmin, getAccessTokenSilently]);

  if (isLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAdmin) return <Navigate to="/dashboard" replace />;

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Tenants</h1>
          <p className="text-gray-500 mt-1">Usage and plan overview per tenant</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded p-4 mb-6">
            Failed to load tenants: {error}
          </div>
        )}

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tenant ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plan</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">API Calls (Month)</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">AI Spend (Month)</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {tenants.length === 0 && !error && (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-400">
                    No tenants found
                  </td>
                </tr>
              )}
              {tenants.map((t) => (
                <tr key={t.tenant_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-mono text-gray-900">{t.tenant_id}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      t.plan === 'enterprise'
                        ? 'bg-yellow-100 text-yellow-800'
                        : t.plan === 'pro'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-700'
                    }`}>
                      {t.plan || 'basic'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    {t.api_calls_this_month?.toLocaleString() ?? '—'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    {t.ai_spend_this_month != null ? `$${t.ai_spend_this_month.toFixed(4)}` : '—'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}
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

export default AdminTenants;
