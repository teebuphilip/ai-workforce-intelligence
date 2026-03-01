/**
 * Frontend Boilerplate Tests - Home Page
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Home from '../../pages/Home';

// Mock hooks
jest.mock('../../hooks/useConfig', () => ({
  __esModule: true,
  default: () => ({
    branding: {
      primary_color: '#3B82F6'
    },
    home: {
      hero: {
        headline: 'Test Headline',
        subheadline: 'Test Subheadline',
        cta_primary: 'Start Free Trial',
        cta_secondary: 'Learn More'
      },
      features: [
        {
          icon: '🎯',
          title: 'Feature 1',
          description: 'Description 1'
        }
      ],
      social_proof: {
        stats: [
          { value: '10K+', label: 'Users' }
        ],
        testimonials: [
          {
            quote: 'Great product!',
            author: 'John Doe',
            title: 'CEO'
          }
        ]
      },
      final_cta: {
        headline: 'Ready to start?',
        subheadline: 'Join us today',
        button_text: 'Get Started'
      }
    }
  })
}));

jest.mock('../../hooks/useAnalytics', () => ({
  __esModule: true,
  default: () => ({
    trackPageView: jest.fn(),
    trackEvent: jest.fn()
  })
}));

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate
}));

describe('Home Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  
  test('renders hero section', () => {
    render(
      <BrowserRouter>
        <Home />
      </BrowserRouter>
    );
    
    expect(screen.getByText(/Test Headline/i)).toBeInTheDocument();
    expect(screen.getByText(/Test Subheadline/i)).toBeInTheDocument();
  });
  
  test('renders CTA buttons', () => {
    render(
      <BrowserRouter>
        <Home />
      </BrowserRouter>
    );
    
    expect(screen.getByText(/Start Free Trial/i)).toBeInTheDocument();
    expect(screen.getByText(/Learn More/i)).toBeInTheDocument();
  });
  
  test('primary CTA navigates to signup', () => {
    render(
      <BrowserRouter>
        <Home />
      </BrowserRouter>
    );
    
    const ctaButton = screen.getAllByText(/Start Free Trial/i)[0];
    fireEvent.click(ctaButton);
    
    expect(mockNavigate).toHaveBeenCalledWith('/signup');
  });
  
  test('renders features section', () => {
    render(
      <BrowserRouter>
        <Home />
      </BrowserRouter>
    );
    
    expect(screen.getByText(/Feature 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Description 1/i)).toBeInTheDocument();
  });
  
  test('renders social proof stats', () => {
    render(
      <BrowserRouter>
        <Home />
      </BrowserRouter>
    );
    
    expect(screen.getByText(/10K\+/i)).toBeInTheDocument();
    expect(screen.getByText(/Users/i)).toBeInTheDocument();
  });
  
  test('renders testimonials', () => {
    render(
      <BrowserRouter>
        <Home />
      </BrowserRouter>
    );
    
    expect(screen.getByText(/Great product!/i)).toBeInTheDocument();
    expect(screen.getByText(/John Doe/i)).toBeInTheDocument();
  });
  
  test('renders final CTA section', () => {
    render(
      <BrowserRouter>
        <Home />
      </BrowserRouter>
    );
    
    expect(screen.getByText(/Ready to start\?/i)).toBeInTheDocument();
  });
});
