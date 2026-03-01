# Testing Directive - For Claude Code / FounderOps

**Instructions for testing boilerplate and business logic**

---

## ⚡ Note: Auto-Loader Architecture

**The boilerplate uses AUTO-LOADER. Routes and pages load automatically.**

This means:
- No imports needed in main.py or App.js
- Tests also don't need imports
- Just test the endpoint/page directly

---

## Test Layers Overview

```
1. Library Tests (teebu-shared-libs)
   ├── test_stripe_lib.py
   ├── test_mailerlite_lib.py
   ├── test_auth0_lib.py
   ├── test_git_lib.py
   └── test_analytics_lib.py
   Status: ✅ Already created and passing

2. Boilerplate Tests (saas-boilerplate)
   ├── Backend: test auth, payments, config, analytics
   └── Frontend: test components, pages, hooks
   Status: ✅ Created (run to validate infrastructure)

3. Business Tests (business/)
   ├── Backend: test your custom routes
   └── Frontend: test your custom pages
   Status: ⏳ You create these per business
```

---

## Running Tests

### 1. Library Tests (One-Time Validation)

```bash
cd teebu-shared-libs/
python run_all_tests.py

# Expected output:
# ✓ test_stripe_lib.py - 7 passed
# ✓ test_mailerlite_lib.py - 15 passed
# ✓ test_auth0_lib.py - 19 passed
# ✓ test_git_lib.py - 19 passed
# ✓ test_analytics_lib.py - 14 passed
# TOTAL: 74 tests passed
```

### 2. Boilerplate Tests (Infrastructure Validation)

**Backend:**
```bash
cd saas-boilerplate/backend/
python run_tests.py

# Or specific test:
pytest tests/test_auth_routes.py -v
pytest tests/test_payment_routes.py -v
pytest tests/test_config_loading.py -v
pytest tests/test_analytics_routes.py -v
```

**Frontend:**
```bash
cd saas-boilerplate/frontend/
npm test

# Or specific test:
npm test -- Navbar.test.jsx
npm test -- Home.test.jsx
```

### 3. Business Tests (Your Custom Logic)

**Backend:**
```bash
cd business/backend/
pytest tests/ -v
```

**Frontend:**
```bash
cd business/frontend/
npm test
```

---

## Backend Testing Guide

### File Location

**Boilerplate tests:** `saas-boilerplate/backend/tests/test_*.py`
**Business tests:** `business/backend/tests/test_*.py`

### Test Template

```python
"""
Test your custom business route
File: business/backend/tests/test_email_rules.py
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Import app
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), 
    '../../../saas-boilerplate/backend'
)))

from main import app

client = TestClient(app)

class TestEmailRules:
    """Test InboxTamer email rules API"""
    
    def test_list_rules(self):
        """Test GET /api/email_rules/"""
        response = client.get("/api/email_rules/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_rule(self):
        """Test POST /api/email_rules/"""
        rule = {
            "name": "Archive Newsletters",
            "condition": "from",
            "value": "@newsletter.com",
            "action": "archive"
        }
        
        response = client.post("/api/email_rules/", json=rule)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == rule["name"]
        assert "id" in data
    
    @patch('saas_boilerplate.core.auth.get_current_user')
    def test_authenticated_endpoint(self, mock_auth):
        """Test endpoint requiring authentication"""
        # Mock authenticated user
        mock_auth.return_value = MagicMock(
            id="auth0|123",
            email="test@example.com"
        )
        
        response = client.get("/api/email_rules/")
        assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Common Test Patterns

**Pattern 1: Test CRUD Operations**
```python
def test_create_item(self):
    response = client.post("/api/items/", json={"name": "test"})
    assert response.status_code == 200

def test_read_item(self):
    response = client.get("/api/items/1")
    assert response.status_code == 200

def test_update_item(self):
    response = client.put("/api/items/1", json={"name": "updated"})
    assert response.status_code == 200

def test_delete_item(self):
    response = client.delete("/api/items/1")
    assert response.status_code == 200
```

**Pattern 2: Test Authentication**
```python
@patch('saas_boilerplate.core.auth.get_current_user')
def test_requires_auth(self, mock_auth):
    mock_auth.return_value = MagicMock(id="auth0|123")
    response = client.get("/api/protected/")
    assert response.status_code == 200

def test_rejects_unauthenticated(self):
    response = client.get("/api/protected/")
    assert response.status_code == 401
