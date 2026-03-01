import { useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import useConfig from '../hooks/useConfig';
import api from '../utils/api';

function AccountSettings() {
  const { user } = useAuth0();
  const config = useConfig();
  const { branding } = config;
  const [saving, setSaving] = useState(false);

  const handleCancelSubscription = async () => {
    if (!window.confirm('Are you sure you want to cancel your subscription?')) return;
    
    try {
      setSaving(true);
      await api.post('/cancel-subscription', { 
        subscription_id: 'sub_xxx',
        user_id: user?.sub 
      });
      alert('Subscription cancelled. You can continue using until the end of your billing period.');
    } catch (error) {
      alert('Failed to cancel subscription');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Account Settings</h1>

        {/* Profile */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Profile</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input 
                type="text" 
                defaultValue={user?.name}
                className="w-full px-4 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input 
                type="email" 
                value={user?.email}
                disabled
                className="w-full px-4 py-2 border rounded-lg bg-gray-100"
              />
            </div>
          </div>
        </div>

        {/* Subscription */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Subscription</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <p className="font-medium">Current Plan: Pro</p>
                <p className="text-sm text-gray-600">Next billing: Feb 15, 2026</p>
              </div>
              <button 
                className="px-4 py-2 rounded-lg border-2"
                style={{ borderColor: branding.primary_color }}
              >
                Change Plan
              </button>
            </div>
            <button 
              onClick={handleCancelSubscription}
              disabled={saving}
              className="text-red-600 hover:text-red-700"
            >
              {saving ? 'Cancelling...' : 'Cancel Subscription'}
            </button>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-white rounded-lg shadow p-6 border-2 border-red-200">
          <h2 className="text-xl font-semibold mb-4 text-red-600">Danger Zone</h2>
          <button 
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            onClick={() => alert('Account deletion would happen here')}
          >
            Delete Account
          </button>
        </div>
      </div>
    </div>
  );
}

export default AccountSettings;
