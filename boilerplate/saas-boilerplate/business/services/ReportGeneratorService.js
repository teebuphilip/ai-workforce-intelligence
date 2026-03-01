const Report = require('../models/Report');
const KPICalculationService = require('./KPICalculationService');
const { format } = require('date-fns');

class ReportGeneratorService {
  constructor(databaseClient) {
    this.db = databaseClient;
    this.kpiService = new KPICalculationService();
  }

  async generateReport(assessmentId) {
    try {
      // Get assessment data
      const { data: assessmentData, error: assessmentError } = await this.db
        .from('assessments')
        .select(`
          *,
          clients (
            name,
            industry,
            employee_count
          )
        `)
        .eq('id', assessmentId)
        .single();

      if (assessmentError) throw assessmentError;

      // Calculate KPI results
      const kpiResults = this.kpiService.calculateAllKPIs(assessmentData.assessment_data);
      const kpiScores = this.kpiService.generateKPIScores(kpiResults);

      // Generate report
      const report = new Report({
        assessmentId,
        reportData: {
          client_info: assessmentData.clients,
          assessment_summary: {
            completed_at: assessmentData.updated_at,
            status: assessmentData.status
          },
          kpi_results: kpiResults,
          kpi_scores: kpiScores,
          executive_summary: this.generateExecutiveSummary(assessmentData.clients, kpiScores),
          recommendations: this.generateRecommendations(kpiScores),
          appendix: {
            methodology: this.getMethodologyDescription(),
            definitions: this.kpiService.getAllKPIDefinitions()
          }
        }
      });

      // Save report
      const { data: savedReport, error: saveError } = await this.db
        .from('reports')
        .insert([report.toJSON()])
        .select()
        .single();

      if (saveError) throw saveError;

      return Report.fromDatabaseRow(savedReport);
    } catch (error) {
      throw new Error(`Failed to generate report: ${error.message}`);
    }
  }

  generateExecutiveSummary(clientInfo, kpiScores) {
    const overallScore = kpiScores.overall_score;
    const overallGrade = kpiScores.overall_grade;
    
    let performanceLevel;
    if (overallScore >= 85) {
      performanceLevel = 'excellent';
    } else if (overallScore >= 70) {
      performanceLevel = 'strong';
    } else if (overallScore >= 55) {
      performanceLevel = 'moderate';
    } else {
      performanceLevel = 'developing';
    }

    const topKPI = Object.entries(kpiScores.individual_scores)
      .filter(([_, data]) => data.status === 'calculated')
      .sort(([_, a], [__, b]) => b.score - a.score)[0];

    const bottomKPI = Object.entries(kpiScores.individual_scores)
      .filter(([_, data]) => data.status === 'calculated')  
      .sort(([_, a], [__, b]) => a.score - b.score)[0];

    return {
      overall_assessment: `${clientInfo.name} demonstrates ${performanceLevel} AI workforce readiness with an overall score of ${overallScore}/100 (Grade ${overallGrade}).`,
      key_findings: [
        `Strongest performance area: ${topKPI ? this.getKPIDisplayName(topKPI[0]) : 'N/A'}`,
        `Primary improvement opportunity: ${bottomKPI ? this.getKPIDisplayName(bottomKPI[0]) : 'N/A'}`,
        `Organization size: ${clientInfo.employee_count} employees in ${clientInfo.industry} sector`
      ],
      strategic_implications: this.getStrategicImplications(overallScore, kpiScores.individual_scores),
      generated_date: format(new Date(), 'MMMM d, yyyy')
    };
  }

