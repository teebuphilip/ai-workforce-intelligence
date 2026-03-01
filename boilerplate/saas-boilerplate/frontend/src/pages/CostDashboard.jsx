/**
 * CostDashboard.jsx - AI Cost Tracking Dashboard
 * ===============================================
 *
 * WHY: AI costs are the #1 variable expense. Without visibility,
 *      you can't answer: "Which tenant/feature is driving cost?"
 *      This dashboard shows cost per tenant, per feature, per day.
 *
 * DATA SOURCE: GET /api/admin/ai-costs?days=30
 *
 * Requires: admin role (require_admin dependency on backend route)
 *
 * Features:
 *   - Total cost summary (last 30 days)
 *   - Cost breakdown by tenant
 *   - Cost breakdown by feature
 *   - Cost trend over time (daily)
 *   - CSV export
 *   - Budget status per tenant (spent vs. limit)
 *
 * Usage:
 *   <Route path="/admin/costs" element={<CostDashboard />} />
 */

import React, { useState, useEffect, useCallback } from 'react';

// ============================================================
// TYPES & CONSTANTS
// ============================================================

const COLORS = {
  primary: '#2563eb',    // blue-600
  success: '#16a34a',    // green-600
  warning: '#d97706',    // amber-600
  danger: '#dc2626',     // red-600
  neutral: '#6b7280',    // gray-500
};

const MODEL_LABELS = {
  'claude-haiku-4-5-20251001': 'Haiku (cheap)',
  'claude-sonnet-4-6': 'Sonnet (smart)',
  'gpt-4o': 'GPT-4o (business)',
  'gpt-4o-mini': 'GPT-4o Mini',
};

// ============================================================
// MOCK DATA - replace with real API calls when backend is ready
// Format matches GET /api/admin/ai-costs response
// ============================================================

function generateMockData() {
  const tenants = ['courtdominion', 'autofounder-hub', 'founderops', 'test-tenant'];
  const features = ['game_summary', 'idea_intake', 'fo_build', 'qa_iteration', 'content_gen'];
  const models = ['claude-haiku-4-5-20251001', 'claude-sonnet-4-6', 'gpt-4o'];

  const rows = [];
  const today = new Date();

  for (let daysAgo = 29; daysAgo >= 0; daysAgo--) {
    const d = new Date(today);
    d.setDate(d.getDate() - daysAgo);
    const dateStr = d.toISOString().split('T')[0];

    tenants.forEach(tenant => {
      features.slice(0, 3).forEach(feature => {
        const model = models[Math.floor(Math.random() * models.length)];
        rows.push({
          tenant_id: tenant,
          feature,
          model,
          date: dateStr,
          total_cost_usd: parseFloat((Math.random() * 3 + 0.1).toFixed(4)),
          call_count: Math.floor(Math.random() * 50 + 5),
          total_tokens_in: Math.floor(Math.random() * 50000 + 1000),
          total_tokens_out: Math.floor(Math.random() * 20000 + 500),
        });
      });
    });
  }

  return { rows, total_cost_usd: rows.reduce((sum, r) => sum + r.total_cost_usd, 0) };
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function formatUSD(amount) {
  if (amount === undefined || amount === null) return '$0.00';
  return `$${Number(amount).toFixed(2)}`;
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function groupBy(rows, key) {
  return rows.reduce((acc, row) => {
    const k = row[key];
    if (!acc[k]) acc[k] = [];
    acc[k].push(row);
    return acc;
  }, {});
}

function sumCost(rows) {
  return rows.reduce((sum, r) => sum + (r.total_cost_usd || 0), 0);
}

// ============================================================
// SUB-COMPONENTS
// ============================================================

function StatCard({ label, value, subtext, color = 'primary' }) {
  return (
    <div style={{
      background: 'white',
      border: '1px solid #e5e7eb',
      borderRadius: 8,
      padding: '20px 24px',
      flex: 1,
      minWidth: 160,
    }}>
      <div style={{ color: '#6b7280', fontSize: 13, marginBottom: 6 }}>{label}</div>
      <div style={{ color: COLORS[color], fontSize: 28, fontWeight: 700 }}>{value}</div>
      {subtext && <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>{subtext}</div>}
    </div>
  );
}

function SimpleBar({ label, value, maxValue, color = '#2563eb', extra = '' }) {
  const pct = maxValue > 0 ? Math.min((value / maxValue) * 100, 100) : 0;
  const barColor = pct > 90 ? COLORS.danger : pct > 75 ? COLORS.warning : color;

  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 13, color: '#374151' }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: 600, color: barColor }}>
          {formatUSD(value)} {extra}
        </span>
      </div>
      <div style={{ background: '#f3f4f6', borderRadius: 4, height: 8 }}>
        <div style={{
          background: barColor,
          borderRadius: 4,
          height: 8,
          width: `${pct}%`,
          transition: 'width 0.3s ease',
        }} />
      </div>
    </div>
  );
}

