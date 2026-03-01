import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import useConfig from '../hooks/useConfig';

function AdminExpenses() {
  const { user, isLoading, getAccessTokenSilently } = useAuth0();
  const config = useConfig();
  const { branding } = config;

  const currentMonth = new Date().toISOString().slice(0, 7);
  const [month, setMonth] = useState(currentMonth);
  const [expenses, setExpenses] = useState(null);
  const [pl, setPl] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const roles = user?.['https://teebu.com/roles'] || user?.roles || [];
  const isAdmin = roles.includes('admin');

  useEffect(() => {
    if (!isAdmin) return;

    async function loadExpenses() {
      setLoading(true);
      setError(null);
      try {
        const token = await getAccessTokenSilently();
        const [expRes, plRes] = await Promise.all([
          fetch(`/api/admin/expenses?month=${month}`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`/api/admin/pl?month=${month}`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        if (expRes.ok) setExpenses(await expRes.json());
        if (plRes.ok) setPl(await plRes.json());
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadExpenses();
  }, [isAdmin, month, getAccessTokenSilently]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAdmin) return <Navigate to="/dashboard" replace />;

  const categoryColors = {
    ai_api: 'bg-purple-100 text-purple-800',
    infra: 'bg-blue-100 text-blue-800',
    stripe_fee: 'bg-green-100 text-green-800',
    email: 'bg-yellow-100 text-yellow-800',
    domain: 'bg-orange-100 text-orange-800',
    misc: 'bg-gray-100 text-gray-700',
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Expenses & P&amp;L</h1>
            <p className="text-gray-500 mt-1">Operational costs and profit summary</p>
          </div>
          <div>
            <label className="text-sm text-gray-600 mr-2">Month:</label>
            <input
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="border rounded px-3 py-1 text-sm"
            />
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded p-4 mb-6">
            Failed to load data: {error}
          </div>
        )}

        {/* P&L summary strip */}
        {pl && (
          <div className="grid md:grid-cols-4 gap-4 mb-8">
            {[
              { label: 'Revenue', value: `$${(pl.total_revenue_usd ?? 0).toFixed(2)}`, color: 'text-green-600' },
              { label: 'Total Expenses', value: `$${(pl.total_expenses_usd ?? 0).toFixed(4)}`, color: 'text-red-600' },
              { label: 'Net Profit', value: `$${(pl.net_profit_usd ?? 0).toFixed(2)}`, color: (pl.net_profit_usd ?? 0) >= 0 ? 'text-green-600' : 'text-red-600' },
              { label: 'Margin', value: `${(pl.margin_pct ?? 0).toFixed(1)}%`, color: 'text-gray-900' },
            ].map((stat) => (
              <div key={stat.label} className="bg-white rounded-lg shadow p-5">
                <p className="text-xs text-gray-500 uppercase tracking-wide">{stat.label}</p>
                <p className={`text-2xl font-bold mt-1 ${stat.color}`}>{loading ? '…' : stat.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Expenses by category */}
        {expenses?.by_category && Object.keys(expenses.by_category).length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Costs by Category</h2>
            <div className="space-y-3">
              {Object.entries(expenses.by_category)
                .sort(([, a], [, b]) => b - a)
                .map(([category, amount]) => (
                  <div key={category} className="flex items-center justify-between">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${categoryColors[category] || 'bg-gray-100 text-gray-700'}`}>
                      {category}
                    </span>
                    <span className="text-sm font-mono text-gray-700">${amount.toFixed(4)}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* By tenant breakdown */}
        {expenses?.by_tenant && Object.keys(expenses.by_tenant).length > 0 && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-semibold text-gray-900">Costs by Tenant</h2>
            </div>
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tenant</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Cost (USD)</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {Object.entries(expenses.by_tenant)
                  .sort(([, a], [, b]) => b - a)
                  .map(([tenantId, amount]) => (
                    <tr key={tenantId} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm font-mono text-gray-900">{tenantId}</td>
                      <td className="px-6 py-4 text-sm text-gray-700">${amount.toFixed(4)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && !error && expenses?.row_count === 0 && (
          <div className="bg-white rounded-lg shadow p-8 text-center text-gray-400">
            No expenses logged for {month}
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminExpenses;
