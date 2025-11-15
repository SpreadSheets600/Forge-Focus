"""Scheduling service for automatic focus sessions."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time as dt_time
import json


class SchedulerService:
    """Manage scheduled focus sessions."""
    
    def __init__(self, session, blocker):
        self.session = session
        self.blocker = blocker
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
    def load_schedules(self):
        """Load all schedules from database and add to scheduler."""
        from ..database.models import Schedule
        
        schedules = self.session.query(Schedule).filter_by(is_active=True).all()
        
        for sched in schedules:
            self.add_schedule(
                schedule_id=sched.id,
                name=sched.name,
                start_time=sched.start_time,
                end_time=sched.end_time,
                days=sched.days_of_week,
                blocked_apps=json.loads(sched.blocked_apps) if sched.blocked_apps else [],
                blocked_websites=json.loads(sched.blocked_websites) if sched.blocked_websites else []
            )
    
    def add_schedule(self, schedule_id: int, name: str, start_time: str, 
                     end_time: str, days: str, blocked_apps: list, blocked_websites: list):
        """
        Add a scheduled focus session.
        
        Args:
            schedule_id: Unique ID for the schedule
            name: Schedule name
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            days: Comma-separated days (0=Monday, 6=Sunday)
            blocked_apps: List of apps to block
            blocked_websites: List of websites to block
        """
        start_hour, start_minute = map(int, start_time.split(':'))
        end_hour, end_minute = map(int, end_time.split(':'))
        day_list = days.split(',') if days else None
        
        # Schedule start
        self.scheduler.add_job(
            func=self._start_focus,
            trigger=CronTrigger(
                day_of_week=day_list,
                hour=start_hour,
                minute=start_minute
            ),
            args=[name, blocked_apps, blocked_websites],
            id=f"start_{schedule_id}",
            replace_existing=True
        )
        
        # Schedule end
        self.scheduler.add_job(
            func=self._stop_focus,
            trigger=CronTrigger(
                day_of_week=day_list,
                hour=end_hour,
                minute=end_minute
            ),
            id=f"stop_{schedule_id}",
            replace_existing=True
        )
        
        print(f"📅 Scheduled: {name} ({start_time}-{end_time})")
    
    def remove_schedule(self, schedule_id: int):
        """Remove a schedule."""
        try:
            self.scheduler.remove_job(f"start_{schedule_id}")
            self.scheduler.remove_job(f"stop_{schedule_id}")
            print(f"🗑️ Removed schedule {schedule_id}")
        except Exception as e:
            print(f"Error removing schedule: {e}")
    
    def _start_focus(self, name: str, blocked_apps: list, blocked_websites: list):
        """Internal: Start a focus session."""
        print(f"🎯 Auto-starting focus: {name}")
        self.blocker.set_blocked_apps(blocked_apps)
        self.blocker.set_blocked_websites(blocked_websites)
        self.blocker.start_blocking(strict_mode=True)
    
    def _stop_focus(self):
        """Internal: Stop focus session."""
        print("⏹️ Auto-stopping focus session")
        self.blocker.stop_blocking()
    
    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