function MiniLineChart({ data, width = 300, height = 80, color = '#2563eb' }) {
  if (!data || data.length < 2) {
    return <div style={{ color: '#9ca3af', fontSize: 12 }}>Not enough data</div>;
  }

  const maxVal = Math.max(...data.map(d => d.value));
  const minVal = Math.min(...data.map(d => d.value));
  const range = maxVal - minVal || 1;

  const padding = 10;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;
  const stepX = chartWidth / (data.length - 1);

  const points = data.map((d, i) => {
    const x = padding + i * stepX;
    const y = padding + chartHeight - ((d.value - minVal) / range) * chartHeight;
    return `${x},${y}`;
  }).join(' ');

  const area = `M${padding},${height - padding} ` +
    data.map((d, i) => {
      const x = padding + i * stepX;
      const y = padding + chartHeight - ((d.value - minVal) / range) * chartHeight;
      return `L${x},${y}`;
    }).join(' ') +
    ` L${padding + chartWidth},${height - padding} Z`;

  return (
    <svg width={width} height={height} style={{ overflow: 'visible' }}>
      {/* Area fill */}
      <path d={area} fill={color} fillOpacity={0.1} />
      {/* Line */}
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Dots */}
      {data.map((d, i) => {
        const x = padding + i * stepX;
        const y = padding + chartHeight - ((d.value - minVal) / range) * chartHeight;
        return (
          <circle key={i} cx={x} cy={y} r={3} fill={color} />
        );
      })}
    </svg>
  );
}

function BudgetBadge({ spent, budget }) {
  if (!budget || budget === 0) return <span style={{ color: '#9ca3af', fontSize: 11 }}>Unlimited</span>;
  const pct = spent / budget;
  const color = pct >= 1 ? COLORS.danger : pct >= 0.9 ? COLORS.warning : COLORS.success;
  return (
    <span style={{
      background: `${color}15`,
      color,
      border: `1px solid ${color}40`,
      borderRadius: 12,
      padding: '2px 8px',
      fontSize: 11,
      fontWeight: 600,
    }}>
      {(pct * 100).toFixed(0)}% of ${budget}
    </span>
  );
}

// ============================================================
// EXPORT TO CSV
// ============================================================

