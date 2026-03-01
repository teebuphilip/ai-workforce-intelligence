import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';

const STEPS = [
  {
    id: 'profile_setup',
    title: 'Set Up Your Profile',
    description: 'Tell us your name and company so we can personalize your experience.',
    cta: 'Complete Profile',
  },
  {
    id: 'plan_selected',
    title: 'Choose Your Plan',
    description: 'Pick the plan that works best for your needs. You can upgrade anytime.',
    cta: 'Select Plan',
  },
  {
    id: 'integration_connected',
    title: 'Connect an Integration',
    description: 'Connect your first integration to unlock the full platform.',
    cta: 'Connect Integration',
  },
];

function Onboarding() {
  const { getAccessTokenSilently } = useAuth0();
  const navigate = useNavigate();
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completedSteps, setCompletedSteps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchOnboardingState();
  }, []);

  async function fetchOnboardingState() {
    try {
      const token = await getAccessTokenSilently();
      const res = await fetch('/api/onboarding', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load onboarding state');
      const data = await res.json();

      if (data.is_complete) {
        navigate('/dashboard');
        return;
      }

      const done = data.completed_steps || [];
      setCompletedSteps(done);
      const nextIncomplete = STEPS.findIndex(s => !done.includes(s.id));
      setCurrentStepIndex(nextIncomplete >= 0 ? nextIncomplete : 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function completeCurrentStep() {
    const step = STEPS[currentStepIndex];
    setSaving(true);
    setError(null);
    try {
      const token = await getAccessTokenSilently();
      const res = await fetch(`/api/onboarding/step/${step.id}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to complete step');
      const data = await res.json();

      setCompletedSteps(data.completed_steps);

      if (data.is_complete) {
        navigate('/dashboard');
        return;
      }

      const nextIndex = currentStepIndex + 1;
      if (nextIndex < STEPS.length) {
        setCurrentStepIndex(nextIndex);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500">Loading your onboarding...</p>
      </div>
    );
  }

  const currentStep = STEPS[currentStepIndex];
  const progress = Math.round((completedSteps.length / STEPS.length) * 100);

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-lg mx-auto">
        <h1 className="text-3xl font-bold text-center mb-2">Welcome!</h1>
        <p className="text-gray-600 text-center mb-8">
          Complete these steps to get started.
        </p>

        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex justify-between text-sm text-gray-500 mb-1">
            <span>Step {currentStepIndex + 1} of {STEPS.length}</span>
            <span>{progress}% complete</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Step indicators */}
        <div className="flex justify-around mb-8">
          {STEPS.map((step, index) => (
            <div key={step.id} className="flex flex-col items-center gap-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold
                  ${completedSteps.includes(step.id)
                    ? 'bg-green-500 text-white'
                    : index === currentStepIndex
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-500'
                  }`}
              >
                {completedSteps.includes(step.id) ? '✓' : index + 1}
              </div>
              <span className="text-xs text-gray-500 text-center w-20">
                {step.title.split(' ').slice(0, 2).join(' ')}
              </span>
            </div>
          ))}
        </div>

        {/* Current step card */}
        <div className="bg-white rounded-xl shadow-md p-8">
          <h2 className="text-xl font-semibold mb-3">{currentStep.title}</h2>
          <p className="text-gray-600 mb-6">{currentStep.description}</p>

          {error && (
            <p className="text-red-500 text-sm mb-4">{error}</p>
          )}

          <button
            onClick={completeCurrentStep}
            disabled={saving}
            className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold
                       hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : currentStep.cta}
          </button>
        </div>

        <p className="text-center text-sm text-gray-400 mt-4">
          You can finish this later from your dashboard.
        </p>
      </div>
    </div>
  );
}

export default Onboarding;
