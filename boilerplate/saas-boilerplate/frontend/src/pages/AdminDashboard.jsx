import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import useConfig from '../hooks/useConfig';

function AdminDashboard() {
  const { user, isLoading, getAccessTokenSilently } = useAuth0();
  const config = useConfig();
  const { branding } = config;

  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState(null);

  // Auth0 roles are stored in the user's custom namespace claim
  const roles = user?.['https://teebu.com/roles'] || user?.roles || [];
  const isAdmin = roles.includes('admin');

  useEffect(() => {
    if (!isAdmin) return;

    async function loadStats() {
      try {
        const token = await getAccessTokenSilently();
        const month = new Date().toISOString().slice(0, 7); // YYYY-MM

        const [tenantRes, plRes] = await Promise.all([
          fetch('/api/admin/tenants', {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`/api/admin/pl?month=${month}`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        const tenants = tenantRes.ok ? await tenantRes.json() : {};
        const pl = plRes.ok ? await plRes.json() : {};

        setStats({
          tenantCount: tenants.total ?? tenants.length ?? 0,
          mrr: pl.total_revenue_usd ?? 0,
          aiSpend: pl.total_ai_costs_usd ?? 0,
        });
      } catch (err) {
        setStatsError('Could not load stats');
      }
    }

    loadStats();
  }, [isAdmin, getAccessTokenSilently]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  const navCards = [
    { label: 'Users', description: 'Manage user accounts and roles', path: '/admin/users', icon: '👤' },
    { label: 'Tenants', description: 'View tenant usage and plans', path: '/admin/tenants', icon: '🏢' },
    { label: 'Billing', description: 'Subscriptions and Stripe events', path: '/admin/billing', icon: '💳' },
    { label: 'Expenses', description: 'P&L and cost tracking', path: '/admin/expenses', icon: '📊' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
          <p className="text-gray-600 mt-1">Platform-wide overview</p>
        </div>

        {/* Quick stats strip */}
        <div className="grid md:grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-5">
            <p className="text-sm text-gray-500 uppercase tracking-wide">Total Tenants</p>
            <p className="text-3xl font-bold mt-1" style={{ color: branding.primary_color }}>
              {statsError ? '—' : stats ? stats.tenantCount : '…'}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-5">
            <p className="text-sm text-gray-500 uppercase tracking-wide">MRR (This Month)</p>
            <p className="text-3xl font-bold mt-1" style={{ color: branding.primary_color }}>
              {statsError ? '—' : stats ? `$${stats.mrr.toFixed(2)}` : '…'}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-5">
            <p className="text-sm text-gray-500 uppercase tracking-wide">AI Spend (This Month)</p>
            <p className="text-3xl font-bold mt-1" style={{ color: branding.primary_color }}>
              {statsError ? '—' : stats ? `$${stats.aiSpend.toFixed(4)}` : '…'}
            </p>
          </div>
        </div>

        {statsError && (
          <p className="text-sm text-yellow-700 bg-yellow-50 border border-yellow-200 rounded p-3 mb-6">
            {statsError} — backend may be unavailable.
          </p>
        )}

        {/* Navigation cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {navCards.map((card) => (
            <Link
              key={card.path}
              to={card.path}
              className="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow block"
            >
              <div className="text-3xl mb-3">{card.icon}</div>
              <h3 className="text-lg font-semibold text-gray-900">{card.label}</h3>
              <p className="text-sm text-gray-500 mt-1">{card.description}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

export default AdminDashboard;
