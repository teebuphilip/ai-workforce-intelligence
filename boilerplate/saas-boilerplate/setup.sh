#!/bin/bash
# SaaS Boilerplate Setup Script
# Run this after copying the boilerplate for a new business

set -e

echo "================================================"
echo "SaaS Boilerplate Setup"
echo "================================================"
echo ""

# Get business name
read -p "Enter business name (e.g., CourtDominion): " BUSINESS_NAME

if [ -z "$BUSINESS_NAME" ]; then
    echo "Error: Business name is required"
    exit 1
fi

echo ""
echo "Setting up $BUSINESS_NAME..."
echo ""

# 1. Backend setup
echo "1. Setting up backend..."
cd backend

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Created .env file (please edit with your API keys)"
else
    echo "✓ .env already exists"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt --break-system-packages || pip install -r requirements.txt
echo "✓ Python dependencies installed"

cd ..

# 2. Frontend setup
echo ""
echo "2. Setting up frontend..."
cd frontend

# Install Node dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies (this may take a few minutes)..."
    npm install
    echo "✓ Node dependencies installed"
else
    echo "✓ Node modules already exist"
fi

# Copy environment file
if [ ! -f .env.local ]; then
    cp .env.example .env.local
    echo "✓ Created .env.local (please edit with your Auth0 credentials)"
else
    echo "✓ .env.local already exists"
fi

cd ..

# 3. Configure business
echo ""
echo "3. Business configuration..."
echo "Edit these files to customize $BUSINESS_NAME:"
echo "  - backend/config/business_config.json"
echo "  - frontend/src/config/business_config.json"
echo "  - Replace frontend/public/logo.svg with your logo"
echo ""

# 4. Next steps
echo "================================================"
echo "Setup Complete! 🎉"
echo "================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure API keys:"
echo "   - Edit backend/.env"
echo "   - Edit frontend/.env.local"
echo ""
echo "2. Edit business config:"
echo "   - backend/config/business_config.json"
echo "   - frontend/src/config/business_config.json"
echo ""
echo "3. Replace logo:"
echo "   - frontend/public/logo.svg"
echo "   - frontend/public/favicon.ico"
echo ""
echo "4. Start development servers:"
echo "   Terminal 1: cd backend && uvicorn main:app --reload"
echo "   Terminal 2: cd frontend && npm start"
echo ""
echo "5. Visit http://localhost:3000"
echo ""
echo "================================================"
