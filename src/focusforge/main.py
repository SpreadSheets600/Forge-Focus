"""Main application entry point."""

import threading
import time
from pathlib import Path

import flet as ft

from .database import init_database
from .services import (
    BlockingService,
    SchedulerService,
    AppTracker,
    track_app_usage,
    run_blocking_service,
    TimeLimitService,
    run_time_limit_enforcer,
)
from .api import set_services, start as start_api
from .ui import create_ui


def ensure_data_directory():
    """Ensure data directory exists."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    return data_dir


def start_background_services(db_session, blocker, scheduler):
    """Start background tracking and blocking services."""

    # Start app tracker in background thread
    tracker = AppTracker()
    tracking_thread = threading.Thread(
        target=track_app_usage, args=(db_session, tracker, 1), daemon=True
    )
    tracking_thread.start()
    print("✅ App tracker started")

    # Start blocker service in background thread
    blocker_thread = threading.Thread(
        target=run_blocking_service, args=(blocker, 1), daemon=True
    )
    blocker_thread.start()
    print("✅ Blocker service started")

    # Start time limit enforcer thread
    limits = TimeLimitService(db_session, blocker)
    limits_thread = threading.Thread(
        target=run_time_limit_enforcer, args=(limits, 30), daemon=True
    )
    limits_thread.start()
    print("✅ Time limit enforcer started")

    # Load schedules
    scheduler.load_schedules()
    print("✅ Schedules loaded")

    return tracker, tracking_thread, blocker_thread, limits, limits_thread


def start_api_server(blocker, scheduler, limits):
    """Start FastAPI server in background thread."""
    # Set services for API
    set_services(blocker, scheduler, limits)

    # Start API server in background thread
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()
    print("✅ API server started on http://localhost:8765")

    return api_thread


def main():
    """Main application entry point."""
    print("🚀 Starting FocusForge...")

    # Ensure data directory exists
    ensure_data_directory()

    # Initialize database
    print("📦 Initializing database...")
    db_session = init_database()

    # Create service instances
    blocker = BlockingService(db_session)
    scheduler = SchedulerService(db_session, blocker)

    # Start background services
    print("🔧 Starting background services...")
    tracker, tracking_thread, blocker_thread, limits, limits_thread = (
        start_background_services(db_session, blocker, scheduler)
    )

    # Start API server
    print("🌐 Starting API server...")

    # Give API server time to start
    time.sleep(2)

    # Create and start UI
    print("🎨 Starting UI...")
    ui_main = create_ui(blocker, scheduler)

    try:
        ft.app(target=ui_main)
    except KeyboardInterrupt:
        print("\n👋 Shutting down FocusForge...")
    finally:
        # Cleanup
        scheduler.shutdown()
        db_session.close()
        print("✅ Shutdown complete")


if __name__ == "__main__":
    main()
