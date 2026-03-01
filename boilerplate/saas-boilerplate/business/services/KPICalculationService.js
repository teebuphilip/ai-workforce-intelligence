const KPI = require('../models/KPI');
const _ = require('lodash');

class KPICalculationService {
  constructor() {
    this.kpiDefinitions = new Map();
    this.loadKPIDefinitions();
  }

  loadKPIDefinitions() {
    const definitions = KPI.getKPIDefinitions();
    definitions.forEach(def => {
      this.kpiDefinitions.set(def.kpi_id, new KPI(def));
    });
  }

  calculateKPI(kpiId, inputData) {
    try {
      const kpiInstance = this.kpiDefinitions.get(kpiId);
      if (!kpiInstance) {
        throw new Error(`Unknown KPI: ${kpiId}`);
      }

      // Validate input
      const validation = kpiInstance.validateInput(inputData);
      if (!validation.isValid) {
        return {
          success: false,
          error: `Missing required fields: ${validation.missingFields.join(', ')}`,
          kpi_id: kpiId
        };
      }

      // Calculate
      const result = kpiInstance.calculate(inputData);
      
      return {
        ...result,
        kpi_id: kpiId,
        kpi_name: kpiInstance.kpiName,
        calculated_at: new Date().toISOString()
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        kpi_id: kpiId
      };
    }
  }

  calculateAllKPIs(assessmentData) {
    const results = {};
    const kpiIds = Array.from(this.kpiDefinitions.keys());

    kpiIds.forEach(kpiId => {
      const kpiInputData = assessmentData.kpis?.[kpiId] || {};
      results[kpiId] = this.calculateKPI(kpiId, kpiInputData);
    });

    return results;
  }

  generateKPIScores(kpiResults) {
    const scores = {};
    const normalizationRules = {
      TTC: 'lower_is_better',
      PDPT: 'higher_is_better', 
      RPL: 'higher_is_better',
      BCI: 'higher_is_better',
      IMV: 'higher_is_better'
    };

    Object.keys(kpiResults).forEach(kpiId => {
      const result = kpiResults[kpiId];
      if (!result.success) {
        scores[kpiId] = {
          score: 0,
          grade: 'F',
          status: 'error',
          message: result.error
        };
        return;
      }

      const rawValue = result.value;
      const rule = normalizationRules[kpiId];
      
      // Normalize to 0-100 scale
      let normalizedScore;
      switch (kpiId) {
        case 'TTC':
          // Lower is better, assume 30 days is excellent, 90+ days is poor
          normalizedScore = Math.max(0, Math.min(100, 100 - ((rawValue - 30) / 60 * 100)));
          break;
        case 'PDPT':
          // Higher is better, assume 20%+ improvement is excellent
          normalizedScore = Math.max(0, Math.min(100, (rawValue / 20) * 100));
          break;
        case 'RPL':
          // Higher is better, normalize based on industry standards
          // Assume $50k+ per learner is excellent
          normalizedScore = Math.max(0, Math.min(100, (rawValue / 50000) * 100));
          break;
        case 'BCI':
          // Scale is 1-5, convert to 0-100
          normalizedScore = ((rawValue - 1) / 4) * 100;
          break;
        case 'IMV':
          // Percentage, use as-is
          normalizedScore = Math.max(0, Math.min(100, rawValue));
          break;
        default:
          normalizedScore = 50; // Default middle score
      }

      const grade = this.getGrade(normalizedScore);
      
      scores[kpiId] = {
        score: Math.round(normalizedScore),
        grade,
        status: 'calculated',
        raw_value: rawValue,
        formatted_value: result.formatted
      };
    });

    // Calculate overall score
    const validScores = Object.values(scores)
      .filter(s => s.status === 'calculated')
      .map(s => s.score);
    
    const overallScore = validScores.length > 0 
      ? Math.round(validScores.reduce((a, b) => a + b, 0) / validScores.length)
      : 0;

    return {
      individual_scores: scores,
      overall_score: overallScore,
      overall_grade: this.getGrade(overallScore),
      calculated_at: new Date().toISOString()
    };
  }

  getGrade(score) {
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'F';
  }

  getKPIDefinition(kpiId) {
    return this.kpiDefinitions.get(kpiId);
  }

  getAllKPIDefinitions() {
    return Array.from(this.kpiDefinitions.values()).map(kpi => ({
      kpi_id: kpi.kpiId,
      kpi_name: kpi.kpiName,
      definition: kpi.definition,
      inputs_required: kpi.inputsRequired,
      output_format: kpi.outputFormat
    }));
  }
}

module.exports = KPICalculationService;
