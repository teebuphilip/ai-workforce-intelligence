import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';

const KPI_DEFINITIONS = {
  TTC: {
    name: 'Time to Competency',
    description: 'Average days from role start to productivity threshold',
    fields: [
      { key: 'role_start_date', label: 'Role Start Date', type: 'date' },
      { key: 'performance_threshold_date', label: 'Performance Threshold Date', type: 'date' }
    ]
  },
  PDPT: {
    name: 'Performance Delta Post-Training',
    description: 'Percentage improvement in performance after training',
    fields: [
      { key: 'pre_training_metric', label: 'Pre-Training Performance Score', type: 'number' },
      { key: 'post_training_metric', label: 'Post-Training Performance Score', type: 'number' }
    ]
  },
  RPL: {
    name: 'Revenue per Learner',
    description: 'Revenue generated per trained employee',
    fields: [
      { key: 'revenue_attributed', label: 'Revenue Attributed ($)', type: 'number' },
      { key: 'trained_employee_count', label: 'Number of Trained Employees', type: 'number' }
    ]
  },
  BCI: {
    name: 'Behavioral Change Index',
    description: 'Manager-rated improvement score 30-90 days post training',
    fields: [
      { key: 'competency_rating_scores', label: 'Competency Ratings (1-5 scale, comma-separated)', type: 'text' }
    ]
  },
  IMV: {
    name: 'Internal Mobility Velocity',
    description: 'Percentage of roles filled internally',
    fields: [
      { key: 'internal_promotions', label: 'Internal Promotions/Fills', type: 'number' },
      { key: 'total_roles_filled', label: 'Total Roles Filled', type: 'number' }
    ]
  }
};

const AssessmentForm = ({ user, supabase }) => {
  const { clientId, assessmentId } = useParams();
  const navigate = useNavigate();
  
  const [client, setClient] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [currentKPI, setCurrentKPI] = useState('TTC');
  const [formData, setFormData] = useState({});
  const [completedKPIs, setCompletedKPIs] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, [clientId, assessmentId]);

  const loadData = async () => {
    try {
      // Load client
      const { data: clientData, error: clientError } = await supabase
        .from('clients')
        .select('*')
        .eq('id', clientId)
        .eq('user_id', user.id)
        .single();

      if (clientError) throw clientError;
      setClient(clientData);

      // Load or create assessment
      if (assessmentId && assessmentId !== 'new') {
        const { data: assessmentData, error: assessmentError } = await supabase
          .from('assessments')
          .select('*')
          .eq('id', assessmentId)
          .single();

        if (assessmentError) throw assessmentError;
        setAssessment(assessmentData);
        
        // Set completed KPIs
        if (assessmentData.assessment_data?.kpis) {
          setCompletedKPIs(new Set(Object.keys(assessmentData.assessment_data.kpis)));
        }
      } else {
        // Create new assessment
        const newAssessment = {
          client_id: clientId,
          assessment_data: { kpis: {} },
          status: 'in_progress'
        };

        const { data: createdAssessment, error: createError } = await supabase
          .from('assessments')
          .insert([newAssessment])
          .select()
          .single();

        if (createError) throw createError;
        setAssessment(createdAssessment);
        navigate(`/clients/${clientId}/assessments/${createdAssessment.id}`);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const saveKPIData = async () => {
    setSaving(true);
    try {
      let processedData = { ...formData };
      
      // Special handling for BCI competency ratings
      if (currentKPI === 'BCI' && formData.competency_rating_scores) {
        const ratings = formData.competency_rating_scores
          .split(',')
          .map(r => parseFloat(r.trim()))
          .filter(r => !isNaN(r) && r >= 1 && r <= 5);
        processedData.competency_rating_scores = ratings;
      }

      // Update assessment data
      const updatedAssessmentData = {
        ...assessment.assessment_data,
        kpis: {
          ...assessment.assessment_data.kpis,
          [currentKPI]: processedData
        }
      };

      const { error } = await supabase
        .from('assessments')
        .update({
          assessment_data: updatedAssessmentData,
          updated_at: new Date()
        })
        .eq('id', assessment.id);

      if (error) throw error;

      // Update local state
      setAssessment(prev => ({
        ...prev,
        assessment_data: updatedAssessmentData
      }));
      
      setCompletedKPIs(prev => new Set([...prev, currentKPI]));
      setFormData({});

      // Move to next KPI
      const kpiOrder = ['TTC', 'PDPT', 'RPL', 'BCI', 'IMV'];
      const currentIndex = kpiOrder.indexOf(currentKPI);
      if (currentIndex < kpiOrder.length - 1) {
        setCurrentKPI(kpiOrder[currentIndex + 1]);
      }
    } catch (error) {
      console.error('Error saving KPI data:', error);
    } finally {
      setSaving(false);
    }
  };

  const completeAssessment = async () => {
    try {
      const { error } = await supabase
        .from('assessments')
        .update({ status: 'completed' })
        .eq('id', assessment.id);

      if (error) throw error;

      navigate(`/clients/${clientId}/assessments/${assessment.id}/report`);
    } catch (error) {
      console.error('Error completing assessment:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const kpiDef = KPI_DEFINITIONS[currentKPI];
  const isCurrentKPIComplete = completedKPIs.has(currentKPI);
  const allKPIsComplete = Object.keys(KPI_DEFINITIONS).every(kpi => completedKPIs.has(kpi));

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">
          AI Workforce Assessment: {client?.name}
        </h1>
        <p className="mt-2 text-sm text-gray-600">
          Complete the KPI data collection for workforce intelligence analysis.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* KPI Navigation */}
        <div className="lg:col-span-1">
          <nav className="space-y-2">
            {Object.entries(KPI_DEFINITIONS).map(([kpiId, def]) => (
              <button
                key={kpiId}
                onClick={() => setCurrentKPI(kpiId)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium flex items-center justify-between ${
                  currentKPI === kpiId
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <span>{def.name}</span>
                {completedKPIs.has(kpiId) && (
                  <CheckIcon className="h-4 w-4 text-green-500" />
                )}
              </button>
            ))}
          </nav>

          <div className="mt-6 bg-gray-50 p-4 rounded-lg">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Progress</h4>
            <div className="flex items-center">
              <div className="flex-1 bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full"
                  style={{ width: `${(completedKPIs.size / Object.keys(KPI_DEFINITIONS).length) * 100}%` }}
                ></div>
              </div>
              <span className="ml-2 text-sm text-gray-600">
                {completedKPIs.size}/{Object.keys(KPI_DEFINITIONS).length}
              </span>
            </div>
          </div>
        </div>

        {/* KPI Form */}
        <div className="lg:col-span-3">
          <div className="bg-white shadow rounded-lg p-6">
            <div className="mb-6">
              <h2 className="text-lg font-medium text-gray-900">{kpiDef.name}</h2>
              <p className="mt-1 text-sm text-gray-600">{kpiDef.description}</p>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); saveKPIData(); }}>
              <div className="space-y-4">
                {kpiDef.fields.map((field) => (
                  <div key={field.key}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {field.label}
                    </label>
                    {field.type === 'text' || field.type === 'number' ? (
                      <input
                        type={field.type}
                        value={formData[field.key] || ''}
                        

<!-- CONTINUATION -->

**FILE: app/components/KPIManagement.js**
