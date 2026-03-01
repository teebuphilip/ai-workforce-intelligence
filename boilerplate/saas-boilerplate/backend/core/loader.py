"""
Backend Core - Route Auto-Loader
Automatically loads and mounts all routes from business/backend/routes/
"""

import os
import sys
import importlib.util
from pathlib import Path
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)

def load_business_routes(app: FastAPI, business_routes_path: str = "../business/backend/routes"):
    """
    Automatically load all route files from business directory.
    
    Example:
        business/backend/routes/email_rules.py (with router variable)
        -> Mounted at /api/email_rules
    
    Args:
        app: FastAPI application instance
        business_routes_path: Path to business routes directory
    
    Returns:
        int: Number of routes loaded
    """
    
    # Get absolute path to business routes
    current_dir = Path(__file__).parent
    routes_dir = (current_dir / business_routes_path).resolve()
    
    if not routes_dir.exists():
        logger.info(f"No business routes directory found at {routes_dir}")
        logger.info("Business routes will be loaded when business/ directory is created")
        return 0
    
    logger.info(f"Loading business routes from: {routes_dir}")
    
    # Add business routes to Python path
    business_backend_path = str(routes_dir.parent)
    if business_backend_path not in sys.path:
        sys.path.insert(0, business_backend_path)
    
    loaded_count = 0
    
    # Load all Python files in routes directory
    for route_file in sorted(routes_dir.glob("*.py")):
        if route_file.name.startswith("_"):
            # Skip private files like __init__.py
            continue
        
        module_name = route_file.stem
        
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(
                f"routes.{module_name}",
                route_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if module has a router
            if not hasattr(module, 'router'):
                logger.warning(
                    f"Skipping {route_file.name}: No 'router' variable found. "
                    f"Add: router = APIRouter()"
                )
                continue
            
            # Mount the router
            prefix = f"/api/{module_name}"
            app.include_router(
                module.router,
                prefix=prefix,
                tags=[module_name.replace("_", " ").title()]
            )
            
            loaded_count += 1
            logger.info(f"✓ Loaded: {module_name} -> {prefix}")
            
        except Exception as e:
            logger.error(f"✗ Failed to load {route_file.name}: {e}")
            # Continue loading other routes even if one fails
            continue
    
    if loaded_count > 0:
        logger.info(f"Successfully loaded {loaded_count} business route(s)")
    else:
        logger.info("No business routes loaded (this is OK if you haven't created any yet)")
    
    return loaded_count


def get_loaded_business_routes(app: FastAPI):
    """
    Get list of all loaded business routes.
    
    Returns:
        list: List of route info dicts
    """
    business_routes = []
    
    for route in app.routes:
        if hasattr(route, 'path') and route.path.startswith('/api/'):
            # Extract route name from path
            parts = route.path.split('/')
            if len(parts) >= 3:
                route_name = parts[2]
                
                # Check if this looks like a business route (not a core route)
                if route_name not in ['auth', 'payments', 'analytics', 'webhooks', 'contact', 'config']:
                    business_routes.append({
                        'name': route_name,
                        'path': route.path,
                        'methods': list(route.methods) if hasattr(route, 'methods') else []
                    })
    
    return business_routes


# Example usage in main.py:
"""
from core.loader import load_business_routes

app = FastAPI()

# Add core routes first
app.include_router(auth_router, prefix="/api/auth")
app.include_router(payments_router, prefix="/api/payments")

# Auto-load business routes
load_business_routes(app)

# Now all routes from business/backend/routes/*.py are available
"""
