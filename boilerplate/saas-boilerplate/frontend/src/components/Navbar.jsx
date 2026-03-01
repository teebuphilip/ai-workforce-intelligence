import { Link } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import useConfig from '../hooks/useConfig';

function Navbar() {
  const { isAuthenticated, loginWithRedirect, logout, user } = useAuth0();
  const config = useConfig();
  const roles = user?.['https://teebu.com/roles'] || user?.roles || [];
  const isAdmin = roles.includes('admin');
  const { business, branding } = config;

  return (
    <nav className="bg-white shadow-sm" style={{ borderBottom: `2px solid ${branding.primary_color}` }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <Link to="/" className="flex items-center">
              <img 
                src={business.logo_url} 
                alt={business.name}
                className="h-8 w-auto"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'block';
                }}
              />
              <span 
                className="ml-2 text-xl font-bold"
                style={{ 
                  color: branding.primary_color,
                  display: 'none'
                }}
              >
                {business.name}
              </span>
            </Link>
          </div>

          <div className="flex items-center space-x-8">
            <Link 
              to="/pricing" 
              className="text-gray-700 hover:text-gray-900"
            >
              Pricing
            </Link>
            <Link 
              to="/faq" 
              className="text-gray-700 hover:text-gray-900"
            >
              FAQ
            </Link>
            <Link 
              to="/contact" 
              className="text-gray-700 hover:text-gray-900"
            >
              Contact
            </Link>

            {isAuthenticated ? (
              <>
                <Link
                  to="/dashboard"
                  className="text-gray-700 hover:text-gray-900"
                >
                  Dashboard
                </Link>
                {isAdmin && (
                  <Link
                    to="/admin"
                    className="text-gray-700 hover:text-gray-900 font-medium"
                  >
                    Admin
                  </Link>
                )}
                <button
                  onClick={() => logout({ returnTo: window.location.origin })}
                  className="text-gray-700 hover:text-gray-900"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => loginWithRedirect()}
                  className="text-gray-700 hover:text-gray-900"
                >
                  Login
                </button>
                <button
                  onClick={() => loginWithRedirect({ screen_hint: 'signup' })}
                  className="px-4 py-2 rounded-lg text-white"
                  style={{ backgroundColor: branding.primary_color }}
                >
                  Sign Up
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
