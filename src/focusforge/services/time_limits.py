"""Time limit enforcement service for apps and websites."""
from datetime import datetime
from typing import List, Set
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..database.models import AppActivity, WebActivity, BlockList


class TimeLimitService:
    """Evaluate and enforce per-day time limits."""

    def __init__(self, session: Session, blocker):
        self.session = session
        self.blocker = blocker
        self.over_limit_apps: Set[str] = set()      # process names
        self.over_limit_websites: Set[str] = set()  # domain patterns

    def _today_range(self):
        today = datetime.now().date()
        start_time = datetime.combine(today, datetime.min.time())
        end_time = datetime.combine(today, datetime.max.time())
        return start_time, end_time

    def _get_app_usage_seconds(self, process_pattern: str) -> float:
        start_time, end_time = self._today_range()
        # Match exactly by app_name; if needed, fallback to LIKE
        total = self.session.query(func.coalesce(func.sum(AppActivity.total_seconds), 0.0)).\
            filter(and_(
                AppActivity.start_time >= start_time,
                AppActivity.start_time <= end_time,
                func.lower(AppActivity.app_name) == func.lower(process_pattern)
            )).scalar() or 0.0
        # If exact match returns 0, try a contains match
        if total == 0:
            total = self.session.query(func.coalesce(func.sum(AppActivity.total_seconds), 0.0)).\
                filter(and_(
                    AppActivity.start_time >= start_time,
                    AppActivity.start_time <= end_time,
                    func.lower(AppActivity.app_name).like(f"%{process_pattern.lower()}%")
                )).scalar() or 0.0
        return float(total)

    def _get_website_usage_seconds(self, domain_pattern: str) -> float:
        start_time, end_time = self._today_range()
        total = self.session.query(func.coalesce(func.sum(WebActivity.total_seconds), 0.0)).\
            filter(and_(
                WebActivity.start_time >= start_time,
                WebActivity.start_time <= end_time,
                func.lower(WebActivity.domain).like(f"%{domain_pattern.lower()}%")
            )).scalar() or 0.0
        return float(total)

    def refresh_and_enforce(self):
        """Refresh limits from DB, compute usage, and enforce if exceeded."""
        self.over_limit_apps.clear()
        self.over_limit_websites.clear()

        limits: List[BlockList] = self.session.query(BlockList).filter(
            BlockList.is_active,
            BlockList.daily_limit_seconds.isnot(None),
            BlockList.daily_limit_seconds > 0
        ).all()

        for item in limits:
            if item.item_type == 'app':
                used = self._get_app_usage_seconds(item.pattern)
                if used >= float(item.daily_limit_seconds or 0):
                    self.over_limit_apps.add(item.pattern.lower())
                    # Trigger warning for any running matching processes
                    try:
                        self.blocker.trigger_warning_for_pattern(item.pattern)
                    except Exception:
                        pass
            elif item.item_type == 'website':
                used = self._get_website_usage_seconds(item.pattern)
                if used >= float(item.daily_limit_seconds or 0):
                    self.over_limit_websites.add(item.pattern.lower())

    def is_website_over_limit(self, domain: str) -> bool:
        d = domain.lower()
        for pat in self.over_limit_websites:
            if pat in d:
                return True
        return False

    def is_app_over_limit(self, process_name: str) -> bool:
        return process_name.lower() in self.over_limit_apps


def run_time_limit_enforcer(service: TimeLimitService, interval_seconds: int = 30):
    """Background loop to enforce time limits periodically."""
    import time
    print("⏳ Time limit enforcer started")
    try:
        while True:
            service.refresh_and_enforce()
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\n🛑 Time limit enforcer stopped")
