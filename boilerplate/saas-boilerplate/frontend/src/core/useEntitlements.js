/**
 * useEntitlements.js - React Hook for Entitlement Checks
 *
 * WHY: Gives every component easy access to what the user can do.
 * Single fetch on mount, cached in state, no prop drilling needed.
 *
 * USAGE:
 *   const { entitlements, can, loading } = useEntitlements();
 *   if (can("ai_sorting")) { ... }
 */

import { useState, useEffect, useCallback } from 'react';
import api from '../utils/api';  // Axios instance with auth header

/**
 * Hook that fetches and exposes the current user's entitlements.
 *
 * Returns:
 *   entitlements  - string[]  - list of entitlement keys
 *   can(feature)  - boolean   - check if user has a feature
 *   canAny(...fs) - boolean   - check if user has ANY of the features
 *   loading       - boolean   - true while fetching
 *   error         - string    - error message if fetch failed
 *   refresh()     - function  - manually re-fetch (e.g. after upgrade)
 */
export function useEntitlements() {
  const [entitlements, setEntitlements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchEntitlements = useCallback(async () => {
    // WHY try/catch here: Network errors shouldn't crash the whole UI.
    // Fail safe: empty entitlements = no access (correct behavior).
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/entitlements/');
      setEntitlements(response.data.entitlements || []);
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Failed to load entitlements';
      setError(message);
      setEntitlements([]);  // Fail closed - no access on error
      console.error('useEntitlements fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEntitlements();
  }, [fetchEntitlements]);

  /**
   * Check if user has a specific entitlement.
   * WHY memoized inline: Avoids re-render on every check call.
   */
  const can = useCallback(
    (feature) => entitlements.includes(feature),
    [entitlements]
  );

  /**
   * Check if user has ANY of the listed entitlements.
   * WHY: Some features are accessible on multiple plans.
   * Example: canAny("analytics_basic", "analytics_pro")
   */
  const canAny = useCallback(
    (...features) => features.some(f => entitlements.includes(f)),
    [entitlements]
  );

  return {
    entitlements,
    can,
    canAny,
    loading,
    error,
    refresh: fetchEntitlements,
  };
}

/**
 * Simpler hook for checking a single feature.
 * WHY: Less boilerplate when you only need one check.
 *
 * USAGE:
 *   const allowed = useCanAccess("ai_sorting");
 *   if (allowed === null) return <Spinner />;  // still loading
 *   if (!allowed) return <UpgradePrompt />;
 */
export function useCanAccess(feature) {
  const { can, loading } = useEntitlements();
  if (loading) return null;   // null = still loading
  return can(feature);
}
