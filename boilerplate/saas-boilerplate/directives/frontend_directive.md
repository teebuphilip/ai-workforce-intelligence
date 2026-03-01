# Frontend Directive - For Claude Code / FounderOps

**Instructions for building frontend business pages**

---

## ⚡ CRITICAL: Auto-Loader - No Integration Required

**THE BOILERPLATE AUTOMATICALLY LOADS YOUR PAGES. DO NOT EDIT APP.JS.**

### What You Do
1. Create file in `business/frontend/pages/`
2. Export default component
3. Done - it auto-loads

### What You DON'T Do
❌ Import your component in App.js
❌ Add <Route> definition
❌ Edit App.js at all
❌ Configure routing manually

**Files in business/frontend/pages/*.jsx automatically become /dashboard/{kebab-case} routes.**

---

## Location

**ALL frontend pages go in:** `business/frontend/pages/`

---

## File Structure

```jsx
// business/frontend/pages/YourPage.jsx

import { useState, useEffect } from 'react';
import { useAuth } from 'saas-boilerplate/core/hooks';
import { Navbar, Footer } from 'saas-boilerplate/core/components';
import api from 'saas-boilerplate/utils/api';

export default function YourPage() {
  const { user } = useAuth();
  const [data, setData] = useState([]);
  
  useEffect(() => {
    // Load data from your custom API
    api.get('/your-feature').then(r => setData(r.data));
  }, []);
  
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="max-w-7xl mx-auto py-8 px-4">
        <h1 className="text-3xl font-bold mb-6">Your Page</h1>
        {/* Your custom content */}
      </main>
      <Footer />
    </div>
  );
}
```

**Result:** 
- Page auto-available at `/dashboard/your-page`
- No import needed
- No route definition needed
- Just start the dev server

---

## Available Shared Components

### 1. Layout Components

```jsx
import { Navbar, Footer } from 'saas-boilerplate/core/components';

export default function YourPage() {
  return (
    <>
      <Navbar />
      <main>Your content</main>
      <Footer />
    </>
  );
}
```

### 2. Authentication Hook

```jsx
import { useAuth } from 'saas-boilerplate/core/hooks';

export default function YourPage() {
  const { user, isLoading, logout } = useAuth();
  
  if (isLoading) return <div>Loading...</div>;
  
  return <div>Welcome {user?.name}</div>;
}
```

### 3. Analytics Hook

```jsx
import { useAnalytics } from 'saas-boilerplate/core/hooks';
import { useEffect } from 'react';

export default function YourPage() {
  const analytics = useAnalytics();
  
  useEffect(() => {
    analytics.trackPageView('/your-page', 'Your Page Title');
  }, []);
  
  const handleAction = () => {
    analytics.trackEvent('button_clicked', { button: 'submit' });
  };
  
  return <button onClick={handleAction}>Submit</button>;
}
```

### 4. Config Hook

```jsx
import { useConfig } from 'saas-boilerplate/core/hooks';

export default function YourPage() {
  const config = useConfig();
  
  return (
    <h1 style={{ color: config.branding.primary_color }}>
      Welcome to {config.business.name}
    </h1>
  );
}
```

### 5. API Client

```jsx
import api from 'saas-boilerplate/utils/api';

export default function YourPage() {
  const handleSubmit = async (data) => {
    try {
      const response = await api.post('/your-endpoint', data);
      alert('Success!');
    } catch (error) {
      alert('Error: ' + error.message);
    }
  };
  
  return <form onSubmit={handleSubmit}>...</form>;
}
```

---

## Common Patterns

### Pattern 1: Data Table

```jsx
import { useState, useEffect } from 'react';
import api from 'saas-boilerplate/utils/api';
import { Navbar, Footer } from 'saas-boilerplate/core/components';

export default function ItemsList() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    api.get('/items')
      .then(r => setItems(r.data))
      .finally(() => setLoading(false));
  }, []);
  
  if (loading) return <div>Loading...</div>;
  
  return (
    <>
      <Navbar />
      <div className="max-w-7xl mx-auto py-8 px-4">
        <h1 className="text-3xl font-bold mb-6">Items</h1>
        <table className="w-full">
          <thead>
            <tr>
              <th className="text-left py-2">Name</th>
              <th className="text-left py-2">Value</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id} className="border-t">
                <td className="py-2">{item.name}</td>
                <td className="py-2">{item.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Footer />
    </>
  );
}
```

### Pattern 2: Form

```jsx
import { useState } from 'react';
import api from 'saas-boilerplate/utils/api';
import { useConfig } from 'saas-boilerplate/core/hooks';