```

**Pattern 3: Test Validation**
```python
def test_validates_input(self):
    response = client.post("/api/items/", json={"invalid": "data"})
    assert response.status_code == 422  # Validation error

def test_requires_fields(self):
    response = client.post("/api/items/", json={})
    assert response.status_code == 422
```

**Pattern 4: Test Error Handling**
```python
@patch('business.backend.routes.items.external_service')
def test_handles_external_failure(self, mock_service):
    mock_service.side_effect = Exception("Service down")
    
    response = client.get("/api/items/")
    assert response.status_code == 500
```

---

## Frontend Testing Guide

### File Location

**Boilerplate tests:** `saas-boilerplate/frontend/src/__tests__/`
**Business tests:** `business/frontend/tests/`

### Test Template

```jsx
/**
 * Test your custom page
 * File: business/frontend/tests/EmailDashboard.test.jsx
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import EmailDashboard from '../pages/EmailDashboard';
import api from 'saas-boilerplate/utils/api';

// Mock API
jest.mock('saas-boilerplate/utils/api');

// Mock hooks
jest.mock('saas-boilerplate/core/hooks', () => ({
  useAuth: () => ({
    user: { sub: 'auth0|123', name: 'Test User' }
  }),
  useAnalytics: () => ({
    trackPageView: jest.fn(),
    trackEvent: jest.fn()
  })
}));

describe('EmailDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  
  test('renders page title', () => {
    render(
      <BrowserRouter>
        <EmailDashboard />
      </BrowserRouter>
    );
    
    expect(screen.getByText(/Email Dashboard/i)).toBeInTheDocument();
  });
  
  test('loads emails on mount', async () => {
    const mockEmails = [
      { id: 1, subject: 'Test Email', from: 'test@example.com' }
    ];
    
    api.get = jest.fn().mockResolvedValue({ data: mockEmails });
    
    render(
      <BrowserRouter>
        <EmailDashboard />
      </BrowserRouter>
    );
    
    await waitFor(() => {
      expect(screen.getByText(/Test Email/i)).toBeInTheDocument();
    });
    
    expect(api.get).toHaveBeenCalledWith('/inbox/emails', expect.any(Object));
  });
  
  test('handles archive button click', async () => {
    api.get = jest.fn().mockResolvedValue({ data: [] });
    api.post = jest.fn().mockResolvedValue({ data: { success: true } });
    
    render(
      <BrowserRouter>
        <EmailDashboard />
      </BrowserRouter>
    );
    
    const archiveButton = screen.getByText(/Archive/i);
    fireEvent.click(archiveButton);
    
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/inbox/emails/1/archive');
    });
  });
});
```

### Common Test Patterns

**Pattern 1: Test Rendering**
```jsx
test('renders component', () => {
  render(<YourComponent />);
  expect(screen.getByText(/Expected Text/i)).toBeInTheDocument();
});
```

**Pattern 2: Test User Interactions**
```jsx
test('handles button click', () => {
  render(<YourComponent />);
  
  const button = screen.getByText(/Submit/i);
  fireEvent.click(button);
  
  expect(screen.getByText(/Success/i)).toBeInTheDocument();
});
```

**Pattern 3: Test Async Data Loading**
```jsx
test('loads data', async () => {
  api.get = jest.fn().mockResolvedValue({ data: mockData });
  
  render(<YourComponent />);
  
  await waitFor(() => {
    expect(screen.getByText(/Data/i)).toBeInTheDocument();
  });
});
```

**Pattern 4: Test Forms**
```jsx
test('submits form', async () => {
  api.post = jest.fn().mockResolvedValue({ data: { success: true } });
  
  render(<YourForm />);
  
  const input = screen.getByLabelText(/Name/i);
  fireEvent.change(input, { target: { value: 'Test Name' } });
  
  const submit = screen.getByText(/Submit/i);
  fireEvent.click(submit);
  
  await waitFor(() => {
    expect(api.post).toHaveBeenCalledWith('/endpoint', {
      name: 'Test Name'
    });
  });
});
```

---

## Test-Driven Development (TDD) Workflow

### For New Features

**Step 1: Write Test First**
```python
# business/backend/tests/test_new_feature.py
def test_new_endpoint():
    response = client.get("/api/new_feature/")
    assert response.status_code == 200
    # Test should FAIL (endpoint doesn't exist yet)
```

**Step 2: Implement Minimum Code**
```python
# business/backend/routes/new_feature.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_feature():
    return {}  # Minimum to pass test
```

**Step 3: Run Test**
```bash
pytest business/backend/tests/test_new_feature.py
# Should PASS now
```

**Step 4: Add More Tests, Refine Implementation**
```python
def test_returns_correct_data():
    response = client.get("/api/new_feature/")
    data = response.json()
    assert "items" in data
    # Fails again, add logic to pass
```

---

## Integration Testing

### Test Boilerplate + Business Logic Together

```python
class TestIntegration:
    """Test business logic integrates with boilerplate"""
    
    @patch('main.analytics')
    def test_business_route_tracks_analytics(self, mock_analytics):
        """Verify your route uses boilerplate analytics"""
        mock_analytics.track_event.return_value = {"success": True}
        
        # Call your business endpoint
        response = client.post("/api/your_feature/action")
        
        # Verify it used boilerplate analytics
        mock_analytics.track_event.assert_called_once()
    
    @patch('main.auth0')
    def test_business_route_requires_auth(self, mock_auth0):
        """Verify your route uses boilerplate auth"""
        # Call without auth should fail
        response = client.get("/api/your_feature/protected")
        assert response.status_code == 401
```

---

## Coverage Goals

### Minimum Coverage

**Backend:**
- ✅ All routes return correct status codes
- ✅ All routes validate input
- ✅ All routes handle errors
- ✅ Auth-required routes reject unauthenticated requests

**Frontend:**
- ✅ All pages render without crashing
- ✅ All interactive elements work (buttons, forms)
- ✅ All API calls are made correctly
- ✅ Loading and error states display

### Good Coverage (Aim For)

**Backend:** 80%+ code coverage
```bash
pytest --cov=business/backend/routes --cov-report=html
```

**Frontend:** 70%+ code coverage
```bash
npm test -- --coverage
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          cd saas-boilerplate/backend
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          cd saas-boilerplate/backend
          pytest tests/ -v --cov
  
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Node
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd saas-boilerplate/frontend
          npm install
      - name: Run tests
        run: |
          cd saas-boilerplate/frontend
          npm test -- --coverage
```

---

## Testing Checklist

### Before Committing Code

**Backend:**
- [ ] All new routes have tests
- [ ] Tests cover success cases
- [ ] Tests cover error cases
- [ ] Tests cover validation
- [ ] All tests pass: `pytest tests/ -v`

**Frontend:**
- [ ] All new pages/components have tests
- [ ] Tests cover rendering
- [ ] Tests cover user interactions
- [ ] Tests cover API calls
- [ ] All tests pass: `npm test`

### Before Deploying

- [ ] All library tests pass
- [ ] All boilerplate tests pass
- [ ] All business tests pass
- [ ] Integration tests pass
- [ ] Manual testing complete

---

## Common Issues & Solutions

### Backend

**Issue:** Tests can't find main.py
```python
# Solution: Fix path
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), 
    '../../../saas-boilerplate/backend'
)))
```

**Issue:** Mock not working
```python
# Solution: Patch at the right location
@patch('main.stripe')  # Patch where it's used, not where it's defined
```

### Frontend

**Issue:** Component not rendering in test
```jsx
// Solution: Wrap in Router and providers
render(
  <BrowserRouter>
    <YourComponent />
  </BrowserRouter>
);
```

**Issue:** Async test failing
```jsx
// Solution: Use waitFor
await waitFor(() => {
  expect(screen.getByText(/Text/i)).toBeInTheDocument();
});
```

---

## Resources

**Backend Testing:**
- FastAPI Testing: https://fastapi.tiangolo.com/tutorial/testing/
- Pytest Docs: https://docs.pytest.org/
- Mock/Patch: https://docs.python.org/3/library/unittest.mock.html

**Frontend Testing:**
- React Testing Library: https://testing-library.com/react
- Jest: https://jestjs.io/
- Testing Best Practices: https://kentcdodds.com/blog/common-mistakes-with-react-testing-library

---

## Summary

**3 Test Layers:**
1. Libraries (validate libs work)
2. Boilerplate (validate infrastructure)
3. Business (validate YOUR logic)

**Run tests at each layer:**
- Libraries: One-time validation
- Boilerplate: On infrastructure updates
- Business: On every code change

**All tests must pass before deploy.**

**Templates provided in:**
- `saas-boilerplate/backend/tests/` (boilerplate examples)
- `saas-boilerplate/frontend/src/__tests__/` (boilerplate examples)
- `business/backend/tests/test_template.py` (your backend template)
- `business/frontend/tests/test_template.jsx` (your frontend template)

**Copy templates, adapt to your features, run tests, ship with confidence. ✅**