function exportCSV(rows) {
  const headers = ['Date', 'Tenant', 'Feature', 'Model', 'Cost ($)', 'Calls', 'Tokens In', 'Tokens Out'];
  const csvRows = [
    headers.join(','),
    ...rows.map(r => [
      r.date, r.tenant_id, r.feature, r.model,
      r.total_cost_usd.toFixed(4), r.call_count,
      r.total_tokens_in, r.total_tokens_out
    ].join(','))
  ];
  const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ai-costs-${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ============================================================
// MAIN DASHBOARD COMPONENT
// ============================================================

export default function CostDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [selectedTenant, setSelectedTenant] = useState('all');
  const [activeTab, setActiveTab] = useState('overview'); // overview | tenant | feature | daily

  // Load data (replace with real API call)
  useEffect(() => {
    setLoading(true);
    // Real implementation:
    // fetch(`/api/admin/ai-costs?days=${days}${selectedTenant !== 'all' ? `&tenant_id=${selectedTenant}` : ''}`)
    //   .then(r => r.json())
    //   .then(d => { setData(d); setLoading(false); })
    //   .catch(e => { console.error(e); setLoading(false); });

    // Mock for now
    setTimeout(() => {
      setData(generateMockData());
      setLoading(false);
    }, 300);
  }, [days, selectedTenant]);

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>
        Loading AI cost data...
      </div>
    );
  }

  if (!data) return <div style={{ padding: 40, color: COLORS.danger }}>Failed to load data.</div>;

  const allRows = data.rows || [];
  const filteredRows = selectedTenant === 'all'
    ? allRows
    : allRows.filter(r => r.tenant_id === selectedTenant);

  const totalCost = sumCost(filteredRows);
  const totalCalls = filteredRows.reduce((sum, r) => sum + (r.call_count || 0), 0);

  // Group data for charts
  const byTenant = groupBy(filteredRows, 'tenant_id');
  const byFeature = groupBy(filteredRows, 'feature');
  const byModel = groupBy(filteredRows, 'model');
  const byDate = groupBy(filteredRows, 'date');

  const tenants = Object.keys(byTenant).sort();
  const maxTenantCost = Math.max(...tenants.map(t => sumCost(byTenant[t])));

  const features = Object.keys(byFeature).sort((a, b) => sumCost(byFeature[b]) - sumCost(byFeature[a]));
  const maxFeatureCost = Math.max(...features.map(f => sumCost(byFeature[f])));

  // Daily trend data
  const dates = Object.keys(byDate).sort();
  const dailyData = dates.map(d => ({ date: d, value: sumCost(byDate[d]) }));

  // Estimate this month vs last month
  const thisMonthCost = filteredRows
    .filter(r => r.date >= new Date().toISOString().slice(0, 7))
    .reduce((sum, r) => sum + r.total_cost_usd, 0);

  // Mock budgets (real: from tenant records)
  const TENANT_BUDGETS = { 'courtdominion': 100, 'autofounder-hub': 150, 'founderops': 200, 'test-tenant': 50 };

  const tabStyle = (tab) => ({
    padding: '8px 16px',
    background: activeTab === tab ? '#2563eb' : 'transparent',
    color: activeTab === tab ? 'white' : '#6b7280',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: activeTab === tab ? 600 : 400,
  });

  return (
    <div style={{
      fontFamily: 'system-ui, -apple-system, sans-serif',
      background: '#f9fafb',
      minHeight: '100vh',
      padding: 24,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111827' }}>
            AI Cost Dashboard
          </h1>
          <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 14 }}>
            Track AI spending across all tenants and features
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          {/* Days filter */}
          <select
            value={days}
            onChange={e => setDays(Number(e.target.value))}
            style={{
              border: '1px solid #d1d5db', borderRadius: 6, padding: '6px 12px',
              fontSize: 14, background: 'white', cursor: 'pointer',
            }}
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>

          {/* Tenant filter */}
          <select
            value={selectedTenant}
            onChange={e => setSelectedTenant(e.target.value)}
            style={{
              border: '1px solid #d1d5db', borderRadius: 6, padding: '6px 12px',
              fontSize: 14, background: 'white', cursor: 'pointer',
            }}
          >
            <option value="all">All Tenants</option>
            {tenants.map(t => <option key={t} value={t}>{t}</option>)}
          </select>

          {/* Export */}
          <button
            onClick={() => exportCSV(filteredRows)}
            style={{
              background: '#111827', color: 'white', border: 'none',
              borderRadius: 6, padding: '8px 16px', fontSize: 14,
              cursor: 'pointer', fontWeight: 500,
            }}
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
        <StatCard
          label={`Total Cost (${days}d)`}
          value={formatUSD(totalCost)}
          subtext={`This month: ${formatUSD(thisMonthCost)}`}
          color={totalCost > 500 ? 'danger' : 'primary'}
        />
        <StatCard
          label="Total API Calls"
          value={totalCalls.toLocaleString()}
          subtext={`Avg ${(totalCost / Math.max(totalCalls, 1) * 1000).toFixed(2)}¢ per call`}
        />
        <StatCard
          label="Active Tenants"
          value={tenants.length}
          subtext="with AI spend this period"
        />
        <StatCard
          label="Avg Daily Cost"
          value={formatUSD(totalCost / Math.max(days, 1))}
          subtext={`Projected monthly: ${formatUSD(totalCost / Math.max(days, 1) * 30)}`}
        />
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, background: 'white', padding: 4, borderRadius: 8, border: '1px solid #e5e7eb', width: 'fit-content' }}>
        {[
          ['overview', 'Overview'],
          ['tenant', 'By Tenant'],
          ['feature', 'By Feature'],
          ['daily', 'Daily Trend'],
        ].map(([tab, label]) => (
          <button key={tab} style={tabStyle(tab)} onClick={() => setActiveTab(tab)}>
            {label}
          </button>
        ))}
      </div>

      {/* OVERVIEW TAB */}
      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {/* Cost by Tenant */}
          <div style={{ background: 'white', borderRadius: 8, border: '1px solid #e5e7eb', padding: 24 }}>
            <h3 style={{ margin: '0 0 20px', fontSize: 16, fontWeight: 600 }}>Cost by Tenant</h3>
            {tenants.map(t => (
              <SimpleBar
                key={t}
                label={t}
                value={sumCost(byTenant[t])}
                maxValue={maxTenantCost}
                extra={<BudgetBadge spent={sumCost(byTenant[t])} budget={TENANT_BUDGETS[t]} />}
              />
            ))}
          </div>

          {/* Cost by Feature */}
          <div style={{ background: 'white', borderRadius: 8, border: '1px solid #e5e7eb', padding: 24 }}>
            <h3 style={{ margin: '0 0 20px', fontSize: 16, fontWeight: 600 }}>Cost by Feature</h3>
            {features.map(f => (
              <SimpleBar
                key={f}
                label={f}
                value={sumCost(byFeature[f])}
                maxValue={maxFeatureCost}
                color="#7c3aed"
              />
            ))}
          </div>

          {/* Cost by Model */}
          <div style={{ background: 'white', borderRadius: 8, border: '1px solid #e5e7eb', padding: 24 }}>
            <h3 style={{ margin: '0 0 20px', fontSize: 16, fontWeight: 600 }}>Cost by Model</h3>
            {Object.keys(byModel).map(m => {
              const modelCost = sumCost(byModel[m]);
              return (
                <div key={m} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 500, color: '#111827' }}>
                      {MODEL_LABELS[m] || m}
                    </div>
                    <div style={{ fontSize: 11, color: '#9ca3af' }}>{m}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 600, color: '#111827' }}>{formatUSD(modelCost)}</div>
                    <div style={{ fontSize: 11, color: '#9ca3af' }}>
                      {((modelCost / totalCost) * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* 30-day Trend */}
          <div style={{ background: 'white', borderRadius: 8, border: '1px solid #e5e7eb', padding: 24 }}>
            <h3 style={{ margin: '0 0 20px', fontSize: 16, fontWeight: 600 }}>Daily Cost Trend</h3>
            <MiniLineChart data={dailyData.slice(-14)} width={340} height={100} />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
              <span style={{ fontSize: 11, color: '#9ca3af' }}>{formatDate(dates[Math.max(0, dates.length - 14)])}</span>
              <span style={{ fontSize: 11, color: '#9ca3af' }}>{formatDate(dates[dates.length - 1])}</span>
            </div>
          </div>
        </div>
      )}

      {/* TENANT TAB */}
      {activeTab === 'tenant' && (
        <div style={{ background: 'white', borderRadius: 8, border: '1px solid #e5e7eb', padding: 24 }}>
          <h3 style={{ margin: '0 0 20px', fontSize: 16, fontWeight: 600 }}>Tenant Cost Details</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #f3f4f6' }}>
                {['Tenant', 'Total Cost', 'API Calls', 'Budget', 'Budget %', 'Top Feature'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '8px 12px', fontSize: 12, color: '#6b7280', fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tenants.sort((a, b) => sumCost(byTenant[b]) - sumCost(byTenant[a])).map((tenant, i) => {
                const tenantRows = byTenant[tenant];
                const tenantCost = sumCost(tenantRows);
                const tenantCalls = tenantRows.reduce((s, r) => s + r.call_count, 0);
                const budget = TENANT_BUDGETS[tenant] || 100;
                const budgetPct = (tenantCost / budget * 100).toFixed(0);
                const topFeatureRows = groupBy(tenantRows, 'feature');
                const topFeature = Object.keys(topFeatureRows).sort((a, b) => sumCost(topFeatureRows[b]) - sumCost(topFeatureRows[a]))[0];

                return (
                  <tr key={tenant} style={{ borderBottom: '1px solid #f9fafb', background: i % 2 === 0 ? 'white' : '#fafafa' }}>
                    <td style={{ padding: '12px', fontWeight: 600, fontSize: 14 }}>{tenant}</td>
                    <td style={{ padding: '12px', fontWeight: 700, color: tenantCost > budget * 0.9 ? COLORS.danger : '#111827' }}>
                      {formatUSD(tenantCost)}
                    </td>
                    <td style={{ padding: '12px', color: '#374151' }}>{tenantCalls.toLocaleString()}</td>
                    <td style={{ padding: '12px', color: '#374151' }}>${budget}</td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        color: Number(budgetPct) >= 100 ? COLORS.danger : Number(budgetPct) >= 90 ? COLORS.warning : COLORS.success,
                        fontWeight: 600,
                      }}>
                        {budgetPct}%
                      </span>
                    </td>
                    <td style={{ padding: '12px', color: '#6b7280', fontSize: 13 }}>{topFeature}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* FEATURE TAB */}
      {activeTab === 'feature' && (
        <div style={{ background: 'white', borderRadius: 8, border: '1px solid #e5e7eb', padding: 24 }}>
          <h3 style={{ margin: '0 0 20px', fontSize: 16, fontWeight: 600 }}>Feature Cost Breakdown</h3>
          {features.map(feature => {
            const featureRows = byFeature[feature];
            const featureCost = sumCost(featureRows);
            const featureCalls = featureRows.reduce((s, r) => s + r.call_count, 0);
            const avgCostPerCall = featureCost / Math.max(featureCalls, 1);
            const byTenantInFeature = groupBy(featureRows, 'tenant_id');

            return (
              <div key={feature} style={{ marginBottom: 24, paddingBottom: 24, borderBottom: '1px solid #f3f4f6' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 16 }}>{feature}</span>
                    <span style={{ color: '#9ca3af', fontSize: 12, marginLeft: 12 }}>
                      {featureCalls} calls · {(avgCostPerCall * 100).toFixed(3)}¢/call avg
                    </span>
                  </div>
                  <span style={{ fontWeight: 700, fontSize: 20, color: '#111827' }}>{formatUSD(featureCost)}</span>
                </div>
                {/* Cost by tenant for this feature */}
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  {Object.entries(byTenantInFeature).map(([t, rows]) => (
                    <div key={t} style={{
                      background: '#f9fafb', border: '1px solid #e5e7eb',
                      borderRadius: 6, padding: '8px 14px', fontSize: 13,
                    }}>
                      <span style={{ color: '#6b7280' }}>{t}: </span>
                      <span style={{ fontWeight: 600 }}>{formatUSD(sumCost(rows))}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* DAILY TAB */}
      {activeTab === 'daily' && (
        <div style={{ background: 'white', borderRadius: 8, border: '1px solid #e5e7eb', padding: 24 }}>
          <h3 style={{ margin: '0 0 20px', fontSize: 16, fontWeight: 600 }}>Daily Cost Detail</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #f3f4f6' }}>
                {['Date', 'Total Cost', 'API Calls', 'Top Tenant', 'Top Feature'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '8px 12px', fontSize: 12, color: '#6b7280', fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dates.slice().reverse().map((date, i) => {
                const dayRows = byDate[date];
                const dayCost = sumCost(dayRows);
                const dayCalls = dayRows.reduce((s, r) => s + r.call_count, 0);
                const dayByTenant = groupBy(dayRows, 'tenant_id');
                const topTenant = Object.keys(dayByTenant).sort((a, b) => sumCost(dayByTenant[b]) - sumCost(dayByTenant[a]))[0];
                const dayByFeature = groupBy(dayRows, 'feature');
                const topFeature = Object.keys(dayByFeature).sort((a, b) => sumCost(dayByFeature[b]) - sumCost(dayByFeature[a]))[0];

                return (
                  <tr key={date} style={{ borderBottom: '1px solid #f9fafb', background: i % 2 === 0 ? 'white' : '#fafafa' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 500 }}>{formatDate(date)}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 700, color: dayCost > 50 ? COLORS.warning : '#111827' }}>
                      {formatUSD(dayCost)}
                    </td>
                    <td style={{ padding: '10px 12px', color: '#374151' }}>{dayCalls}</td>
                    <td style={{ padding: '10px 12px', color: '#6b7280', fontSize: 13 }}>{topTenant}</td>
                    <td style={{ padding: '10px 12px', color: '#6b7280', fontSize: 13 }}>{topFeature}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
