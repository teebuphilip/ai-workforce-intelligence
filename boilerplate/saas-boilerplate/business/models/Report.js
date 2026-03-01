const { v4: uuidv4 } = require('uuid');

class Report {
  constructor(data = {}) {
    this.id = data.id || uuidv4();
    this.assessmentId = data.assessmentId || data.assessment_id;
    this.reportData = data.reportData || data.report_data || {};
    this.generatedAt = data.generatedAt || data.generated_at || new Date();
  }

  toJSON() {
    return {
      id: this.id,
      assessment_id: this.assessmentId,
      report_data: this.reportData,
      generated_at: this.generatedAt
    };
  }

  setExecutiveSummary(summary) {
    this.reportData.executive_summary = summary;
  }

  addKPIResult(kpiId, result) {
    if (!this.reportData.kpi_results) {
      this.reportData.kpi_results = {};
    }
    this.reportData.kpi_results[kpiId] = result;
  }

  addRecommendation(recommendation) {
    if (!this.reportData.recommendations) {
      this.reportData.recommendations = [];
    }
    this.reportData.recommendations.push(recommendation);
  }

  getDownloadableData() {
    return {
      title: 'AI Workforce Intelligence Report',
      generated_at: this.generatedAt,
      executive_summary: this.reportData.executive_summary,
      kpi_results: this.reportData.kpi_results,
      recommendations: this.reportData.recommendations,
      appendix: this.reportData.appendix
    };
  }

  validate() {
    const errors = [];
    
    if (!this.assessmentId) {
      errors.push('Assessment ID is required');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  static fromDatabaseRow(row) {
    return new Report(row);
  }
}

module.exports = Report;
