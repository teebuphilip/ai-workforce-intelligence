# Auto-Loader & Database Module - Complete Guide

**Two major improvements added to the boilerplate:**

---

## 1. Auto-Loader System ✅

### What It Does

**Automatically loads all routes and pages from `business/` directory.**

No more manual imports - just drop a file in the right place and it works.

### Backend Auto-Loader

**File:** `saas-boilerplate/backend/core/loader.py`

**How It Works:**
1. Scans `business/backend/routes/` for `*.py` files
2. Imports each module
3. Looks for `router` variable (FastAPI APIRouter)
4. Mounts to `/api/{filename}`

**Example:**

```python
# business/backend/routes/email_rules.py
from fastapi import APIRouter

router = APIRouter()  # REQUIRED variable name

@router.get("/list")
def list_rules():
    return {"rules": []}
```

**Result:** Endpoint available at `/api/email_rules/list`

**No manual registration needed!**

### Frontend Auto-Loader

**File:** `saas-boilerplate/frontend/src/core/loader.js`

**How It Works:**
1. Uses webpack `require.context` to find all `.jsx` files
2. Lazy loads each component
3. Converts PascalCase to kebab-case for URL
4. Creates route automatically

**Example:**

```jsx
// business/frontend/pages/EmailDashboard.jsx
export default function EmailDashboard() {
  return <div>Email Dashboard</div>;
}
```

**Result:** Page available at `/dashboard/email-dashboard`

**No manual routing needed!**

### Usage in Main Files

**Backend (main.py):**
```python
from core.loader import load_business_routes

app = FastAPI()

# Add core routes
app.include_router(auth_router, prefix="/api/auth")
app.include_router(payments_router, prefix="/api/payments")

# Auto-load business routes
load_business_routes(app)

# All routes from business/backend/routes/*.py now available!
```

**Frontend (App.js):**
```jsx
import { Suspense } from 'react';
import { loadBusinessPages } from './core/loader';

const businessRoutes = loadBusinessPages();

function App() {
  return (
    <Routes>
      {/* Core routes */}
      <Route path="/" element={<Home />} />
      
      {/* Auto-loaded business routes */}
      <Suspense fallback={<div>Loading...</div>}>
        {businessRoutes.map(({ path, component: Component, name }) => (
          <Route key={name} path={path} element={<Component />} />
        ))}
      </Suspense>
    </Routes>
  );
}
```

### Benefits

✅ **Zero configuration** - Drop files, they work  
✅ **Convention over configuration** - Predictable URLs  
✅ **Fail-safe** - One bad route doesn't break others  
✅ **Discoverable** - See loaded routes in logs  

### Logging

The auto-loader logs what it loads:

```
INFO: Loading business routes from: /path/to/business/backend/routes
INFO: ✓ Loaded: email_rules -> /api/email_rules
INFO: ✓ Loaded: ai_sorting -> /api/ai_sorting
INFO: Successfully loaded 2 business route(s)
```

---

## 2. Database Module ✅

### What It Does

**Provides SQLAlchemy ORM with best practices built-in.**

### File Structure

```
backend/
├── core/
│   └── database.py         # Database setup
├── models_example.py       # Example models (copy to business/)
└── main.py                 # Auto-initializes DB
```

### Core Features

**File:** `saas-boilerplate/backend/core/database.py`

1. **Database Connection**
   - SQLite for development (default)
   - PostgreSQL for production (via env var)
   - Automatic table creation

2. **Session Management**
   - `get_db()` dependency for FastAPI
   - Automatic cleanup
   - Thread-safe

3. **Base Model**
   - All models inherit from `Base`
   - Auto table creation

### Configuration

**Via Environment Variable:**

```bash
# Development (default)
DATABASE_URL=sqlite:///./saas_boilerplate.db

# Production
DATABASE_URL=postgresql://user:password@localhost/dbname
```

### Usage in Routes

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from models import EmailRule

router = APIRouter()

@router.get("/rules")
def list_rules(db: Session = Depends(get_db)):
    """List all rules - database injected automatically"""
    rules = db.query(EmailRule).all()
    return rules

@router.post("/rules")
def create_rule(name: str, db: Session = Depends(get_db)):
    """Create new rule"""
    rule = EmailRule(name=name)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.get("/rules/{rule_id}")
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get specific rule"""
    rule = db.query(EmailRule).filter(EmailRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404)
    return rule

@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete rule"""
    rule = db.query(EmailRule).filter(EmailRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404)
    db.delete(rule)
    db.commit()
    return {"deleted": True}
```

### Example Models

**File:** `models_example.py` (copy to `business/backend/models.py`)

**User Model:**
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    auth0_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Business Model (InboxTamer example):**
```python
class EmailRule(Base):
    __tablename__ = "email_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    condition = Column(String, nullable=False)  # from, subject, body
    value = Column(String, nullable=False)
    action = Column(String, nullable=False)  # archive, label, delete
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Relationships:**
```python
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    # ... columns ...
    
    # One-to-many relationship
    subscriptions = relationship("Subscription", back_populates="user")

class Subscription(Base):
    __tablename__ = "subscriptions"
    # ... columns ...
    
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="subscriptions")
```

### Queries

