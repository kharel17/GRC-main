import sys
import os
import logging

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up basic logging to see the AI service output
logging.basicConfig(level=logging.INFO)

try:
    from app.services.ai_service import ai_service
    print("AI Service: Successfully imported.")
    
    print("AI Service: Starting initialization...")
    ai_service.initialize()
    
    print(f"AI Service Ready: {ai_service.is_ready}")
    print(f"Active Engine: {ai_service.active_engine}")
    
    if ai_service.is_ready:
        print("SUCCESS: AI Service initialized correctly.")
    else:
        print("FAILURE: AI Service failed to initialize.")
        
except Exception as e:
    print(f"ERROR: Verification script encountered an error: {e}")
    import traceback
    traceback.print_exc()
