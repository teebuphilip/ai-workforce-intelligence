const Assessment = require('../models/Assessment');
const { v4: uuidv4 } = require('uuid');

class AssessmentService {
  constructor(databaseClient) {
    this.db = databaseClient;
  }

  async createAssessment(clientId, userId) {
    try {
      const assessment = new Assessment({
        clientId,
        userId,
        assessmentData: {
          kpis: {},
          metadata: {
            created_by: userId,
            version: '1.0'
          }
        }
      });

      const validation = assessment.validate();
      if (!validation.isValid) {
        throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
      }

      const result = await this.db
        .from('assessments')
        .insert([assessment.toJSON()])
        .select()
        .single();

      return Assessment.fromDatabaseRow(result);
    } catch (error) {
      throw new Error(`Failed to create assessment: ${error.message}`);
    }
  }

  async getAssessment(assessmentId) {
    try {
      const { data, error } = await this.db
        .from('assessments')
        .select('*')
        .eq('id', assessmentId)
        .single();

      if (error) throw error;
      if (!data) return null;

      return Assessment.fromDatabaseRow(data);
    } catch (error) {
      throw new Error(`Failed to get assessment: ${error.message}`);
    }
  }

  async updateAssessmentData(assessmentId, kpiId, kpiData) {
    try {
      // Get current assessment
      const assessment = await this.getAssessment(assessmentId);
      if (!assessment) {
        throw new Error('Assessment not found');
      }

      // Update KPI data
      assessment.addKPIData(kpiId, kpiData);

      // Save to database
      const { data, error } = await this.db
        .from('assessments')
        .update({ 
          assessment_data: assessment.assessmentData,
          updated_at: new Date()
        })
        .eq('id', assessmentId)
        .select()
        .single();

      if (error) throw error;

      return Assessment.fromDatabaseRow(data);
    } catch (error) {
      throw new Error(`Failed to update assessment: ${error.message}`);
    }
  }

  async completeAssessment(assessmentId) {
    try {
      const { data, error } = await this.db
        .from('assessments')
        .update({ 
          status: 'completed',
          updated_at: new Date()
        })
        .eq('id', assessmentId)
        .select()
        .single();

      if (error) throw error;

      return Assessment.fromDatabaseRow(data);
    } catch (error) {
      throw new Error(`Failed to complete assessment: ${error.message}`);
    }
  }

  async getAssessmentsByClient(clientId) {
    try {
      const { data, error } = await this.db
        .from('assessments')
        .select('*')
        .eq('client_id', clientId)
        .order('created_at', { ascending: false });

      if (error) throw error;

      return data.map(row => Assessment.fromDatabaseRow(row));
    } catch (error) {
      throw new Error(`Failed to get assessments: ${error.message}`);
    }
  }

  async getAssessmentProgress(assessmentId) {
    try {
      const assessment = await this.getAssessment(assessmentId);
      if (!assessment) return null;

      const kpiData = assessment.assessmentData.kpis || {};
      const requiredKPIs = ['TTC', 'PDPT', 'RPL', 'BCI', 'IMV'];
      const completedKPIs = requiredKPIs.filter(kpiId => kpiData[kpiId]);

      return {
        total: requiredKPIs.length,
        completed: completedKPIs.length,
        percentage: Math.round((completedKPIs.length / requiredKPIs.length) * 100),
        remaining: requiredKPIs.filter(kpiId => !kpiData[kpiId])
      };
    } catch (error) {
      throw new Error(`Failed to get progress: ${error.message}`);
    }
  }
}

module.exports = AssessmentService;
