import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { PlusIcon, ChartBarIcon, DocumentTextIcon } from '@heroicons/react/24/outline';

const ClientDashboard = ({ user, supabase }) => {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadClients();
  }, []);

  const loadClients = async () => {
    try {
      const { data, error } = await supabase
        .from('clients')
        .select(`
          *,
          assessments (
            id,
            status,
            created_at
          )
        `)
        .eq('user_id', user.id)
        .order('name');

      if (error) throw error;

      const clientsWithStats = data.map(client => ({
        ...client,
        stats: {
          total_assessments: client.assessments?.length || 0,
          completed_assessments: client.assessments?.filter(a => a.status === 'completed').length || 0,
          in_progress_assessments: client.assessments?.filter(a => a.status === 'in_progress').length || 0
        }
      }));

      setClients(clientsWithStats);
    } catch (error) {
      console.error('Error loading clients:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredClients = clients.filter(client =>
    client.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    client.industry?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900">Client Dashboard</h1>
          <p className="mt-2 text-sm text-gray-700">
            Manage your client organizations and their AI workforce assessments.
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          <Link
            to="/clients/new"
            className="inline-flex items-center justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 sm:w-auto"
          >
            <PlusIcon className="-ml-1 mr-2 h-4 w-4" />
            Add Client
          </Link>
        </div>
      </div>

      {/* Search */}
      <div className="mt-6">
        <input
          type="text"
          placeholder="Search clients by name or industry..."
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {/* Stats Summary */}
      <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ChartBarIcon className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Clients</dt>
                  <dd className="text-lg font-medium text-gray-900">{clients.length}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <DocumentTextIcon className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Assessments</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {clients.reduce((sum, client) => sum + client.stats.total_assessments, 0)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ChartBarIcon className="h-6 w-6 text-green-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Completed Assessments</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {clients.reduce((sum, client) => sum + client.stats.completed_assessments, 0)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Client List */}
      <div className="mt-8">
        <div className="bg-white shadow overflow-hidden sm:rounded-lg">
          {filteredClients.length === 0 ? (
            <div className="text-center py-12">
              <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No clients</h3>
              <p className="mt-1 text-sm text-gray-500">
                Get started by adding your first client organization.
              </p>
              <div className="mt-6">
                <Link
                  to="/clients/new"
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  <PlusIcon className="-ml-1 mr-2 h-4 w-4" />
                  Add Client
                </Link>
              </div>
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {filteredClients.map((client) => (
                <li key={client.id}>
                  <Link to={`/clients/${client.id}`} className="block hover:bg-gray-50">
                    <div className="px-4 py-4 sm:px-6">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <div>
                            <p className="text-sm font-medium text-blue-600 truncate">
                              {client.name}
                            </p>
                            <p className="text-sm text-gray-500">
                              {client.industry} • {client.employee_count?.toLocaleString()} employees
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-4">
                          <div className="text-right">
                            <p className="text-sm text-gray-900">
                              {client.stats.total_assessments} assessments
                            </p>
                            <p className="text-xs text-gray-500">
                              {client.stats.completed_assessments} completed
                            </p>
                          </div>
                          {client.stats.in_progress_assessments > 0 && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                              In Progress
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

export default ClientDashboard;
