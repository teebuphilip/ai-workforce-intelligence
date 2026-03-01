/**
 * platform.js — single import for all shared platform UI utilities.
 *
 * Business pages import from here instead of using deep relative paths.
 *
 * Usage in any file under business/frontend/pages/:
 *
 *   import DashboardLayout, { useConfig, useAnalytics } from '../platform';
 *
 *   export default function MyPage() {
 *     const { branding } = useConfig();
 *     return (
 *       <DashboardLayout title="My Page">
 *         <DashboardLayout.Card title="Stats">
 *           <DashboardLayout.Stat label="Items" value={42} note="total" />
 *         </DashboardLayout.Card>
 *       </DashboardLayout>
 *     );
 *   }
 */

// Layout + sub-components
export { default } from '../../saas-boilerplate/frontend/src/components/DashboardLayout';
export { default as DashboardLayout } from '../../saas-boilerplate/frontend/src/components/DashboardLayout';

// Hooks
export { default as useConfig }    from '../../saas-boilerplate/frontend/src/hooks/useConfig';
export { default as useAnalytics } from '../../saas-boilerplate/frontend/src/hooks/useAnalytics';
