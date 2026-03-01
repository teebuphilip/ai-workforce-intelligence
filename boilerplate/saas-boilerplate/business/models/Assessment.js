const { v4: uuidv4 } = require('uuid');

class Assessment {
  constructor(data = {}) {
    this.id = data.id || uuidv4();
    this.clientId = data.clientId || data.client_id;
    this.assessmentData = data.assessmentData || data.assessment_data || {};
    this.status = data.status || 'in_progress';
    this.createdAt = data.createdAt || data.created_at || new Date();
    this.updatedAt = data.updatedAt || data.updated_at || new Date();
  }

  toJSON() {
    return {
      id: this.id,
      client_id: this.clientId,
      assessment_data: this.assessmentData,
      status: this.status,
      created_at: this.createdAt,
      updated_at: this.updatedAt
    };
  }

  addKPIData(kpiId, data) {
    if (!this.assessmentData.kpis) {
      this.assessmentData.kpis = {};
    }
    this.assessmentData.kpis[kpiId] = data;
    this.updatedAt = new Date();
  }

  getKPIData(kpiId) {
    return this.assessmentData.kpis?.[kpiId] || null;
  }

  markComplete() {
    this.status = 'completed';
    this.updatedAt = new Date();
  }

  validate() {
    const errors = [];
    
    if (!this.clientId) {
      errors.push('Client ID is required');
    }
    
    if (!['in_progress', 'completed', 'archived'].includes(this.status)) {
      errors.push('Invalid status');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  static fromDatabaseRow(row) {
    return new Assessment(row);
  }
}

module.exports = Assessment;
