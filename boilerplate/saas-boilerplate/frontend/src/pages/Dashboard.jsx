import { useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import useConfig from '../hooks/useConfig';
import useAnalytics from '../hooks/useAnalytics';

function Dashboard() {
  const { user } = useAuth0();
  const config = useConfig();
  const analytics = useAnalytics();
  const { branding } = config;

  useEffect(() => {
    analytics.trackPageView('/dashboard', 'Dashboard');
  }, [analytics]);

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Welcome back, {user?.name || 'User'}!</h1>
          <p className="text-gray-600 mt-2">Here's your dashboard overview.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-2">Current Plan</h3>
            <p className="text-3xl font-bold" style={{ color: branding.primary_color }}>
              Pro
            </p>
            <p className="text-sm text-gray-600 mt-2">Active subscription</p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-2">Usage This Month</h3>
            <p className="text-3xl font-bold" style={{ color: branding.primary_color }}>
              1,234
            </p>
            <p className="text-sm text-gray-600 mt-2">of unlimited</p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-2">Member Since</h3>
            <p className="text-3xl font-bold" style={{ color: branding.primary_color }}>
              Jan 2026
            </p>
            <p className="text-sm text-gray-600 mt-2">Active for 1 month</p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="grid md:grid-cols-2 gap-4">
            <button 
              className="p-4 border-2 rounded-lg text-left hover:border-blue-600 transition-colors"
              style={{ borderColor: branding.primary_color + '40' }}
            >
              <h3 className="font-semibold mb-1">Get Started</h3>
              <p className="text-sm text-gray-600">Complete your onboarding</p>
            </button>
            <button 
              className="p-4 border-2 rounded-lg text-left hover:border-blue-600 transition-colors"
              style={{ borderColor: branding.primary_color + '40' }}
            >
              <h3 className="font-semibold mb-1">View Analytics</h3>
              <p className="text-sm text-gray-600">See your usage stats</p>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
