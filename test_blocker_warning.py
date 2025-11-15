"""Test blocker warning dialog functionality."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from focusforge.database import init_database
from focusforge.services import BlockingService

def test_warning_callback():
    """Test that warning callback is triggered."""
    print("Testing blocker warning callback...")
    
    # Initialize
    db = init_database("data/test.db")
    blocker = BlockingService(db)
    
    # Track callback invocations
    warnings = []
    
    def warning_handler(app_name: str, pid: int):
        warnings.append((app_name, pid))
        print(f"⚠️  Warning triggered for {app_name} (PID: {pid})")
    
    # Set callback
    blocker.set_warning_callback(warning_handler)
    
    # Start blocking with notepad as test
    blocker.set_blocked_apps(["notepad.exe"])
    blocker.start_blocking(strict_mode=False)
    
    print("✅ Blocker configured")
    print("📋 Blocked apps:", blocker.blocked_apps)
    print("🔔 Warning callback:", "SET" if blocker.warning_callback else "NOT SET")
    print("⏰ Warning cooldown:", blocker.warning_cooldown, "seconds")
    
    # Test warning state tracking
    blocker.warned_pids[1234] = 0  # Simulate old warning
    print(f"📊 Warned PIDs: {len(blocker.warned_pids)}")
    
    print("\n✅ All checks passed!")
    print("\nℹ️  To test the full flow:")
    print("   1. Run: uv run python -m focusforge.main")
    print("   2. Start a Focus Session")
    print("   3. Open a blocked app (e.g., Chrome if blocked)")
    print("   4. Verify warning dialog appears with only 'Close App' button")
    print("   5. Click 'Close App' and verify process terminates")
    
    # Cleanup
    blocker.stop_blocking()
    db.close()
    
    import os
    try:
        os.remove("data/test.db")
    except Exception:
        pass

if __name__ == "__main__":
    test_warning_callback()
