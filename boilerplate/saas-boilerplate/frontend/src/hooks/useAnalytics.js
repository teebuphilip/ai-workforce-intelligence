import { useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import api from '../utils/api';

function useAnalytics() {
  const { user } = useAuth0();

  const trackEvent = useCallback((eventName, eventParams = {}) => {
    api.post('/analytics/track', {
      event_name: eventName,
      user_id: user?.sub,
      event_params: eventParams
    }).catch(err => console.error('Analytics error:', err));
  }, [user]);

  const trackPageView = useCallback((pagePath, pageTitle) => {
    api.post('/analytics/page-view', {
      page_path: pagePath,
      page_title: pageTitle,
      user_id: user?.sub
    }).catch(err => console.error('Analytics error:', err));
  }, [user]);

  return { trackEvent, trackPageView };
}

export default useAnalytics;
