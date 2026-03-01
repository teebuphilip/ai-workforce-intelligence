/**
 * EntitlementGate.jsx - Feature Gating Component
 *
 * WHY: Single component to wrap any feature that requires an entitlement.
 * Shows upgrade prompt automatically if user lacks access.
 * Hero configures which plan unlocks what - this component enforces it.
 *
 * USAGE:
 *
 *   // Basic gate - shows upgrade prompt if not entitled
 *   <EntitlementGate feature="ai_sorting">
 *     <AISortingPanel />
 *   </EntitlementGate>
 *
 *   // Custom fallback
 *   <EntitlementGate feature="bulk_actions" fallback={<div>Locked</div>}>
 *     <BulkActionsPanel />
 *   </EntitlementGate>
 *
 *   // Custom upgrade prompt text
 *   <EntitlementGate
 *     feature="analytics"
 *     planName="Pro"
 *     description="Unlock detailed analytics to track your performance."
 *   >
 *     <AnalyticsDashboard />
 *   </EntitlementGate>
 *
 *   // Gate on ANY of multiple features
 *   <EntitlementGate anyOf={["analytics_basic", "analytics_pro"]}>
 *     <Reports />
 *   </EntitlementGate>
 */

import { useEntitlements } from '../core/useEntitlements';

// ============================================================
// DEFAULT UPGRADE PROMPT
// WHY: Consistent upgrade UX across all gated features.
// Hero doesn't need to build this - it's automatic.
// ============================================================

function DefaultUpgradePrompt({ feature, planName, description }) {
  const displayName = feature
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');

  return (
    <div className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-gray-200 rounded-lg bg-gray-50 text-center">
      {/* Lock icon */}
      <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-4">
        <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
          />
        </svg>
      </div>

      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        {displayName}
        {planName && <span className="ml-2 text-sm font-normal text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">{planName}</span>}
      </h3>

      <p className="text-sm text-gray-500 mb-6 max-w-xs">
        {description || `Upgrade your plan to unlock ${displayName}.`}
      </p>

      <a
        href="/pricing"
        className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
      >
        View Plans
        <svg className="ml-2 w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </a>
    </div>
  );
}

// ============================================================
// LOADING SKELETON
// WHY: Prevents layout shift while entitlements load.
// ============================================================

function LoadingSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
      <div className="h-4 bg-gray-200 rounded w-1/2"></div>
    </div>
  );
}

// ============================================================
// MAIN GATE COMPONENT
// ============================================================

/**
 * EntitlementGate
 *
 * Props:
 *   feature     - string    - single entitlement key required
 *   anyOf       - string[]  - gate opens if user has ANY of these
 *   children    - ReactNode - content to show when entitled
 *   fallback    - ReactNode - custom fallback (overrides default upgrade prompt)
 *   planName    - string    - plan name shown in upgrade prompt e.g. "Pro"
 *   description - string    - custom description in upgrade prompt
 *   showLoading - boolean   - show skeleton while loading (default: true)
 */
export default function EntitlementGate({
  feature,
  anyOf,
  children,
  fallback,
  planName,
  description,
  showLoading = true,
}) {
  const { can, canAny, loading } = useEntitlements();

  // Show skeleton while loading
  if (loading && showLoading) {
    return <LoadingSkeleton />;
  }

  // Check entitlement
  const allowed = anyOf
    ? canAny(...anyOf)
    : can(feature);

  if (!allowed) {
    // Show custom fallback if provided, otherwise default upgrade prompt
    return fallback || (
      <DefaultUpgradePrompt
        feature={feature || anyOf?.[0] || 'feature'}
        planName={planName}
        description={description}
      />
    );
  }

  // User is entitled - render children
  return children;
}
