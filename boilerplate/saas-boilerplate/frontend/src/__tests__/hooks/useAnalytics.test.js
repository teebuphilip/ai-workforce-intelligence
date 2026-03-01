/**
 * Frontend Boilerplate Tests - useAnalytics Hook
 */

import { renderHook } from '@testing-library/react';
import useAnalytics from '../../hooks/useAnalytics';
import api from '../../utils/api';

// Mock API
jest.mock('../../utils/api');

// Mock Auth0
jest.mock('@auth0/auth0-react', () => ({
  useAuth0: () => ({
    user: { sub: 'auth0|123', name: 'Test User' }
  })
}));

describe('useAnalytics Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    api.post = jest.fn().mockResolvedValue({ data: { success: true } });
  });
  
  test('trackEvent sends correct data', async () => {
    const { result } = renderHook(() => useAnalytics());
    
    await result.current.trackEvent('button_clicked', { button: 'save' });
    
    expect(api.post).toHaveBeenCalledWith('/analytics/track', {
      event_name: 'button_clicked',
      user_id: 'auth0|123',
      event_params: { button: 'save' }
    });
  });
  
  test('trackEvent handles errors gracefully', async () => {
    api.post = jest.fn().mockRejectedValue(new Error('Network error'));
    
    const { result } = renderHook(() => useAnalytics());
    
    // Should not throw
    await expect(
      result.current.trackEvent('test_event')
    ).resolves.not.toThrow();
  });
  
  test('trackPageView sends correct data', async () => {
    const { result } = renderHook(() => useAnalytics());
    
    await result.current.trackPageView('/home', 'Home Page');
    
    expect(api.post).toHaveBeenCalledWith('/analytics/page-view', {
      page_path: '/home',
      page_title: 'Home Page',
      user_id: 'auth0|123'
    });
  });
  
  test('works without user (not authenticated)', async () => {
    require('@auth0/auth0-react').useAuth0 = () => ({
      user: null
    });
    
    const { result } = renderHook(() => useAnalytics());
    
    await result.current.trackEvent('test_event');
    
    expect(api.post).toHaveBeenCalledWith('/analytics/track', {
      event_name: 'test_event',
      user_id: undefined,
      event_params: {}
    });
  });
});