export default function CreateItem() {
  const config = useConfig();
  const [formData, setFormData] = useState({ name: '', value: 0 });
  const [status, setStatus] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus('submitting');
    
    try {
      await api.post('/items', formData);
      setStatus('success');
      setFormData({ name: '', value: 0 });
    } catch (error) {
      setStatus('error');
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="max-w-md mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">Create Item</h2>
      
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Name</label>
        <input
          type="text"
          value={formData.name}
          onChange={e => setFormData({...formData, name: e.target.value})}
          className="w-full px-4 py-2 border rounded-lg"
          required
        />
      </div>
      
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Value</label>
        <input
          type="number"
          value={formData.value}
          onChange={e => setFormData({...formData, value: parseInt(e.target.value)})}
          className="w-full px-4 py-2 border rounded-lg"
          required
        />
      </div>
      
      <button
        type="submit"
        disabled={status === 'submitting'}
        className="w-full py-3 rounded-lg text-white"
        style={{ backgroundColor: config.branding.primary_color }}
      >
        {status === 'submitting' ? 'Saving...' : 'Create Item'}
      </button>
      
      {status === 'success' && (
        <p className="text-green-600 mt-4">Item created successfully!</p>
      )}
      {status === 'error' && (
        <p className="text-red-600 mt-4">Error creating item</p>
      )}
    </form>
  );
}
```

### Pattern 3: Dashboard with Stats

```jsx
import { useState, useEffect } from 'react';
import { useAuth, useConfig } from 'saas-boilerplate/core/hooks';
import api from 'saas-boilerplate/utils/api';

export default function Dashboard() {
  const { user } = useAuth();
  const config = useConfig();
  const [stats, setStats] = useState({ total: 0, active: 0, pending: 0 });
  
  useEffect(() => {
    api.get('/stats').then(r => setStats(r.data));
  }, []);
  
  return (
    <div className="max-w-7xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-8">
        Welcome back, {user?.name}!
      </h1>
      
      <div className="grid md:grid-cols-3 gap-6">
        <StatCard
          title="Total Items"
          value={stats.total}
          color={config.branding.primary_color}
        />
        <StatCard
          title="Active"
          value={stats.active}
          color={config.branding.secondary_color}
        />
        <StatCard
          title="Pending"
          value={stats.pending}
          color={config.branding.accent_color}
        />
      </div>
    </div>
  );
}

function StatCard({ title, value, color }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-4xl font-bold" style={{ color }}>
        {value}
      </p>
    </div>
  );
}
```

### Pattern 4: Modal Dialog

```jsx
import { useState } from 'react';

export default function YourPage() {
  const [showModal, setShowModal] = useState(false);
  
  return (
    <>
      <button onClick={() => setShowModal(true)}>
        Open Modal
      </button>
      
      {showModal && (
        <Modal onClose={() => setShowModal(false)}>
          <h2>Modal Title</h2>
          <p>Modal content</p>
        </Modal>
      )}
    </>
  );
}

function Modal({ children, onClose }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        {children}
        <button
          onClick={onClose}
          className="mt-4 w-full py-2 bg-gray-200 rounded-lg"
        >
          Close
        </button>
      </div>
    </div>
  );
}
```

### Pattern 5: Tabs

```jsx
import { useState } from 'react';

export default function TabbedPage() {
  const [activeTab, setActiveTab] = useState('overview');
  
  return (
    <div className="max-w-7xl mx-auto py-8 px-4">
      <div className="border-b mb-6">
        <nav className="flex space-x-8">
          <Tab active={activeTab === 'overview'} onClick={() => setActiveTab('overview')}>
            Overview
          </Tab>
          <Tab active={activeTab === 'details'} onClick={() => setActiveTab('details')}>
            Details
          </Tab>
          <Tab active={activeTab === 'settings'} onClick={() => setActiveTab('settings')}>
            Settings
          </Tab>
        </nav>
      </div>
      
      {activeTab === 'overview' && <OverviewTab />}
      {activeTab === 'details' && <DetailsTab />}
      {activeTab === 'settings' && <SettingsTab />}
    </div>
  );
}

