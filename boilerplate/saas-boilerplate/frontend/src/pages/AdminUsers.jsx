import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';

function AdminUsers() {
  const { user, isLoading, getAccessTokenSilently } = useAuth0();
  const [users, setUsers] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const roles = user?.['https://teebu.com/roles'] || user?.roles || [];
  const isAdmin = roles.includes('admin');

  useEffect(() => {
    if (!isAdmin) return;

    async function loadUsers() {
      try {
        const token = await getAccessTokenSilently();
        const res = await fetch('/api/admin/users', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setUsers(data.users || data || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadUsers();
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
          <h1 className="text-3xl font-bold text-gray-900">Users</h1>
          <p className="text-gray-500 mt-1">All registered users on the platform</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded p-4 mb-6">
            Failed to load users: {error}
          </div>
        )}

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plan</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.length === 0 && !error && (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-400">
                    No users found
                  </td>
                </tr>
              )}
              {users.map((u) => (
                <tr key={u.user_id || u.email} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">{u.email}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{u.name || '—'}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      u.role === 'admin'
                        ? 'bg-purple-100 text-purple-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {u.role || 'user'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">{u.plan || '—'}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
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

export default AdminUsers;
