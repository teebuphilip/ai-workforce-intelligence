import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import useConfig from '../hooks/useConfig';
import useAnalytics from '../hooks/useAnalytics';
import FeatureCard from '../components/FeatureCard';

function Home() {
  const navigate = useNavigate();
  const config = useConfig();
  const analytics = useAnalytics();
  const { home, branding } = config;

  useEffect(() => {
    analytics.trackPageView('/', 'Home');
  }, [analytics]);

  const handleCTA = () => {
    analytics.trackEvent('cta_click', { location: 'hero' });
    navigate('/signup');
  };

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section 
        className="py-20 px-4"
        style={{ backgroundColor: branding.primary_color + '10' }}
      >
        <div className="max-w-6xl mx-auto text-center">
          <h1 className="text-5xl font-bold mb-6">{home.hero.headline}</h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            {home.hero.subheadline}
          </p>
          <div className="flex justify-center gap-4">
            <button 
              onClick={handleCTA}
              className="px-8 py-4 rounded-lg text-white text-lg hover:opacity-90"
              style={{ backgroundColor: branding.primary_color }}
            >
              {home.hero.cta_primary}
            </button>
            <button 
              onClick={() => navigate('/pricing')}
              className="px-8 py-4 rounded-lg border-2 text-lg hover:bg-gray-50"
              style={{ 
                borderColor: branding.primary_color,
                color: branding.primary_color
              }}
            >
              {home.hero.cta_secondary}
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {home.features.map((feature, i) => (
              <FeatureCard
                key={i}
                icon={feature.icon}
                title={feature.title}
                description={feature.description}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Social Proof - Stats */}
      <section className="py-20 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8 text-center">
            {home.social_proof.stats.map((stat, i) => (
              <div key={i}>
                <div 
                  className="text-5xl font-bold mb-2"
                  style={{ color: branding.primary_color }}
                >
                  {stat.value}
                </div>
                <div className="text-gray-600">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">
            What Our Users Say
          </h2>
          <div className="grid md:grid-cols-2 gap-8">
            {home.social_proof.testimonials.map((testimonial, i) => (
              <div key={i} className="bg-white p-8 rounded-lg shadow">
                <p className="text-lg mb-4">"{testimonial.quote}"</p>
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-gray-200 rounded-full mr-4" />
                  <div>
                    <p className="font-semibold">{testimonial.author}</p>
                    <p className="text-sm text-gray-600">{testimonial.title}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section 
        className="py-20 px-4"
        style={{ backgroundColor: branding.primary_color }}
      >
        <div className="max-w-4xl mx-auto text-center text-white">
          <h2 className="text-4xl font-bold mb-4">
            {home.final_cta.headline}
          </h2>
          <p className="text-xl mb-8">
            {home.final_cta.subheadline}
          </p>
          <button 
            onClick={handleCTA}
            className="px-8 py-4 bg-white rounded-lg text-lg hover:bg-gray-100"
            style={{ color: branding.primary_color }}
          >
            {home.final_cta.button_text}
          </button>
        </div>
      </section>
    </div>
  );
}

export default Home;
