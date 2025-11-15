"""Simple test to verify FocusForge installation."""
import sys

def test_imports():
    """Test that all required modules can be imported."""
    try:
        print("Testing imports...")
        
        # Core dependencies
        import flet
        print("✅ Flet")
        
        import fastapi
        print("✅ FastAPI")
        
        import sqlalchemy
        print("✅ SQLAlchemy")
        
        import psutil
        print("✅ psutil")
        
        import plotly
        print("✅ Plotly")
        
        from apscheduler.schedulers.background import BackgroundScheduler
        print("✅ APScheduler")
        
        # FocusForge modules
        from focusforge.database import init_database, get_session
        print("✅ Database module")
        
        from focusforge.services import AppTracker, BlockingService, SchedulerService
        print("✅ Services module")
        
        from focusforge.api import app
        print("✅ API module")
        
        from focusforge.ui import create_ui
        print("✅ UI module")
        
        print("\n🎉 All imports successful!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import failed: {e}")
        print("\nRun: uv sync")
        return False


def test_database():
    """Test database creation."""
    try:
        print("\nTesting database...")
        from focusforge.database import init_database
        
        # Create test database
        session = init_database("data/test.db")
        print("✅ Database created successfully")
        
        # Close session properly
        session.close()
        
        # Clean up
        import os
        import time
        time.sleep(0.1)  # Give time for file handles to close
        
        try:
            if os.path.exists("data/test.db"):
                os.remove("data/test.db")
                print("✅ Test database cleaned up")
        except:
            print("⚠️ Could not remove test database (file in use)")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def test_api():
    """Test API can be created."""
    try:
        print("\nTesting API...")
        from focusforge.api import app
        
        # Check routes exist
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/focus/status" in routes
        assert "/stats/daily" in routes
        
        print("✅ API routes configured")
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("FocusForge Installation Test")
    print("=" * 50)
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("API", test_api),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        results.append(test_func())
    
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for i, (name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(results)
    
    if all_passed:
        print("\n🎉 All tests passed! FocusForge is ready to use.")
        print("\nRun: uv run python -m focusforge.main")
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
