import { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';

function ConsentGate({ children }) {
  const { getAccessTokenSilently } = useAuth0();
  const [consentStatus, setConsentStatus] = useState(null); // null = loading
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    checkConsentStatus();
  }, []);

  async function checkConsentStatus() {
    try {
      const token = await getAccessTokenSilently();
      const res = await fetch('/api/legal/consent/status', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to check consent status');
      setConsentStatus(await res.json());
    } catch {
      // Fail open — never block users on network error
      setConsentStatus({ requires_reacceptance: false });
    }
  }

  async function acceptConsent() {
    setAccepting(true);
    setError(null);
    try {
      const token = await getAccessTokenSilently();
      for (const docType of ['terms', 'privacy']) {
        const typeStatus = consentStatus[docType];
        if (!typeStatus.is_current && typeStatus.current_version) {
          const res = await fetch('/api/legal/consent', {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              doc_type: docType,
              version: typeStatus.current_version,
            }),
          });
          if (!res.ok) throw new Error('Failed to record consent');
        }
      }
      await checkConsentStatus();
    } catch {
      setError('Failed to record consent. Please try again.');
    } finally {
      setAccepting(false);
    }
  }

  // Loading state — same spinner as ProtectedRoute
  if (consentStatus === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Consent up to date — transparent passthrough, no UX impact
  if (!consentStatus.requires_reacceptance) {
    return children;
  }

  // Build list of pending documents
  const pendingDocs = [];
  if (consentStatus.terms && !consentStatus.terms.is_current) pendingDocs.push('Terms of Service');
  if (consentStatus.privacy && !consentStatus.privacy.is_current) pendingDocs.push('Privacy Policy');

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white rounded-xl shadow-md p-8 max-w-md w-full">
        <h2 className="text-xl font-semibold mb-3">Updated Legal Documents</h2>
        <p className="text-gray-600 mb-4">
          We've updated our {pendingDocs.join(' and ')}. Please review and accept to continue.
        </p>

        <ul className="mb-6 space-y-2">
          {consentStatus.terms && !consentStatus.terms.is_current && (
            <li>
              <a
                href="/terms"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline"
              >
                Terms of Service
              </a>
              {consentStatus.terms.current_version && (
                <span className="text-gray-400 text-sm ml-2">
                  v{consentStatus.terms.current_version}
                </span>
              )}
            </li>
          )}
          {consentStatus.privacy && !consentStatus.privacy.is_current && (
            <li>
              <a
                href="/privacy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline"
              >
                Privacy Policy
              </a>
              {consentStatus.privacy.current_version && (
                <span className="text-gray-400 text-sm ml-2">
                  v{consentStatus.privacy.current_version}
                </span>
              )}
            </li>
          )}
        </ul>

        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

        <button
          onClick={acceptConsent}
          disabled={accepting}
          className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold
                     hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {accepting ? 'Saving...' : `I Accept the ${pendingDocs.join(' and ')}`}
        </button>
      </div>
    </div>
  );
}

export default ConsentGate;
