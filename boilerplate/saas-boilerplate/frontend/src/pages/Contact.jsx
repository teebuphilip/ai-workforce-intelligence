import { useState } from 'react';
import useConfig from '../hooks/useConfig';
import useAnalytics from '../hooks/useAnalytics';
import api from '../utils/api';

function Contact() {
  const config = useConfig();
  const analytics = useAnalytics();
  const { contact, branding } = config;
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: ''
  });
  const [status, setStatus] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus('sending');
    
    analytics.trackEvent('contact_form_submit', { subject: formData.subject });
    
    try {
      await api.post('/contact', formData);
      setStatus('success');
      setFormData({ name: '', email: '', subject: '', message: '' });
    } catch (error) {
      setStatus('error');
    }
  };

  return (
    <div className="min-h-screen py-20 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4">{contact.headline}</h1>
          <p className="text-xl text-gray-600">{contact.subheadline}</p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 mb-12">
          {contact.methods.map((method, i) => (
            <div key={i} className="bg-white rounded-lg shadow p-6">
              <h3 className="text-xl font-semibold mb-2">{method.label}</h3>
              <p className="text-gray-600 mb-2">{method.description}</p>
              {method.value && (
                <a 
                  href={`mailto:${method.value}`}
                  className="font-medium"
                  style={{ color: branding.primary_color }}
                >
                  {method.value}
                </a>
              )}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-lg shadow p-8">
          <h2 className="text-2xl font-semibold mb-6">{contact.form.title}</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {contact.form.fields.map((field, i) => (
              <div key={i}>
                <label className="block text-sm font-medium mb-1">
                  {field.label} {field.required && <span className="text-red-600">*</span>}
                </label>
                {field.type === 'textarea' ? (
                  <textarea
                    value={formData[field.name]}
                    onChange={(e) => setFormData({...formData, [field.name]: e.target.value})}
                    required={field.required}
                    rows={5}
                    className="w-full px-4 py-2 border rounded-lg"
                  />
                ) : field.type === 'select' ? (
                  <select
                    value={formData[field.name]}
                    onChange={(e) => setFormData({...formData, [field.name]: e.target.value})}
                    required={field.required}
                    className="w-full px-4 py-2 border rounded-lg"
                  >
                    <option value="">Select...</option>
                    {field.options.map((opt, j) => (
                      <option key={j} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={field.type}
                    value={formData[field.name]}
                    onChange={(e) => setFormData({...formData, [field.name]: e.target.value})}
                    required={field.required}
                    className="w-full px-4 py-2 border rounded-lg"
                  />
                )}
              </div>
            ))}
            
            <button
              type="submit"
              disabled={status === 'sending'}
              className="w-full py-3 rounded-lg text-white"
              style={{ backgroundColor: branding.primary_color }}
            >
              {status === 'sending' ? 'Sending...' : contact.form.submit_text}
            </button>
            
            {status === 'success' && (
              <p className="text-green-600 text-center">{contact.form.success_message}</p>
            )}
            {status === 'error' && (
              <p className="text-red-600 text-center">Failed to send. Please try again.</p>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}

export default Contact;
