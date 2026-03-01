const Client = require('../models/Client');

class ClientManagementService {
  constructor(databaseClient) {
    this.db = databaseClient;
  }

  async createClient(clientData, userId) {
    try {
      const client = new Client({
        ...clientData,
        userId
      });

      const validation = client.validate();
      if (!validation.isValid) {
        throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
      }

      const { data, error } = await this.db
        .from('clients')
        .insert([client.toJSON()])
        .select()
        .single();

      if (error) throw error;

      return Client.fromDatabaseRow(data);
    } catch (error) {
      throw new Error(`Failed to create client: ${error.message}`);
    }
  }

  async getClient(clientId, userId) {
    try {
      const { data, error } = await this.db
        .from('clients')
        .select('*')
        .eq('id', clientId)
        .eq('user_id', userId)
        .single();

      if (error) throw error;
      if (!data) return null;

      return Client.fromDatabaseRow(data);
    } catch (error) {
      throw new Error(`Failed to get client: ${error.message}`);
    }
  }

  async updateClient(clientId, updates, userId) {
    try {
      // Verify ownership
      const existingClient = await this.getClient(clientId, userId);
      if (!existingClient) {
        throw new Error('Client not found or access denied');
      }

      // Update client data
      Object.assign(existingClient, updates);
      existingClient.updatedAt = new Date();

      const validation = existingClient.validate();
      if (!validation.isValid) {
        throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
      }

      const { data, error } = await this.db
        .from('clients')
        .update(existingClient.toJSON())
        .eq('id', clientId)
        .eq('user_id', userId)
        .select()
        .single();

      if (error) throw error;

      return Client.fromDatabaseRow(data);
    } catch (error) {
      throw new Error(`Failed to update client: ${error.message}`);
    }
  }

  async deleteClient(clientId, userId) {
    try {
      // Check for existing assessments
      const { data: assessments } = await this.db
        .from('assessments')
        .select('id')
        .eq('client_id', clientId);

      if (assessments && assessments.length > 0) {
        throw new Error('Cannot delete client with existing assessments');
      }

      const { error } = await this.db
        .from('clients')
        .delete()
        .eq('id', clientId)
        .eq('user_id', userId);

      if (error) throw error;

      return { success: true };
    } catch (error) {
      throw new Error(`Failed to delete client: ${error.message}`);
    }
  }

  async getClientsByUser(userId) {
    try {
      const { data, error } = await this.db
        .from('clients')
        .select('*')
        .eq('user_id', userId)
        .order('name');

      if (error) throw error;

      return data.map(row => Client.fromDatabaseRow(row));
    } catch (error) {
      throw new Error(`Failed to get clients: ${error.message}`);
    }
  }

  async getClientWithStats(clientId, userId) {
    try {
      const client = await this.getClient(clientId, userId);
      if (!client) return null;

      // Get assessment stats
      const { data: assessments, error: assessmentError } = await this.db
        .from('assessments')
        .select('id, status, created_at')
        .eq('client_id', clientId);

      if (assessmentError) throw assessmentError;

      const stats = {
        total_assessments: assessments.length,
        completed_assessments: assessments.filter(a => a.status === 'completed').length,
        in_progress_assessments: assessments.filter(a => a.status === 'in_progress').length,
        last_assessment_date: assessments.length > 0 
          ? Math.max(...assessments.map(a => new Date(a.created_at).getTime()))
          : null
      };

      return {
        ...client.toJSON(),
        stats
      };
    } catch (error) {
      throw new Error(`Failed to get client stats: ${error.message}`);
    }
  }

  async searchClients(userId, searchTerm) {
    try {
      const { data, error } = await this.db
        .from('clients')
        .select('*')
        .eq('user_id', userId)
        .or(`name.ilike.%${searchTerm}%,industry.ilike.%${searchTerm}%`)
        .order('name');

      if (error) throw error;

      return data.map(row => Client.fromDatabaseRow(row));
    } catch (error) {
      throw new Error(`Failed to search clients: ${error.message}`);
    }
  }
}

module.exports = ClientManagementService;
