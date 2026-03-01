import useConfig from '../hooks/useConfig';

function PricingCard({ plan, billingCycle, onSelect, popular }) {
  const config = useConfig();
  const { branding } = config;

  const price = billingCycle === 'monthly' ? plan.price_monthly : plan.price_annual;
  
  return (
    <div 
      className={`bg-white rounded-lg shadow-lg p-8 relative ${
        popular ? 'border-4' : 'border'
      }`}
      style={{ borderColor: popular ? branding.primary_color : '#e5e7eb' }}
    >
      {popular && (
        <span 
          className="absolute -top-4 left-1/2 transform -translate-x-1/2 px-4 py-1 rounded-full text-sm text-white"
          style={{ backgroundColor: branding.primary_color }}
        >
          Most Popular
        </span>
      )}
      
      <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
      <p className="text-gray-600 mb-6">{plan.description}</p>
      
      <div className="mb-6">
        <span className="text-5xl font-bold">${price}</span>
        <span className="text-gray-600">
          /{billingCycle === 'monthly' ? 'month' : 'year'}
        </span>
        {billingCycle === 'annual' && plan.annual_savings && (
          <p className="text-sm text-green-600 mt-2">{plan.annual_savings}</p>
        )}
      </div>
      
      <ul className="mb-8 space-y-3">
        {plan.features.map((feature, i) => (
          <li key={i} className="flex items-start">
            <span className="text-green-600 mr-2 flex-shrink-0">✓</span>
            <span className="text-gray-700">{feature}</span>
          </li>
        ))}
        {plan.limitations && plan.limitations.map((limitation, i) => (
          <li key={`limit-${i}`} className="flex items-start">
            <span className="text-gray-400 mr-2 flex-shrink-0">✗</span>
            <span className="text-gray-500">{limitation}</span>
          </li>
        ))}
      </ul>
      
      <button
        onClick={() => onSelect(plan)}
        className="w-full py-3 rounded-lg text-white hover:opacity-90"
        style={{ backgroundColor: branding.primary_color }}
      >
        {plan.cta_text}
      </button>
    </div>
  );
}

export default PricingCard;
