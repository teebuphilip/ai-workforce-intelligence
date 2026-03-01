const { v4: uuidv4 } = require('uuid');

class Client {
  constructor(data = {}) {
    this.id = data.id || uuidv4();
    this.userId = data.userId || data.user_id;
    this.name = data.name || '';
    this.industry = data.industry || '';
    this.employeeCount = data.employeeCount || data.employee_count || 0;
    this.contactEmail = data.contactEmail || data.contact_email || '';
    this.createdAt = data.createdAt || data.created_at || new Date();
    this.updatedAt = data.updatedAt || data.updated_at || new Date();
  }

  toJSON() {
    return {
      id: this.id,
      user_id: this.userId,
      name: this.name,
      industry: this.industry,
      employee_count: this.employeeCount,
      contact_email: this.contactEmail,
      created_at: this.createdAt,
      updated_at: this.updatedAt
    };
  }

  validate() {
    const errors = [];
    
    if (!this.name || this.name.trim().length < 2) {
      errors.push('Client name must be at least 2 characters');
    }
    
    if (!this.userId) {
      errors.push('User ID is required');
    }
    
    if (this.employeeCount < 0) {
      errors.push('Employee count cannot be negative');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  static fromDatabaseRow(row) {
    return new Client(row);
  }
}

module.exports = Client;