function Tab({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`py-4 px-1 border-b-2 font-medium ${
        active 
          ? 'border-blue-600 text-blue-600' 
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {children}
    </button>
  );
}
```

---

## Styling (Tailwind CSS)

### Available Classes:
```jsx
// Layout
<div className="container mx-auto">           // Center with max-width
<div className="flex items-center">           // Flexbox
<div className="grid grid-cols-3 gap-4">     // Grid

// Spacing
<div className="p-4">      // Padding all sides
<div className="py-8">     // Padding top/bottom
<div className="mb-6">     // Margin bottom

// Typography
<h1 className="text-3xl font-bold">          // Large bold heading
<p className="text-gray-600">                // Gray text

// Colors
<div className="bg-white">                   // White background
<div className="text-blue-600">              // Blue text
<div className="border-gray-200">            // Gray border

// Interactive
<button className="hover:bg-blue-700">       // Hover state
<input className="focus:ring-2">             // Focus ring
```

### Use Config Colors:
```jsx
const config = useConfig();

<div style={{ backgroundColor: config.branding.primary_color }}>
  Primary color element
</div>
```

---

## Example: InboxTamer Email Dashboard

```jsx
// business/frontend/pages/EmailDashboard.jsx

import { useState, useEffect } from 'react';
import { useAuth, useAnalytics } from 'saas-boilerplate/core/hooks';
import { Navbar, Footer } from 'saas-boilerplate/core/components';
import api from 'saas-boilerplate/utils/api';

export default function EmailDashboard() {
  const { user } = useAuth();
  const analytics = useAnalytics();
  const [emails, setEmails] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    analytics.trackPageView('/dashboard/email', 'Email Dashboard');
    loadEmails();
  }, [filter]);
  
  const loadEmails = async () => {
    setLoading(true);
    try {
      const response = await api.get('/inbox/emails', {
        params: { filter }
      });
      setEmails(response.data);
    } finally {
      setLoading(false);
    }
  };
  
  const handleArchive = async (emailId) => {
    await api.post(`/inbox/emails/${emailId}/archive`);
    analytics.trackEvent('email_archived', { email_id: emailId });
    loadEmails();
  };
  
  return (
    <>
      <Navbar />
      <div className="max-w-7xl mx-auto py-8 px-4">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Email Dashboard</h1>
          <button
            onClick={loadEmails}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg"
          >
            Refresh
          </button>
        </div>
        
        {/* Filters */}
        <div className="mb-6 flex space-x-4">
          <FilterButton
            active={filter === 'all'}
            onClick={() => setFilter('all')}
          >
            All
          </FilterButton>
          <FilterButton
            active={filter === 'important'}
            onClick={() => setFilter('important')}
          >
            Important
          </FilterButton>
          <FilterButton
            active={filter === 'unread'}
            onClick={() => setFilter('unread')}
          >
            Unread
          </FilterButton>
        </div>
        
        {/* Email List */}
        {loading ? (
          <div className="text-center py-12">Loading emails...</div>
        ) : emails.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No emails found
          </div>
        ) : (
          <div className="space-y-2">
            {emails.map(email => (
              <EmailCard
                key={email.id}
                email={email}
                onArchive={() => handleArchive(email.id)}
              />
            ))}
          </div>
        )}
      </div>
      <Footer />
    </>
  );
}

function FilterButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-lg ${
        active
          ? 'bg-blue-600 text-white'
          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
      }`}
    >
      {children}
    </button>
  );
}

function EmailCard({ email, onArchive }) {
  return (
    <div className="bg-white border rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center mb-2">
            <span className="font-semibold">{email.from}</span>
            {email.important && (
              <span className="ml-2 text-xs bg-red-100 text-red-600 px-2 py-1 rounded">
                Important
              </span>
            )}
          </div>
          <h3 className="font-medium mb-1">{email.subject}</h3>
          <p className="text-sm text-gray-600">{email.preview}</p>
        </div>
        <button
          onClick={onArchive}
          className="ml-4 text-gray-400 hover:text-gray-600"
        >
          Archive
        </button>
      </div>
    </div>
  );
}
```

---

## State Management

### Simple (useState):
```jsx
const [data, setData] = useState([]);
```

### Complex (useReducer):
```jsx
const [state, dispatch] = useReducer(reducer, initialState);

function reducer(state, action) {
  switch (action.type) {
    case 'ADD_ITEM':
      return { ...state, items: [...state.items, action.item] };
    case 'REMOVE_ITEM':
      return { ...state, items: state.items.filter(i => i.id !== action.id) };
    default:
      return state;
  }
}
```

---

## Error Handling

```jsx
const [error, setError] = useState(null);

useEffect(() => {
  api.get('/data')
    .then(r => setData(r.data))
    .catch(err => setError(err.message));
}, []);

if (error) {
  return (
    <div className="text-center py-12">
      <p className="text-red-600">Error: {error}</p>
      <button onClick={() => window.location.reload()}>
        Retry
      </button>
    </div>
  );
}
```

---

## Loading States

```jsx
if (loading) {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
    </div>
  );
}
```

---

## Responsive Design

```jsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* 1 column on mobile, 2 on tablet, 3 on desktop */}
</div>

<div className="hidden md:block">
  {/* Only show on desktop */}
</div>

<div className="block md:hidden">
  {/* Only show on mobile */}
</div>
```

---

## Testing Your Pages

### 1. Start Frontend:
```bash
cd saas-boilerplate/frontend
npm start
```

### 2. Visit Your Page:
```
http://localhost:3000/dashboard/your-page
```

### 3. Check Console:
- Open browser DevTools
- Look for errors
- Verify API calls

---

## Checklist

- [ ] Page file in `business/frontend/pages/`
- [ ] Uses Navbar and Footer
- [ ] Handles loading state
- [ ] Handles error state
- [ ] Responsive (mobile + desktop)
- [ ] Analytics tracked
- [ ] Uses config colors
- [ ] API calls work
- [ ] No console errors

---

## Ready to Build

1. Create file: `business/frontend/pages/YourPage.jsx`
2. Add component with layout
3. Connect to your backend API
4. Style with Tailwind
5. Test at http://localhost:3000

**The boilerplate handles routing and infrastructure.**
