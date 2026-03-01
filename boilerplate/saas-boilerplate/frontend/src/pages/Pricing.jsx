import { useState, useEffect, useMemo } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import useConfig from '../hooks/useConfig';
import useAnalytics from '../hooks/useAnalytics';
import PricingCard from '../components/PricingCard';
import api from '../utils/api';

/**
 * Build plan list from stripe_products in business_config.json.
 *
 * WHY: Plans are defined once in config by the hero.
 * Pricing page reads them dynamically - supports any number of plans.
 * No hardcoded plan count anywhere in code.
 *
 * stripe_products entry expected shape:
 * {
 *   "prod_abc": {
 *     "name": "Pro",
 *     "price": "$29/mo",
 *     "price_monthly": 29,
 *     "price_annual": 290,
 *     "description": "For power users",
 *     "entitlements": ["dashboard", "ai_sorting"],
 *     "features": ["Unlimited rules", "AI sorting"],   // display labels
 *     "limitations": ["No team access"],               // optional
 *     "popular": true,                                 // optional
 *     "cta_text": "Get Started",                       // optional
 *     "stripe_price_id_monthly": "price_xxx",          // set by hero
 *     "stripe_price_id_annual":  "price_yyy"           // set by hero
 *   }
 * }
 */
function buildPlansFromConfig(stripe_products = {}) {
  return Object.entries(stripe_products)
    // Filter out _comment keys
    .filter(([key]) => !key.startsWith('_'))
    .map(([product_id, product]) => ({
      product_id,
      name:                   product.name        || 'Plan',
      description:            product.description || '',
      price_monthly:          product.price_monthly ?? 0,
      price_annual:           product.price_annual  ?? 0,
      annual_savings:         product.annual_savings || null,
      features:               product.features    || product.entitlements || [],
      limitations:            product.limitations || [],
      popular:                product.popular     || false,
      cta_text:               product.cta_text    || 'Get Started',
      stripe_price_id_monthly: product.stripe_price_id_monthly || null,
      stripe_price_id_annual:  product.stripe_price_id_annual  || null,
    }))
    // Sort: free first, then by price, popular plans floated up
    .sort((a, b) => a.price_monthly - b.price_monthly);
}

function Pricing() {
  const [billingCycle, setBillingCycle] = useState('monthly');
  const { isAuthenticated, loginWithRedirect, user } = useAuth0();
  const config = useConfig();
  const analytics = useAnalytics();
  const { pricing, branding, stripe_products } = config;

  // WHY useMemo: Recompute only when config changes, not on every render
  const plans = useMemo(
    () => buildPlansFromConfig(stripe_products),
    [stripe_products]
  );

  useEffect(() => {
    analytics.trackPageView('/pricing', 'Pricing');
  }, [analytics]);

  const handleSubscribe = async (plan) => {
    analytics.trackEvent('pricing_cta_click', {
      plan: plan.name,
      billing: billingCycle
    });

    if (!isAuthenticated) {
      loginWithRedirect({ screen_hint: 'signup' });
      return;
    }

    if (plan.price_monthly === 0) {
      alert('Free plan activated!');
      return;
    }

    const priceId = billingCycle === 'monthly'
      ? plan.stripe_price_id_monthly
      : plan.stripe_price_id_annual;

    try {
      const response = await api.post('/subscribe', {
        price_id: priceId,
        user_id: user?.sub
      });
      if (response.data.payment_link) {
        window.location.href = response.data.payment_link;
      }
    } catch (error) {
      console.error('Subscription error:', error);
      alert('Failed to create checkout session. Please try again.');
    }
  };

  /**
   * Dynamic grid columns based on plan count.
   * WHY: Hero may have 2, 3, 4, or 5 plans. Grid adapts.
   * Caps at 4 columns on large screens to keep cards readable.
   */
  const gridClass = {
    1: 'md:grid-cols-1 max-w-md mx-auto',
    2: 'md:grid-cols-2 max-w-3xl mx-auto',
    3: 'md:grid-cols-3',
    4: 'md:grid-cols-4',
    5: 'md:grid-cols-3 lg:grid-cols-5',
  }[plans.length] || 'md:grid-cols-3';

  return (
    <div className="min-h-screen py-20 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold mb-4">{pricing?.headline}</h1>
          <p className="text-xl text-gray-600">{pricing?.subheadline}</p>
        </div>

        {/* Billing Toggle - only show if any plan has annual pricing */}
        {plans.some(p => p.stripe_price_id_annual) && (
          <div className="flex justify-center mb-12">
            <div className="inline-flex rounded-lg border border-gray-300 p-1">
              <button
                onClick={() => setBillingCycle('monthly')}
                className={`px-6 py-2 rounded-md transition-colors ${
                  billingCycle === 'monthly' ? 'text-white' : 'text-gray-700'
                }`}
                style={{
                  backgroundColor: billingCycle === 'monthly' ? branding.primary_color : 'transparent'
                }}
              >
                Monthly
              </button>
              <button
                onClick={() => setBillingCycle('annual')}
                className={`px-6 py-2 rounded-md transition-colors ${
                  billingCycle === 'annual' ? 'text-white' : 'text-gray-700'
                }`}
                style={{
                  backgroundColor: billingCycle === 'annual' ? branding.primary_color : 'transparent'
                }}
              >
                Annual
                <span className="ml-2 text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                  Save 20%
                </span>
              </button>
            </div>
          </div>
        )}

        {/* Pricing Cards - dynamic count from config */}
        {plans.length === 0 ? (
          <div className="text-center text-gray-500 py-20">
            <p>No plans configured yet.</p>
            <p className="text-sm mt-2">Add plans to stripe_products in business_config.json</p>
          </div>
        ) : (
          <div className={`grid gap-8 mb-20 ${gridClass}`}>
            {plans.map((plan) => (
              <PricingCard
                key={plan.product_id}
                plan={plan}
                billingCycle={billingCycle}
                onSelect={handleSubscribe}
                popular={plan.popular}
              />
            ))}
          </div>
        )}

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            {pricing.faq.map((item, i) => (
              <div key={i} className="bg-white rounded-lg shadow p-6">
                <h3 className="font-semibold text-lg mb-2">{item.question}</h3>
                <p className="text-gray-600">{item.answer}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Pricing;
