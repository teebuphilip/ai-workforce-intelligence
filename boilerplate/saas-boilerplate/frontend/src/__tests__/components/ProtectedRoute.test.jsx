/**
 * Frontend Boilerplate Tests - ProtectedRoute Component
 */

import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ProtectedRoute from '../../components/ProtectedRoute';

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  Navigate: ({ to }) => {
    mockNavigate(to);
    return <div>Redirecting to {to}</div>;
  }
}));

describe('ProtectedRoute Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  
  test('shows loading when Auth0 is loading', () => {
    require('@auth0/auth0-react').useAuth0 = () => ({
      isAuthenticated: false,
      isLoading: true
    });
    
    render(
      <BrowserRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </BrowserRouter>
    );
    
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
    expect(screen.queryByText(/Protected Content/i)).not.toBeInTheDocument();
  });
  
  test('redirects to login when not authenticated', () => {
    require('@auth0/auth0-react').useAuth0 = () => ({
      isAuthenticated: false,
      isLoading: false
    });
    
    render(
      <BrowserRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </BrowserRouter>
    );
    
    expect(mockNavigate).toHaveBeenCalledWith('/login');
    expect(screen.queryByText(/Protected Content/i)).not.toBeInTheDocument();
  });
  
  test('renders children when authenticated', () => {
    require('@auth0/auth0-react').useAuth0 = () => ({
      isAuthenticated: true,
      isLoading: false
    });
    
    render(
      <BrowserRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </BrowserRouter>
    );
    
    expect(screen.getByText(/Protected Content/i)).toBeInTheDocument();
  });
});
