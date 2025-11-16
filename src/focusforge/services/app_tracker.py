"""Desktop app activity tracker."""

import time
import platform
from datetime import datetime
from typing import Optional, Tuple
import psutil

# Platform-specific imports
if platform.system() == "Windows":
    try:
        import win32gui
        import win32process
    except ImportError:
        print("Warning: pywin32 not installed. Install it for Windows tracking.")
elif platform.system() == "Linux":
    try:
        from Xlib import display, X
        from Xlib.error import XError
    except ImportError:
        print("Warning: python-xlib not installed. Install it for Linux tracking.")
elif platform.system() == "Darwin":  # macOS
    try:
        from AppKit import NSWorkspace
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGWindowListOptionOnScreenOnly,
            kCGNullWindowID,
        )
    except ImportError:
        print("Warning: pyobjc not installed. Install it for macOS tracking.")


class AppTracker:
    """Track active application usage."""

    def __init__(self):
        self.current_app = None
        self.current_window = None
        self.start_time = None
        self.system = platform.system()

    def get_active_window_windows(self) -> Optional[Tuple[str, str]]:
        """Get active window on Windows."""
        try:
            window = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(window)
            _, pid = win32process.GetWindowThreadProcessId(window)

            try:
                process = psutil.Process(pid)
                app_name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app_name = "Unknown"

            return app_name, window_title
        except Exception as e:
            print(f"Error getting active window: {e}")
            return None

    def get_active_window_linux(self) -> Optional[Tuple[str, str]]:
        """Get active window on Linux."""
        try:
            d = display.Display()
            window = d.get_input_focus().focus

            # Get window title
            wmname = window.get_wm_name()
            wmclass = window.get_wm_class()

            if wmclass:
                app_name = wmclass[1] if len(wmclass) > 1 else wmclass[0]
            else:
                app_name = "Unknown"

            window_title = wmname if wmname else "Unknown"
            return app_name, window_title
        except Exception as e:
            print(f"Error getting active window: {e}")
            return None

    def get_active_window_macos(self) -> Optional[Tuple[str, str]]:
        """Get active window on macOS."""
        try:
            active_app = NSWorkspace.sharedWorkspace().activeApplication()
            app_name = active_app["NSApplicationName"]

            # Get window title
            windows = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly, kCGNullWindowID
            )

            window_title = "Unknown"
            for window in windows:
                if window.get("kCGWindowOwnerName") == app_name:
                    window_title = window.get("kCGWindowName", "Unknown")
                    break

            return app_name, window_title
        except Exception as e:
            print(f"Error getting active window: {e}")
            return None

    def get_active_window(self) -> Optional[Tuple[str, str]]:
        """Get currently active window (platform-independent)."""
        if self.system == "Windows":
            return self.get_active_window_windows()
        elif self.system == "Linux":
            return self.get_active_window_linux()
        elif self.system == "Darwin":
            return self.get_active_window_macos()
        else:
            print(f"Unsupported platform: {self.system}")
            return None

    def is_idle(self, threshold_seconds: int = 60) -> bool:
        """Check if user is idle."""
        # Simple CPU-based idle detection
        # For more accurate detection, use platform-specific APIs
        return False  # Placeholder - implement based on mouse/keyboard activity

    def get_current_activity(self) -> Optional[dict]:
        """Get current app activity."""
        result = self.get_active_window()
        if not result:
            return None

        app_name, window_title = result
        return {
            "app_name": app_name,
            "window_title": window_title,
            "timestamp": datetime.now(),
        }


def track_app_usage(session, tracker: AppTracker, interval: int = 1):
    """
    Continuously track app usage and save to database.

    Args:
        session: SQLAlchemy session
        tracker: AppTracker instance
        interval: Polling interval in seconds
    """
    from ..database.models import AppActivity

    current_activity = None
    start_time = None

    while True:
        try:
            activity = tracker.get_current_activity()

            if activity:
                # Check if app changed
                if (
                    not current_activity
                    or activity["app_name"] != current_activity["app_name"]
                    or activity["window_title"] != current_activity["window_title"]
                ):
                    # Save previous activity
                    if current_activity and start_time:
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()

                        record = AppActivity(
                            app_name=current_activity["app_name"],
                            window_title=current_activity["window_title"],
                            start_time=start_time,
                            end_time=end_time,
                            total_seconds=duration,
                        )
                        active_record = None  # last DB record being extended
                        session.add(record)
                        session.commit()

                    # Start new activity
                    current_activity = activity
                    start_time = datetime.now()

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\nStopping app tracker...")
            break
        except Exception as e:
            print(f"Error in tracking loop: {e}")
            time.sleep(interval)