**Basic:**
```python
# Get all
users = db.query(User).all()

# Filter
active_users = db.query(User).filter(User.is_active == True).all()

# Get one
user = db.query(User).filter(User.id == 1).first()

# Count
count = db.query(User).count()
```

**Complex:**
```python
# Join
results = db.query(User, Subscription).join(Subscription).all()

# Order
users = db.query(User).order_by(User.created_at.desc()).all()

# Limit
recent = db.query(User).limit(10).all()

# Pagination
page_size = 20
offset = (page_num - 1) * page_size
users = db.query(User).limit(page_size).offset(offset).all()
```

### Automatic Initialization

**In main.py:**
```python
from core.database import init_db

@app.on_event("startup")
async def startup_event():
    # Database tables created automatically on startup
    init_db()
```

### Database Utilities

```python
from core.database import init_db, drop_db, reset_db

# Create all tables
init_db()

# Drop all tables (CAUTION!)
drop_db()

# Drop and recreate (development only)
reset_db()
```

---

## Complete Example: InboxTamer Email Rules

### 1. Create Model

**File:** `business/backend/models.py`
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime
from core.database import Base

class EmailRule(Base):
    __tablename__ = "email_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    condition = Column(String, nullable=False)
    value = Column(String, nullable=False)
    action = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 2. Create Routes

**File:** `business/backend/routes/email_rules.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models import EmailRule
from pydantic import BaseModel

router = APIRouter()  # Auto-loaded!

class RuleCreate(BaseModel):
    name: str
    condition: str
    value: str
    action: str

@router.get("/")
def list_rules(user_id: int, db: Session = Depends(get_db)):
    return db.query(EmailRule).filter(EmailRule.user_id == user_id).all()

@router.post("/")
def create_rule(rule: RuleCreate, user_id: int, db: Session = Depends(get_db)):
    db_rule = EmailRule(user_id=user_id, **rule.dict())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.get("/{rule_id}")
def get_rule(rule_id: int, user_id: int, db: Session = Depends(get_db)):
    rule = db.query(EmailRule).filter(
        EmailRule.id == rule_id,
        EmailRule.user_id == user_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404)
    return rule

@router.delete("/{rule_id}")
def delete_rule(rule_id: int, user_id: int, db: Session = Depends(get_db)):
    rule = db.query(EmailRule).filter(
        EmailRule.id == rule_id,
        EmailRule.user_id == user_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404)
    db.delete(rule)
    db.commit()
    return {"deleted": True}
```

### 3. Done!

**Endpoints auto-created:**
- `GET /api/email_rules/` - List rules
- `POST /api/email_rules/` - Create rule
- `GET /api/email_rules/{id}` - Get rule
- `DELETE /api/email_rules/{id}` - Delete rule

**No manual registration. Just works.**

---

## Testing Auto-Loader

### Backend Test
```bash
cd saas-boilerplate/backend

# Start server
uvicorn main:app --reload

# Check logs - should see:
# ✓ Loaded: email_rules -> /api/email_rules

# Test endpoint
curl http://localhost:8000/api/email_rules/

# View auto-docs
open http://localhost:8000/docs
```

### Frontend Test
```bash
cd saas-boilerplate/frontend

# Start dev server
npm start

# Check console - should see:
# ✓ Loaded business page: EmailDashboard -> /dashboard/email-dashboard

# Visit page
open http://localhost:3000/dashboard/email-dashboard
```

---

## Updated Requirements

**Added to requirements.txt:**
```
# Database
sqlalchemy>=2.0.0
alembic>=1.13.0
```

**Install:**
```bash
pip install -r requirements.txt --break-system-packages
```

---

## Health Check

**Updated health endpoint shows auto-loader status:**

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "business": "InboxTamer",
  "version": "2.0.0",
  "features": {
    "auto_loader": true,
    "database": true,
    "business_routes_loaded": 2
  }
}
```

---

## Migration Path (Alembic)

**For production database migrations:**

```bash
# Initialize Alembic
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Create email_rules table"

# Apply migration
alembic upgrade head
```

**Optional - only needed when changing schema in production**

---

## Files Created

### Auto-Loader
1. ✅ `backend/core/loader.py` - Backend route auto-loader
2. ✅ `frontend/src/core/loader.js` - Frontend page auto-loader

### Database
3. ✅ `backend/core/database.py` - Database module
4. ✅ `backend/models_example.py` - Example models

### Updated Files
5. ✅ `backend/main.py` - Uses auto-loader and database
6. ✅ `backend/requirements.txt` - Added SQLAlchemy

---

## Benefits Summary

**Auto-Loader:**
✅ Drop files, they work  
✅ No manual imports  
✅ Convention over configuration  
✅ Fail-safe loading  

**Database:**
✅ SQLAlchemy ORM ready  
✅ Dependency injection built-in  
✅ Automatic table creation  
✅ Production-ready patterns  

**Combined:**
✅ Build features faster  
✅ Less boilerplate code  
✅ More maintainable  
✅ Scale to 25+ businesses  

---

## Next Steps

1. ✅ Auto-loader created
2. ✅ Database module created
3. ⏳ Copy models_example.py to business/backend/models.py
4. ⏳ Create your first business route
5. ⏳ Test endpoints
6. ⏳ Build frontend pages

**Everything ready. Build your business logic, not infrastructure. 🚀**
