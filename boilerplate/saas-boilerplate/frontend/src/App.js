import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Auth0Provider } from '@auth0/auth0-react';
import { useEffect, Suspense } from 'react';
import { loadBusinessPages } from './core/loader';
import Home from './pages/Home';
import Pricing from './pages/Pricing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import AccountSettings from './pages/AccountSettings';
import Terms from './pages/Terms';
import Privacy from './pages/Privacy';
import FAQ from './pages/FAQ';
import Contact from './pages/Contact';
import AdminDashboard from './pages/AdminDashboard';
import AdminUsers from './pages/AdminUsers';
import AdminTenants from './pages/AdminTenants';
import AdminBilling from './pages/AdminBilling';
import AdminExpenses from './pages/AdminExpenses';
import Onboarding from './pages/Onboarding';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import ProtectedRoute from './components/ProtectedRoute';
import ConsentGate from './components/ConsentGate';
import config from './config/business_config.json';

// Load all business pages at startup — auto-mounted under /dashboard/*
const businessRoutes = loadBusinessPages();

function App() {
  // Load Google Analytics
  useEffect(() => {
    if (config.metadata?.analytics?.google_analytics_id) {
      const script = document.createElement('script');
      script.src = `https://www.googletagmanager.com/gtag/js?id=${config.metadata.analytics.google_analytics_id}`;
      script.async = true;
      document.head.appendChild(script);

      window.dataLayer = window.dataLayer || [];
      function gtag(){window.dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', config.metadata.analytics.google_analytics_id);
    }
  }, []);

  return (
    <Auth0Provider
      domain={process.env.REACT_APP_AUTH0_DOMAIN}
      clientId={process.env.REACT_APP_AUTH0_CLIENT_ID}
      authorizationParams={{
        redirect_uri: window.location.origin
      }}
    >
      <BrowserRouter>
        <div className="flex flex-col min-h-screen">
          <Navbar />
          <main className="flex-grow">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/faq" element={<FAQ />} />
              <Route path="/contact" element={<Contact />} />
              <Route path="/terms" element={<Terms />} />
              <Route path="/privacy" element={<Privacy />} />
              <Route path="/onboarding" element={
                <ProtectedRoute><ConsentGate><Onboarding /></ConsentGate></ProtectedRoute>
              } />
              <Route path="/dashboard" element={
                <ProtectedRoute><ConsentGate><Dashboard /></ConsentGate></ProtectedRoute>
              } />
              <Route path="/settings" element={
                <ProtectedRoute><ConsentGate><AccountSettings /></ConsentGate></ProtectedRoute>
              } />
              <Route path="/admin" element={
                <ProtectedRoute><ConsentGate><AdminDashboard /></ConsentGate></ProtectedRoute>
              } />
              <Route path="/admin/users" element={
                <ProtectedRoute><ConsentGate><AdminUsers /></ConsentGate></ProtectedRoute>
              } />
              <Route path="/admin/tenants" element={
                <ProtectedRoute><ConsentGate><AdminTenants /></ConsentGate></ProtectedRoute>
              } />
              <Route path="/admin/billing" element={
                <ProtectedRoute><ConsentGate><AdminBilling /></ConsentGate></ProtectedRoute>
              } />
              <Route path="/admin/expenses" element={
                <ProtectedRoute><ConsentGate><AdminExpenses /></ConsentGate></ProtectedRoute>
              } />

              {/* ── Auto-loaded business pages (/dashboard/<page-name>) ── */}
              <Suspense fallback={
                <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                  <p className="text-gray-400">Loading...</p>
                </div>
              }>
                {businessRoutes.map(({ path, component: Component, name }) => (
                  <Route
                    key={name}
                    path={path}
                    element={
                      <ProtectedRoute>
                        <ConsentGate>
                          <Component />
                        </ConsentGate>
                      </ProtectedRoute>
                    }
                  />
                ))}
              </Suspense>

            </Routes>
          </main>
          <Footer />
        </div>
      </BrowserRouter>
    </Auth0Provider>
  );
}

export default App;
