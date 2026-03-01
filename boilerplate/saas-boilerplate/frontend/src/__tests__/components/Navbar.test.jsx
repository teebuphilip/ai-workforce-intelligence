/**
 * Frontend Boilerplate Tests - Navbar Component
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Auth0Provider } from '@auth0/auth0-react';
import Navbar from '../../components/Navbar';

// Mock useConfig hook
jest.mock('../../hooks/useConfig', () => ({
  __esModule: true,
  default: () => ({
    business: {
      name: 'Test Business',
      logo_url: '/logo.svg'
    },
    branding: {
      primary_color: '#3B82F6'
    }
  })
}));

// Mock Auth0
const mockLoginWithRedirect = jest.fn();
const mockLogout = jest.fn();

jest.mock('@auth0/auth0-react', () => ({
  ...jest.requireActual('@auth0/auth0-react'),
  useAuth0: () => ({
    isAuthenticated: false,
    loginWithRedirect: mockLoginWithRedirect,
    logout: mockLogout
  })
}));

const renderNavbar = (isAuthenticated = false) => {
  return render(
    <BrowserRouter>
      <Navbar />
    </BrowserRouter>
  );
};

describe('Navbar Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  
  test('renders business name', () => {
    renderNavbar();
    expect(screen.getByText(/Test Business/i)).toBeInTheDocument();
  });
  
  test('renders navigation links', () => {
    renderNavbar();
    expect(screen.getByText(/Pricing/i)).toBeInTheDocument();
    expect(screen.getByText(/FAQ/i)).toBeInTheDocument();
    expect(screen.getByText(/Contact/i)).toBeInTheDocument();
  });
  
  test('shows login and signup when not authenticated', () => {
    renderNavbar(false);
    expect(screen.getByText(/Login/i)).toBeInTheDocument();
    expect(screen.getByText(/Sign Up/i)).toBeInTheDocument();
  });
  
  test('login button triggers Auth0', () => {
    renderNavbar(false);
    const loginButton = screen.getByText(/Login/i);
    fireEvent.click(loginButton);
    expect(mockLoginWithRedirect).toHaveBeenCalled();
  });
  
  test('signup button triggers Auth0 with signup screen', () => {
    renderNavbar(false);
    const signupButton = screen.getByText(/Sign Up/i);
    fireEvent.click(signupButton);
    expect(mockLoginWithRedirect).toHaveBeenCalledWith({ screen_hint: 'signup' });
  });
});

describe('Navbar - Authenticated', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock authenticated state
    require('@auth0/auth0-react').useAuth0 = () => ({
      isAuthenticated: true,
      loginWithRedirect: mockLoginWithRedirect,
      logout: mockLogout
    });
  });
  
  test('shows dashboard and logout when authenticated', () => {
    renderNavbar(true);
    expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/Logout/i)).toBeInTheDocument();
  });
  
  test('logout button triggers Auth0 logout', () => {
    renderNavbar(true);
    const logoutButton = screen.getByText(/Logout/i);
    fireEvent.click(logoutButton);
    expect(mockLogout).toHaveBeenCalledWith({ returnTo: window.location.origin });
  });
  
  test('does not show login/signup when authenticated', () => {
    renderNavbar(true);
    expect(screen.queryByText(/^Login$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Sign Up$/i)).not.toBeInTheDocument();
  });
});
