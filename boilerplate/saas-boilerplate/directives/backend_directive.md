# Backend Directive - For Claude Code / FounderOps

**Instructions for building backend business logic**

---

## ⚡ CRITICAL: Auto-Loader - No Integration Required

**THE BOILERPLATE AUTOMATICALLY LOADS YOUR ROUTES. DO NOT EDIT MAIN.PY.**

### What You Do
1. Create file in `business/backend/routes/`
2. Include `router = APIRouter()` variable
3. Done - it auto-loads

### What You DON'T Do
❌ Import your route in main.py
❌ Call app.include_router()
❌ Edit main.py at all
❌ Register anything manually

**Files in business/backend/routes/*.py automatically become /api/{filename} endpoints.**

---

## Location

**ALL backend code goes in:** `business/backend/routes/`

---

## File Structure

```python
# business/backend/routes/your_feature.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Import shared services (already available)
from saas_boilerplate.core.auth import get_current_user
from saas_boilerplate.core.analytics import track_event
from saas_boilerplate.core.database import get_db
from sqlalchemy.orm import Session

# REQUIRED: Must export a router variable
router = APIRouter(tags=["your-feature"])

# Define your models
class YourModel(BaseModel):
    name: str
    value: int

# Define your endpoints
@router.get("/")
def list_items():
    return {"items": []}

@router.post("/")
def create_item(item: YourModel, user = Depends(get_current_user)):
    # Your business logic here
    track_event("item_created", user_id=user.id)
    return {"success": True, "item": item}
```

**Result:** 
- Endpoints auto-mounted to `/api/your_feature/`
- No import needed
- No registration needed
- Just start the server

---

## Available Shared Services

### 1. Authentication

```python
from saas_boilerplate.core.auth import get_current_user

@router.get("/protected")
def protected_route(user = Depends(get_current_user)):
    # user.id, user.email, user.name available
    return {"user_id": user.id}
```

### 2. Analytics

```python
from saas_boilerplate.core.analytics import track_event, track_page_view

@router.post("/action")
def some_action(user = Depends(get_current_user)):
    track_event("button_clicked", user_id=user.id, event_params={
        "button": "save",
        "page": "dashboard"
    })
    return {"success": True}
```

### 3. Stripe (Payments)

```python
from saas_boilerplate.libs.stripe_lib import load_stripe_lib

stripe = load_stripe_lib('config/stripe_config.json')

@router.post("/custom-payment")
def custom_payment():
    result = stripe.create_subscription_product(
        business_name="Custom Product",
        description="..."
    )
    return result
```

### 4. MailerLite (Email)

```python
from saas_boilerplate.libs.mailerlite_lib import load_mailerlite_lib

mailer = load_mailerlite_lib('config/mailerlite_config.json')

@router.post("/subscribe-to-feature")
def subscribe_feature(email: str):
    result = mailer.add_subscriber(
        email=email,
        fields={"feature": "custom"},
        groups=["feature_subscribers"]
    )
    return result
```

### 5. Database (If Added)

```python
from saas_boilerplate.core.database import get_db
from sqlalchemy.orm import Session

@router.get("/items")
def get_items(db: Session = Depends(get_db)):
    # Use SQLAlchemy
    items = db.query(YourModel).all()
    return items
```

---

## Common Patterns

### Pattern 1: CRUD API

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()

# In-memory storage (replace with DB later)
items = []

class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: str

@router.get("/", response_model=List[Item])
def list_items():
    return items

@router.post("/", response_model=Item)
def create_item(item: Item):
    item.id = len(items) + 1
    items.append(item)
    return item

@router.get("/{item_id}", response_model=Item)
def get_item(item_id: int):
    item = next((i for i in items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.put("/{item_id}", response_model=Item)
def update_item(item_id: int, updated: Item):
    for i, item in enumerate(items):
        if item.id == item_id:
            updated.id = item_id
            items[i] = updated
            return updated
    raise HTTPException(status_code=404, detail="Item not found")

@router.delete("/{item_id}")
def delete_item(item_id: int):
    global items
    items = [i for i in items if i.id != item_id]
    return {"deleted": True}
```

### Pattern 2: External API Integration

```python
import requests
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/external-data")
async def fetch_external_data(query: str):
    try:
        response = requests.get(
            f"https://api.example.com/data",
            params={"q": query},
            headers={"Authorization": "Bearer YOUR_API_KEY"}
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Pattern 3: File Upload

```python
from fastapi import APIRouter, File, UploadFile
import shutil

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save file
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"filename": file.filename, "path": file_path}
```

### Pattern 4: Background Task

```python
from fastapi import APIRouter, BackgroundTasks

router = APIRouter()

def process_data(item_id: int):
    # Long-running task
    import time
    time.sleep(10)
    print(f"Processed {item_id}")

@router.post("/process/{item_id}")
async def start_processing(item_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_data, item_id)
    return {"message": "Processing started"}
```

### Pattern 5: Webhooks

```python
from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib

router = APIRouter()

@router.post("/webhook")
async def handle_webhook(request: Request):
    # Verify signature
    signature = request.headers.get("X-Webhook-Signature")
    body = await request.body()
    
    expected = hmac.new(
        b"your_webhook_secret",
        body,
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Process webhook
    data = await request.json()
    # Handle data...
    
    return {"received": True}
```

---

## Error Handling

### Standard Pattern:

```python
from fastapi import HTTPException
from pydantic import ValidationError

@router.get("/risky")
def risky_operation(param: str):
    try:
        # Your logic that might fail
        if not param:
            raise ValueError("param is required")
        
        result = some_operation(param)
        return {"result": result}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Log error
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Testing Your Routes

### 1. Start Backend:
```bash
cd saas-boilerplate/backend
uvicorn main:app --reload
```

### 2. Test with curl:
```bash
# GET request
curl http://localhost:8000/api/your_feature/

# POST request
curl -X POST http://localhost:8000/api/your_feature/ \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "value": 123}'
```

### 3. Interactive Docs:
- Open: http://localhost:8000/docs
- Test all endpoints interactively

---

## Example: InboxTamer Email Rules

```python
# business/backend/routes/email_rules.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from saas_boilerplate.core.auth import get_current_user
from saas_boilerplate.core.analytics import track_event

router = APIRouter(tags=["email-rules"])

# In-memory storage (replace with DB)
rules = {}

class EmailRule(BaseModel):
    id: Optional[int] = None
    user_id: str
    name: str
    condition: str  # "from", "subject", "body"
    value: str      # What to match
    action: str     # "archive", "label", "delete"
    label: Optional[str] = None

@router.get("/", response_model=List[EmailRule])
def list_rules(user = Depends(get_current_user)):
    """Get all email rules for current user"""
    user_rules = [r for r in rules.values() if r.user_id == user.id]
    track_event("rules_viewed", user_id=user.id)
    return user_rules

@router.post("/", response_model=EmailRule)
def create_rule(rule: EmailRule, user = Depends(get_current_user)):
    """Create new email rule"""
    rule.user_id = user.id
    rule.id = len(rules) + 1
    rules[rule.id] = rule
    
    track_event("rule_created", user_id=user.id, event_params={
        "condition": rule.condition,
        "action": rule.action
    })
    
    return rule

@router.get("/{rule_id}", response_model=EmailRule)
def get_rule(rule_id: int, user = Depends(get_current_user)):
    """Get specific rule"""
    rule = rules.get(rule_id)
    if not rule or rule.user_id != user.id:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.put("/{rule_id}", response_model=EmailRule)
def update_rule(rule_id: int, updated: EmailRule, user = Depends(get_current_user)):
    """Update existing rule"""
    if rule_id not in rules or rules[rule_id].user_id != user.id:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    updated.id = rule_id
    updated.user_id = user.id
    rules[rule_id] = updated
    
    track_event("rule_updated", user_id=user.id)
    return updated

@router.delete("/{rule_id}")
def delete_rule(rule_id: int, user = Depends(get_current_user)):
    """Delete rule"""
    if rule_id not in rules or rules[rule_id].user_id != user.id:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    del rules[rule_id]
    track_event("rule_deleted", user_id=user.id)
    return {"deleted": True}

@router.post("/{rule_id}/test")
def test_rule(rule_id: int, email_content: dict, user = Depends(get_current_user)):
    """Test rule against sample email"""
    rule = rules.get(rule_id)
    if not rule or rule.user_id != user.id:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Simple matching logic
    matches = False
    if rule.condition == "from":
        matches = rule.value.lower() in email_content.get("from", "").lower()
    elif rule.condition == "subject":
        matches = rule.value.lower() in email_content.get("subject", "").lower()
    elif rule.condition == "body":
        matches = rule.value.lower() in email_content.get("body", "").lower()
    
    return {
        "matches": matches,
        "action": rule.action if matches else None
    }
```

---

## Database Integration (Optional)

### Add SQLAlchemy:

```python
# business/backend/models.py
from sqlalchemy import Column, Integer, String, ForeignKey
from saas_boilerplate.core.database import Base

class YourModel(Base):
    __tablename__ = "your_table"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    name = Column(String)
    value = Column(Integer)
```

```python
# business/backend/routes/your_route.py
from sqlalchemy.orm import Session
from saas_boilerplate.core.database import get_db
from ..models import YourModel

@router.get("/items")
def list_items(db: Session = Depends(get_db)):
    return db.query(YourModel).all()

@router.post("/items")
def create_item(item: dict, db: Session = Depends(get_db)):
    db_item = YourModel(**item)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
```

---

## Security Checklist

- [ ] All sensitive routes use `Depends(get_current_user)`
- [ ] User can only access their own data
- [ ] Input validation with Pydantic models
- [ ] API keys/secrets in environment variables
- [ ] Error messages don't leak sensitive info
- [ ] Rate limiting on expensive operations

---

## Performance Tips

- Use `async def` for I/O-bound operations
- Use background tasks for long-running jobs
- Cache expensive queries
- Paginate large lists
- Use database indexes

---

## Ready to Build

1. Create file: `business/backend/routes/your_feature.py`
2. Define router with endpoints
3. Test at http://localhost:8000/docs
4. Integrate with frontend

**The boilerplate handles everything else.**