  generateRecommendations(kpiScores) {
    const recommendations = [];
    
    Object.entries(kpiScores.individual_scores).forEach(([kpiId, scoreData]) => {
      if (scoreData.status !== 'calculated') return;
      
      const score = scoreData.score;
      
      switch (kpiId) {
        case 'TTC':
          if (score < 70) {
            recommendations.push({
              priority: 'High',
              area: 'Time to Competency',
              recommendation: 'Implement structured onboarding programs and mentorship systems to reduce time-to-productivity.',
              expected_impact: 'Reduce new hire ramp-up time by 25-40%'
            });
          }
          break;
        case 'PDPT':
          if (score < 70) {
            recommendations.push({
              priority: 'High', 
              area: 'Training Effectiveness',
              recommendation: 'Redesign training programs with more practical, role-specific content and post-training reinforcement.',
              expected_impact: 'Improve performance delta by 15-30%'
            });
          }
          break;
        case 'RPL':
          if (score < 70) {
            recommendations.push({
              priority: 'Medium',
              area: 'Revenue per Learner',
              recommendation: 'Better align training investments with revenue-generating activities and track ROI more precisely.',
              expected_impact: 'Increase training ROI by 20-50%'
            });
          }
          break;
        case 'BCI':
          if (score < 70) {
            recommendations.push({
              priority: 'Medium',
              area: 'Behavioral Change',
              recommendation: 'Implement manager coaching programs and behavioral reinforcement systems post-training.',
              expected_impact: 'Improve sustained behavior change by 35%'
            });
          }
          break;
        case 'IMV':
          if (score < 70) {
            recommendations.push({
              priority: 'Low',
              area: 'Internal Mobility',
              recommendation: 'Create clearer career paths and internal opportunity communication systems.',
              expected_impact: 'Increase internal fill rate by 15-25%'
            });
          }
          break;
      }
    });

    // Add strategic recommendations based on overall score
    const overallScore = kpiScores.overall_score;
    if (overallScore < 60) {
      recommendations.unshift({
        priority: 'Critical',
        area: 'Overall Strategy',
        recommendation: 'Conduct comprehensive workforce strategy review and implement foundational learning infrastructure.',
        expected_impact: 'Establish baseline for measurable workforce development'
      });
    }

    return recommendations;
  }

  getStrategicImplications(overallScore, individualScores) {
    if (overallScore >= 85) {
      return 'Organization is well-positioned for AI transformation with strong foundational workforce capabilities.';
    } else if (overallScore >= 70) {
      return 'Solid workforce foundation with targeted improvement opportunities for AI readiness enhancement.';
    } else if (overallScore >= 55) {
      return 'Moderate workforce readiness requiring focused development in key performance areas before AI scaling.';
    } else {
      return 'Fundamental workforce development needed to establish baseline capabilities for AI transformation.';
    }
  }

  getKPIDisplayName(kpiId) {
    const names = {
      TTC: 'Time to Competency',
      PDPT: 'Performance Delta Post-Training', 
      RPL: 'Revenue per Learner',
      BCI: 'Behavioral Change Index',
      IMV: 'Internal Mobility Velocity'
    };
    return names[kpiId] || kpiId;
  }

  getMethodologyDescription() {
    return {
      overview: 'AI Workforce Intelligence assessment using five core KPIs measuring learning effectiveness, performance impact, and organizational readiness.',
      scoring_method: 'Normalized 0-100 scale with industry benchmarks and weighted composite scoring.',
      data_sources: 'Consultant-collected organizational data with optional API integrations for enhanced accuracy.',
      validation: 'Cross-referenced metrics with statistical validation and outlier detection.'
    };
  }

  async getReport(reportId) {
    try {
      const { data, error } = await this.db
        .from('reports')
        .select('*')
        .eq('id', reportId)
        .single();

      if (error) throw error;
      if (!data) return null;

      return Report.fromDatabaseRow(data);
    } catch (error) {
      throw new Error(`Failed to get report: ${error.message}`);
    }
  }

  async getReportsByAssessment(assessmentId) {
    try {
      const { data, error } = await this.db
        .from('reports')
        .select('*')
        .eq('assessment_id', assessmentId)
        .order('generated_at', { ascending: false });

      if (error) throw error;

      return data.map(row => Report.fromDatabaseRow(row));
    } catch (error) {
      throw new Error(`Failed to get reports: ${error.message}`);
    }
  }
}

module.exports = ReportGeneratorService;
