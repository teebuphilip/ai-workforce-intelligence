class KPI {
  constructor(definition) {
    this.kpiId = definition.kpi_id;
    this.kpiName = definition.kpi_name;
    this.type = definition.type;
    this.definition = definition.definition;
    this.inputsRequired = definition.inputs_required;
    this.calculationLogic = definition.calculation_logic;
    this.aggregationMethods = definition.aggregation_methods;
    this.outputFormat = definition.output_format;
  }

  calculate(inputData) {
    try {
      switch (this.kpiId) {
        case 'TTC':
          return this.calculateTTC(inputData);
        case 'PDPT':
          return this.calculatePDPT(inputData);
        case 'RPL':
          return this.calculateRPL(inputData);
        case 'BCI':
          return this.calculateBCI(inputData);
        case 'IMV':
          return this.calculateIMV(inputData);
        default:
          throw new Error(`Unknown KPI: ${this.kpiId}`);
      }
    } catch (error) {
      return {
        success: false,
        error: error.message,
        value: null
      };
    }
  }

  calculateTTC(data) {
    const { role_start_date, performance_threshold_date } = data;
    
    if (!role_start_date || !performance_threshold_date) {
      throw new Error('Missing required dates for TTC calculation');
    }

    const startDate = new Date(role_start_date);
    const thresholdDate = new Date(performance_threshold_date);
    const diffTime = Math.abs(thresholdDate - startDate);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    return {
      success: true,
      value: diffDays,
      formatted: `${diffDays} days`,
      calculation_used: 'performance_threshold_date - role_start_date'
    };
  }

  calculatePDPT(data) {
    const { pre_training_metric, post_training_metric } = data;
    
    if (pre_training_metric === undefined || post_training_metric === undefined) {
      throw new Error('Missing required metrics for PDPT calculation');
    }

    if (pre_training_metric === 0) {
      throw new Error('Pre-training metric cannot be zero');
    }

    const improvement = ((post_training_metric - pre_training_metric) / pre_training_metric) * 100;

    return {
      success: true,
      value: improvement,
      formatted: `${improvement.toFixed(1)}%`,
      calculation_used: '(post - pre) / pre * 100'
    };
  }

  calculateRPL(data) {
    const { revenue_attributed, trained_employee_count } = data;
    
    if (revenue_attributed === undefined || trained_employee_count === undefined) {
      throw new Error('Missing required data for RPL calculation');
    }

    if (trained_employee_count === 0) {
      throw new Error('Trained employee count cannot be zero');
    }

    const rpl = revenue_attributed / trained_employee_count;

    return {
      success: true,
      value: rpl,
      formatted: `$${rpl.toLocaleString()}`,
      calculation_used: 'revenue_attributed / trained_employee_count'
    };
  }

  calculateBCI(data) {
    const { competency_rating_scores } = data;
    
    if (!Array.isArray(competency_rating_scores) || competency_rating_scores.length === 0) {
      throw new Error('Competency rating scores must be a non-empty array');
    }

    const average = competency_rating_scores.reduce((sum, score) => sum + score, 0) / competency_rating_scores.length;

    return {
      success: true,
      value: average,
      formatted: `${average.toFixed(1)}/5.0`,
      calculation_used: 'average(competency_rating_scores)'
    };
  }

  calculateIMV(data) {
    const { internal_promotions, total_roles_filled } = data;
    
    if (internal_promotions === undefined || total_roles_filled === undefined) {
      throw new Error('Missing required data for IMV calculation');
    }

    if (total_roles_filled === 0) {
      throw new Error('Total roles filled cannot be zero');
    }

    const imv = (internal_promotions / total_roles_filled) * 100;

    return {
      success: true,
      value: imv,
      formatted: `${imv.toFixed(1)}%`,
      calculation_used: 'internal_promotions / total_roles_filled * 100'
    };
  }

  validateInput(inputData) {
    const missing = this.inputsRequired.filter(field => !(field in inputData));
    
    return {
      isValid: missing.length === 0,
      missingFields: missing
    };
  }

  static getKPIDefinitions() {
    return [
      {
        kpi_id: 'TTC',
        kpi_name: 'Time to Competency',
        type: 'time_duration',
        definition: 'Average number of days from role start to defined productivity threshold.',
        inputs_required: ['role_start_date', 'performance_threshold_date'],
        calculation_logic: 'performance_threshold_date - role_start_date',
        aggregation_methods: ['organization_average', 'department_average', 'time_trend'],
        output_format: 'days'
      },
      {
        kpi_id: 'PDPT',
        kpi_name: 'Performance Delta Post-Training',
        type: 'percentage_change',
        definition: 'Percentage improvement in performance metric after training.',
        inputs_required: ['pre_training_metric', 'post_training_metric'],
        calculation_logic: '(post_training_metric - pre_training_metric) / pre_training_metric',
        aggregation_methods: ['program_average', 'organization_average', 'program_ranking'],
        output_format: 'percentage'
      },
      {
        kpi_id: 'RPL',
        kpi_name: 'Revenue per Learner',
        type: 'monetary_ratio',
        definition: 'Revenue generated or influenced per trained employee.',
        inputs_required: ['revenue_attributed', 'trained_employee_count'],
        calculation_logic: 'revenue_attributed / trained_employee_count',
        aggregation_methods: ['organization_average', 'trained_vs_untrained_comparison'],
        output_format: 'currency'
      },
      {
        kpi_id: 'BCI',
        kpi_name: 'Behavioral Change Index',
        type: 'scored_index',
        definition: 'Manager-rated improvement score 30-90 days post training.',
        inputs_required: ['competency_rating_scores'],
        calculation_logic: 'average(competency_rating_scores)',
        aggregation_methods: ['organization_average', 'distribution_analysis', 'correlation_with_PDPT'],
        output_format: '1-5_scale'
      },
      {
        kpi_id: 'IMV',
        kpi_name: 'Internal Mobility Velocity',
        type: 'percentage_ratio',
        definition: 'Percentage of roles filled internally.',
        inputs_required: ['internal_promotions', 'total_roles_filled'],
        calculation_logic: 'internal_promotions / total_roles_filled',
        aggregation_methods: ['organization_rate', 'year_over_year_change'],
        output_format: 'percentage'
      }
    ];
  }
}

module.exports = KPI;
