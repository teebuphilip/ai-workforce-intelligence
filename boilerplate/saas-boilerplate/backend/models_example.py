"""
Example Database Models
Copy to business/backend/models.py and customize
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class User(Base):
    """
    User model - synced with Auth0
    Stores additional user data not in Auth0
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    auth0_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Subscription(Base):
    """
    Subscription model - synced with Stripe
    Tracks user subscription status
    """
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_subscription_id = Column(String, unique=True, index=True)
    stripe_customer_id = Column(String, index=True)
    plan_id = Column(String, nullable=False)
    status = Column(String, nullable=False)  # active, canceled, past_due, trialing
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, status={self.status})>"


# Business-Specific Models Example (InboxTamer)
class EmailRule(Base):
    """
    Example business model for InboxTamer
    """
    __tablename__ = "email_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    condition = Column(String, nullable=False)  # from, subject, body
    value = Column(String, nullable=False)  # What to match
    action = Column(String, nullable=False)  # archive, label, delete
    label = Column(String)  # Optional label for action
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Order of execution
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<EmailRule(id={self.id}, name={self.name})>"


class EmailLog(Base):
    """
    Example: Track processed emails
    """
    __tablename__ = "email_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email_id = Column(String, index=True)  # External email ID
    subject = Column(String)
    sender = Column(String)
    processed_at = Column(DateTime, default=datetime.utcnow)
    rules_applied = Column(Text)  # JSON of rules that matched
    action_taken = Column(String)
    
    def __repr__(self):
        return f"<EmailLog(id={self.id}, subject={self.subject})>"


# Usage Example in Routes:
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models import User, EmailRule
from pydantic import BaseModel

router = APIRouter()

class RuleCreate(BaseModel):
    name: str
    condition: str
    value: str
    action: str
    label: str = None

@router.get("/rules")
def list_rules(user_id: int, db: Session = Depends(get_db)):
    rules = db.query(EmailRule).filter(
        EmailRule.user_id == user_id,
        EmailRule.is_active == True
    ).order_by(EmailRule.priority).all()
    return rules

@router.post("/rules")
def create_rule(rule: RuleCreate, user_id: int, db: Session = Depends(get_db)):
    db_rule = EmailRule(
        user_id=user_id,
        **rule.dict()
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, user_id: int, db: Session = Depends(get_db)):
    rule = db.query(EmailRule).filter(
        EmailRule.id == rule_id,
        EmailRule.user_id == user_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
    return {"deleted": True}
"""
