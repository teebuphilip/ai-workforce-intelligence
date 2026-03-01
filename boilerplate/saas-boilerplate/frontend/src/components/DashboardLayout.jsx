/**
 * DashboardLayout — shared inner-page wrapper for all business pages.
 *
 * Provides:
 *  - Consistent background (gray-50)
 *  - Max-width container (max-w-7xl)
 *  - Optional page title + subtitle using brand primary color
 *  - Optional action button slot (top-right of header)
 *
 * Usage in a business page:
 *   import DashboardLayout from '../platform';
 *
 *   export default function MyFeature() {
 *     return (
 *       <DashboardLayout title="My Feature" subtitle="Manage your items here">
 *         <div className="bg-white rounded-lg shadow p-6">
 *           ...your content...
 *         </div>
 *       </DashboardLayout>
 *     );
 *   }
 */

import useConfig from '../hooks/useConfig';

const BRAND_DEFAULTS = {
  primary_color: '#4F46E5',
  logo_url:      '',
  company_name:  '',
};

export default function DashboardLayout({ title, subtitle, action, children }) {
  const config = useConfig();
  const branding = { ...BRAND_DEFAULTS, ...(config.branding || {}) };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">

        {/* Page header */}
        {(title || action) && (
          <div className="mb-8 flex items-start justify-between">
            <div>
              {title && (
                <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
              )}
              {subtitle && (
                <p className="text-gray-500 mt-1">{subtitle}</p>
              )}
            </div>
            {action && (
              <div className="ml-4 flex-shrink-0">{action}</div>
            )}
          </div>
        )}

        {/* Page content */}
        {children}

      </div>
    </div>
  );
}

/**
 * Reusable card — consistent with Dashboard.jsx card styling.
 *
 * Usage:
 *   <DashboardLayout.Card title="Stats">...</DashboardLayout.Card>
 */
function Card({ title, children, className = '' }) {
  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      {title && (
        <h3 className="text-lg font-semibold mb-4 text-gray-900">{title}</h3>
      )}
      {children}
    </div>
  );
}

/**
 * Reusable stat tile — matches the 3-column stat row in Dashboard.jsx.
 *
 * Usage:
 *   <DashboardLayout.Stat label="Total Items" value={42} note="this month" />
 */
function Stat({ label, value, note }) {
  const config = useConfig();
  const branding = { ...BRAND_DEFAULTS, ...(config.branding || {}) };
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-2 text-gray-900">{label}</h3>
      <p className="text-3xl font-bold" style={{ color: branding.primary_color }}>
        {value}
      </p>
      {note && <p className="text-sm text-gray-500 mt-2">{note}</p>}
    </div>
  );
}

/**
 * Primary action button — matches brand primary color.
 *
 * Usage:
 *   <DashboardLayout.Button onClick={handleClick}>Save</DashboardLayout.Button>
 */
function Button({ children, onClick, disabled, variant = 'primary', className = '' }) {
  const config = useConfig();
  const branding = { ...BRAND_DEFAULTS, ...(config.branding || {}) };

  const base = 'px-4 py-2 rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed';

  if (variant === 'outline') {
    return (
      <button
        onClick={onClick}
        disabled={disabled}
        className={`${base} border-2 bg-white ${className}`}
        style={{ borderColor: branding.primary_color, color: branding.primary_color }}
      >
        {children}
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${base} text-white ${className}`}
      style={{ backgroundColor: branding.primary_color }}
    >
      {children}
    </button>
  );
}

/**
 * Empty state — shows when a list has no items.
 *
 * Usage:
 *   <DashboardLayout.Empty message="No items yet." cta="Create your first item" onCta={...} />
 */
function Empty({ message, cta, onCta }) {
  const config = useConfig();
  const branding = { ...BRAND_DEFAULTS, ...(config.branding || {}) };
  return (
    <div className="bg-white rounded-lg shadow p-12 text-center">
      <p className="text-gray-400 mb-4">{message || 'Nothing here yet.'}</p>
      {cta && onCta && (
        <button
          onClick={onCta}
          className="px-4 py-2 rounded-lg text-white font-semibold"
          style={{ backgroundColor: branding.primary_color }}
        >
          {cta}
        </button>
      )}
    </div>
  );
}

/**
 * Loading state — consistent with boilerplate loading patterns.
 *
 * Usage:
 *   if (loading) return <DashboardLayout.Loading />;
 */
function Loading({ message = 'Loading...' }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <p className="text-gray-400">{message}</p>
    </div>
  );
}

/**
 * Error state.
 *
 * Usage:
 *   if (error) return <DashboardLayout.Error message={error} />;
 */
function ErrorState({ message }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow p-8 max-w-md text-center">
        <p className="text-red-600 font-semibold mb-2">Something went wrong</p>
        <p className="text-gray-500 text-sm">{message}</p>
      </div>
    </div>
  );
}

// Attach sub-components
DashboardLayout.Card   = Card;
DashboardLayout.Stat   = Stat;
DashboardLayout.Button = Button;
DashboardLayout.Empty  = Empty;
DashboardLayout.Loading = Loading;
DashboardLayout.Error  = ErrorState;
