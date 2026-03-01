/**
 * Frontend Core - Page Auto-Loader
 * Automatically loads and routes all pages from business/frontend/pages/
 */

import { lazy } from 'react';
import { Route } from 'react-router-dom';

/**
 * Load all business pages dynamically
 * 
 * Example:
 *   business/frontend/pages/EmailDashboard.jsx
 *   -> Route: /dashboard/email-dashboard
 * 
 * @returns {Array} Array of Route components
 */
export function loadBusinessPages() {
  const routes = [];
  
  try {
    // Use webpack's require.context to load all .jsx files from business/pages
    // Note: Path is relative to this file's location
    const businessPages = require.context(
      '../../../../business/frontend/pages',
      false,
      /\.jsx$/
    );
    
    businessPages.keys().forEach((filePath) => {
      // Extract filename without extension
      // './EmailDashboard.jsx' -> 'EmailDashboard'
      const fileName = filePath.replace('./', '').replace('.jsx', '');
      
      // Convert PascalCase to kebab-case for URL
      // 'EmailDashboard' -> 'email-dashboard'
      const routePath = fileName
        .replace(/([A-Z])/g, '-$1')
        .toLowerCase()
        .substring(1);
      
      // Lazy load the component
      const Component = lazy(() => import(
        `../../../../business/frontend/pages/${fileName}.jsx`
      ));
      
      // Create route object
      routes.push({
        path: `/dashboard/${routePath}`,
        component: Component,
        name: fileName
      });
      
      console.log(`✓ Loaded business page: ${fileName} -> /dashboard/${routePath}`);
    });
    
    if (routes.length > 0) {
      console.log(`Successfully loaded ${routes.length} business page(s)`);
    } else {
      console.log('No business pages loaded (this is OK if you haven\'t created any yet)');
    }
    
  } catch (error) {
    // If business/frontend/pages doesn't exist yet, that's fine
    console.log('No business pages directory found (will be created when you add pages)');
  }
  
  return routes;
}

/**
 * Get list of all loaded business pages
 * 
 * @returns {Array} List of loaded page info
 */
export function getLoadedBusinessPages() {
  try {
    const businessPages = require.context(
      '../../../../business/frontend/pages',
      false,
      /\.jsx$/
    );
    
    return businessPages.keys().map(filePath => {
      const fileName = filePath.replace('./', '').replace('.jsx', '');
      const routePath = fileName
        .replace(/([A-Z])/g, '-$1')
        .toLowerCase()
        .substring(1);
      
      return {
        name: fileName,
        path: `/dashboard/${routePath}`
      };
    });
  } catch (error) {
    return [];
  }
}

/**
 * Fallback loader when webpack require.context is not available
 * (e.g., in test environments)
 */
export function loadBusinessPagesFallback() {
  console.log('Using fallback loader (require.context not available)');
  return [];
}

// Example usage in App.js:
/**
import { Suspense } from 'react';
import { loadBusinessPages } from './core/loader';

const businessRoutes = loadBusinessPages();

function App() {
  return (
    <Routes>
      {/* Core routes *\/}
      <Route path="/" element={<Home />} />
      <Route path="/pricing" element={<Pricing />} />
      
      {/* Auto-loaded business routes *\/}
      <Suspense fallback={<div>Loading...</div>}>
        {businessRoutes.map(({ path, component: Component, name }) => (
          <Route 
            key={name}
            path={path} 
            element={<Component />} 
          />
        ))}
      </Suspense>
    </Routes>
  );
}
*/
