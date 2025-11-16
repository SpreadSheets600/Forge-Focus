"""Main Flet UI for FocusForge."""
import flet as ft
from datetime import datetime, timedelta
import json
from sqlalchemy import func, and_

from ..database.models import AppActivity, WebActivity, FocusSession, get_session
from ..utils.analytics import (
    create_daily_usage_chart,
    create_productivity_score_gauge,
    create_focus_sessions_chart
)
from ..utils.helpers import format_duration, get_motivational_quote


class FocusForgeUI:
    """Main UI controller."""
    
    def __init__(self, blocker_service, scheduler_service):
        self.blocker = blocker_service
        self.scheduler = scheduler_service
        self.db = get_session()
        self.page = None
        self.current_view = "dashboard"
        
        # Setup blocker warning callback
        self.blocker.set_warning_callback(self._on_blocked_app_warning)
    
    def _on_blocked_app_warning(self, app_name: str, pid: int):
        """Called when a blocked app is detected - show warning dialog."""
        if not self.page:
            return
        
        def close_app(e):
            self.blocker.force_kill_process(pid)
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("🚫 Blocked Application Detected", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        f"You've opened a blocked application during your focus session:",
                        size=14,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        f"📱 {app_name}",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color="#fa709a",
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "This app is blocked to help you stay focused. Please close it to continue.",
                        size=14,
                        color=ft.Colors.WHITE70,
                    ),
                ]),
                width=400,
            ),
            actions=[
                ft.ElevatedButton(
                    "Close App",
                    on_click=close_app,
                    bgcolor="#fa709a",
                    color=ft.Colors.WHITE,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
    
    def main(self, page: ft.Page):
        """Main app entry point."""
        self.page = page
        page.title = "FocusForge"
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 0
        page.window.width = 1200
        page.window.height = 800
        
        # Custom theme with neon/glow Colors
        page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary="#667eea",
                secondary="#764ba2",
                background="#0a0a0a",
                surface="#1a1a1a",
            ),
        )
        
        # Connect blocker UI warning callback (ensure UI exists)
        def _warn(app_name: str, pid: int):
            # Schedule UI dialog on main thread
            def show_dialog():
                title = ft.Text(f"{app_name}", color=ft.Colors.RED, size=18, weight=ft.FontWeight.BOLD)
                txt = ft.Text("This app is blocked during focus. Close it to continue.")
                def close_app(_):
                    try:
                        self.blocker.force_kill_pid(pid)
                    finally:
                        dlg.open = False
                        self.page.update()
                dlg.actions = [
                    ft.ElevatedButton("Close App", bgcolor=ft.Colors.RED, color=ft.Colors.WHITE, on_click=close_app),
                ]
                dlg.title = title
                dlg.content = txt
                dlg.modal = True
                dlg.open = True
                self.page.update()

            # Prepare dialog control once and reuse
            if not hasattr(self, "_block_dialog"):
                dlg = ft.AlertDialog(modal=True)
                self._block_dialog = dlg
                self.page.dialog = dlg
            else:
                dlg = self._block_dialog

            # Try to marshal to UI thread if available
            try:
                if hasattr(self.page, "run_on_main"):
                    self.page.run_on_main(show_dialog)
                else:
                    show_dialog()
            except Exception:
                # Best-effort fallback
                show_dialog()

        # register callback
        try:
            self.blocker.set_warning_callback(_warn)
        except Exception:
            pass

        # Sidebar navigation
        sidebar = ft.Container(
            content=ft.Column([
                ft.Container(height=20),
                ft.Text("⚡ FocusForge", size=24, weight=ft.FontWeight.BOLD,
                       color=ft.Colors.with_opacity(0.9, "#667eea")),
                ft.Container(height=40),
                self._nav_button("📊 Dashboard", "dashboard"),
                self._nav_button("🎯 Focus Mode", "focus"),
                self._nav_button("🚫 Blocklist", "blocklist"),
                self._nav_button("📅 Schedule", "schedule"),
                self._nav_button("⚙️ Settings", "settings"),
            ]),
            width=220,
            bgcolor="#1a1a1a",
            padding=20,
        )
        
        # Main content area
        self.content_area = ft.Container(
            content=self._build_dashboard(),
            expand=True,
            padding=30,
        )
        
        # Main layout
        page.add(
            ft.Row([
                sidebar,
                self.content_area,
            ], expand=True, spacing=0)
        )
    
    def _nav_button(self, text: str, view: str):
        """Create navigation button."""
        return ft.TextButton(
            text=text,
            style=ft.ButtonStyle(
                color={"": ft.Colors.WHITE70, "hovered": "#667eea"},
                overlay_color={"": "transparent", "hovered": ft.Colors.with_opacity(0.1, "#667eea")},
            ),
            on_click=lambda _: self._navigate_to(view),
            width=180,
        )
    
    def _navigate_to(self, view: str):
        """Navigate to a view."""
        self.current_view = view
        
        if view == "dashboard":
            self.content_area.content = self._build_dashboard()
        elif view == "focus":
            self.content_area.content = self._build_focus_mode()
        elif view == "blocklist":
            self.content_area.content = self._build_blocklist()
        elif view == "schedule":
            self.content_area.content = self._build_schedule()
        elif view == "settings":
            self.content_area.content = self._build_settings()
        
        self.page.update()
    
    def _build_dashboard(self):
        """Build dashboard view."""
        # Get today's stats
        today = datetime.now().date()
        start_time = datetime.combine(today, datetime.min.time())
        end_time = datetime.combine(today, datetime.max.time())
        
        app_stats = self.db.query(
            AppActivity.app_name,
            func.sum(AppActivity.total_seconds).label('total_time')
        ).filter(
            and_(AppActivity.start_time >= start_time, AppActivity.start_time <= end_time)
        ).group_by(AppActivity.app_name).order_by(
            func.sum(AppActivity.total_seconds).desc()
        ).limit(5).all()
        
        web_stats = self.db.query(
            WebActivity.domain,
            func.sum(WebActivity.total_seconds).label('total_time')
        ).filter(
            and_(WebActivity.start_time >= start_time, WebActivity.start_time <= end_time)
        ).group_by(WebActivity.domain).order_by(
            func.sum(WebActivity.total_seconds).desc()
        ).limit(5).all()
        
        # Total time tracked
        total_app_time = sum(t for _, t in app_stats) if app_stats else 0
        total_web_time = sum(t for _, t in web_stats) if web_stats else 0
        
        return ft.Column([
            ft.Text("Dashboard", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(height=20),
            
            # Stats cards
            ft.Row([
                self._stat_card("⏱️ Apps", format_duration(total_app_time), "#667eea"),
                self._stat_card("🌐 Websites", format_duration(total_web_time), "#764ba2"),
                self._stat_card("🎯 Focus Sessions", "3 today", "#43e97b"),
                self._stat_card("📈 Score", "85/100", "#fa709a"),
            ], spacing=20),
            
            ft.Container(height=30),
            
            # Top apps and websites
            ft.Text("Today's Activity", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            
            ft.Row([
                # Top apps
                ft.Container(
                    content=ft.Column([
                        ft.Text("📱 Top Apps", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        *[self._activity_row(app, time) for app, time in app_stats[:5]]
                    ]),
                    bgcolor="#1a1a1a",
                    border_radius=10,
                    padding=20,
                    expand=True,
                ),
                
                # Top websites
                ft.Container(
                    content=ft.Column([
                        ft.Text("🌐 Top Websites", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        *[self._activity_row(domain, time) for domain, time in web_stats[:5]]
                    ]),
                    bgcolor="#1a1a1a",
                    border_radius=10,
                    padding=20,
                    expand=True,
                ),
            ], spacing=20),
        ], scroll=ft.ScrollMode.AUTO)
    
    def _stat_card(self, label: str, value: str, color: str):
        """Create a stat card."""
        return ft.Container(
            content=ft.Column([
                ft.Text(label, size=14, color=ft.Colors.WHITE70),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD,
                       color=color),
            ], spacing=5),
            bgcolor="#1a1a1a",
            border_radius=10,
            padding=20,
            expand=True,
            border=ft.border.all(2, ft.Colors.with_opacity(0.2, color)),
        )
    
    def _activity_row(self, name: str, seconds: float):
        """Create activity row."""
        return ft.Row([
            ft.Text(name, size=14, expand=True),
            ft.Text(format_duration(seconds), size=14, color="#667eea"),
        ], spacing=10)
    
    def _build_focus_mode(self):
        """Build focus mode view."""
        status = self.blocker.get_block_status()
        
        if status['active']:
            return self._build_active_focus(status)
        else:
            return self._build_start_focus()
    
    def _build_start_focus(self):
        """Build start focus UI."""
        duration_slider = ft.Slider(
            min=15,
            max=180,
            divisions=33,
            value=60,
            label="{value} min",
        )
        
        session_name = ft.TextField(
            label="Session Name",
            value="Deep Work",
            bgcolor="#1a1a1a",
        )
        
        strict_mode_check = ft.Checkbox(
            label="Strict Mode (requires passphrase to stop)",
            value=False,
        )
        
        def start_focus(e):
            # Start focus session
            duration = int(duration_slider.value)
            
            # Get blocked items from DB
            from ..database.models import BlockList
            blocked_apps = [b.pattern for b in self.db.query(BlockList).filter_by(
                item_type="app", is_active=True
            ).all()]
            
            blocked_websites = [b.pattern for b in self.db.query(BlockList).filter_by(
                item_type="website", is_active=True
            ).all()]
            
            # Start blocking
            self.blocker.set_blocked_apps(blocked_apps)
            self.blocker.set_blocked_websites(blocked_websites)
            self.blocker.start_blocking(strict_mode=strict_mode_check.value)
            
            # Create session record
            focus_session = FocusSession(
                name=session_name.value,
                start_time=datetime.now(),
                duration_minutes=duration,
                blocked_apps=json.dumps(blocked_apps),
                blocked_websites=json.dumps(blocked_websites),
                completed=False
            )
            self.db.add(focus_session)
            self.db.commit()
            
            # Refresh view
            self._navigate_to("focus")
        
        return ft.Column([
            ft.Text("🎯 Focus Mode", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(height=20),
            
            ft.Container(
                content=ft.Column([
                    ft.Text("✨ " + get_motivational_quote(),
                           size=18, italic=True, color=ft.Colors.WHITE70),
                ]),
                bgcolor="#1a1a1a",
                border_radius=10,
                padding=20,
            ),
            
            ft.Container(height=30),
            
            session_name,
            ft.Container(height=20),
            
            ft.Text("Duration", size=16),
            duration_slider,
            ft.Container(height=20),
            
            strict_mode_check,
            ft.Container(height=30),
            
            ft.ElevatedButton(
                "🚀 Start Focus Session",
                on_click=start_focus,
                style=ft.ButtonStyle(
                    bgcolor="#667eea",
                    color=ft.Colors.WHITE,
                    padding=20,
                ),
                width=200,
            ),
        ], scroll=ft.ScrollMode.AUTO)
    
    def _build_active_focus(self, status: dict):
        """Build active focus session UI."""
        passphrase_field = ft.TextField(
            label="Enter passphrase to stop (if strict mode)",
            password=True,
            can_reveal_password=True,
            bgcolor="#1a1a1a",
        )
        
        def stop_focus(e):
            success = self.blocker.stop_blocking(
                passphrase=passphrase_field.value if status['strict_mode'] else None
            )
            
            if success:
                # Update session
                last_session = self.db.query(FocusSession).filter_by(
                    completed=False
                ).order_by(FocusSession.start_time.desc()).first()
                
                if last_session:
                    last_session.end_time = datetime.now()
                    last_session.completed = True
                    self.db.commit()
                
                self._navigate_to("focus")
            else:
                self.page.snack_bar = ft.SnackBar(
                    ft.Text("Incorrect passphrase or cooldown active"),
                    bgcolor=ft.Colors.RED,
                )
                self.page.snack_bar.open = True
                self.page.update()
        
        duration_minutes = int(status['session_duration'] / 60)
        
        return ft.Column([
            ft.Text("🎯 Focus Session Active", size=32, weight=ft.FontWeight.BOLD,
                   color="#43e97b"),
            ft.Container(height=20),
            
            ft.Container(
                content=ft.Column([
                    ft.Text(f"⏱️ {duration_minutes} minutes elapsed",
                           size=24, weight=ft.FontWeight.BOLD),
                    ft.Container(height=10),
                    ft.Text("Stay focused! You're doing great! 💪",
                           size=16, color=ft.Colors.WHITE70),
                ]),
                bgcolor="#1a1a1a",
                border_radius=10,
                padding=30,
                border=ft.border.all(2, "#43e97b"),
            ),
            
            ft.Container(height=30),
            
            ft.Text("🚫 Blocked Apps:", size=16, weight=ft.FontWeight.BOLD),
            *[ft.Text(f"  • {app}", size=14, color=ft.Colors.WHITE70)
              for app in status['blocked_apps'][:5]],
            
            ft.Container(height=20),
            
            ft.Text("🌐 Blocked Websites:", size=16, weight=ft.FontWeight.BOLD),
            *[ft.Text(f"  • {site}", size=14, color=ft.Colors.WHITE70)
              for site in status['blocked_websites'][:5]],
            
            ft.Container(height=30),
            
            passphrase_field if status['strict_mode'] else ft.Container(),
            ft.Container(height=20) if status['strict_mode'] else ft.Container(),
            
            ft.ElevatedButton(
                "⏹️ Stop Focus Session",
                on_click=stop_focus,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.RED,
                    color=ft.Colors.WHITE,
                    padding=20,
                ),
                width=200,
            ),
        ], scroll=ft.ScrollMode.AUTO)
    
    def _build_blocklist(self):
        """Build blocklist view."""
        from ..database.models import BlockList
        
        blocked_apps = self.db.query(BlockList).filter_by(
            item_type="app", is_active=True
        ).all()
        
        blocked_websites = self.db.query(BlockList).filter_by(
            item_type="website", is_active=True
        ).all()
        
        new_app_name = ft.TextField(label="App Name", bgcolor="#1a1a1a")
        new_app_pattern = ft.TextField(label="Process Name (e.g., chrome.exe)", bgcolor="#1a1a1a")
        
        new_website_name = ft.TextField(label="Website Name", bgcolor="#1a1a1a")
        new_website_domain = ft.TextField(label="Domain (e.g., youtube.com)", bgcolor="#1a1a1a")
        
        def add_app(e):
            if new_app_name.value and new_app_pattern.value:
                item = BlockList(
                    item_type="app",
                    name=new_app_name.value,
                    pattern=new_app_pattern.value,
                )
                self.db.add(item)
                self.db.commit()
                self._navigate_to("blocklist")
        
        def add_website(e):
            if new_website_name.value and new_website_domain.value:
                item = BlockList(
                    item_type="website",
                    name=new_website_name.value,
                    pattern=new_website_domain.value,
                )
                self.db.add(item)
                self.db.commit()
                self._navigate_to("blocklist")
        
        def _limit_row(item):
            current_min = int((item.daily_limit_seconds or 0) // 60)
            minutes_field = ft.TextField(
                label="Daily Limit (minutes)",
                value=str(current_min) if current_min > 0 else "",
                width=200,
                bgcolor="#1a1a1a",
            )

            def save_limit(_):
                try:
                    val = minutes_field.value.strip()
                    seconds = int(val) * 60 if val else None
                    obj = self.db.query(BlockList).filter_by(id=item.id).first()
                    obj.daily_limit_seconds = seconds
                    self.db.commit()
                    self.page.snack_bar = ft.SnackBar(ft.Text("Saved limit"))
                    self.page.snack_bar.open = True
                    self.page.update()
                except Exception as ex:
                    self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor=ft.Colors.RED)
                    self.page.snack_bar.open = True
                    self.page.update()

            def test_now(_):
                try:
                    # Manually trigger a warning for matching running processes
                    self.blocker.trigger_warning_for_pattern(item.pattern)
                except Exception as ex:
                    self.page.snack_bar = ft.SnackBar(ft.Text(f"Test failed: {ex}"), bgcolor=ft.Colors.RED)
                    self.page.snack_bar.open = True
                    self.page.update()

            return ft.Row([
                ft.Text(item.name, size=14, expand=True),
                ft.Text(item.pattern, size=12, color=ft.Colors.WHITE70, width=220),
                minutes_field,
                ft.ElevatedButton("Save", on_click=save_limit, bgcolor="#667eea"),
                ft.OutlinedButton("Test", on_click=test_now),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        return ft.Column([
            ft.Text("🚫 Blocklist", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(height=20),
            
            ft.Row([
                # Apps column
                ft.Container(
                    content=ft.Column([
                        ft.Text("📱 Blocked Apps", size=20, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        *([_limit_row(app) for app in blocked_apps] or [ft.Text("No apps", size=12, color=ft.Colors.WHITE70)]),
                        ft.Container(height=20),
                        new_app_name,
                        new_app_pattern,
                        ft.Container(height=10),
                        ft.ElevatedButton("Add App", on_click=add_app, bgcolor="#667eea"),
                    ]),
                    bgcolor="#1a1a1a",
                    border_radius=10,
                    padding=20,
                    expand=True,
                ),
                
                # Websites column
                ft.Container(
                    content=ft.Column([
                        ft.Text("🌐 Blocked Websites", size=20, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        *([_limit_row(site) for site in blocked_websites] or [ft.Text("No websites", size=12, color=ft.Colors.WHITE70)]),
                        ft.Container(height=20),
                        new_website_name,
                        new_website_domain,
                        ft.Container(height=10),
                        ft.ElevatedButton("Add Website", on_click=add_website, bgcolor="#667eea"),
                    ]),
                    bgcolor="#1a1a1a",
                    border_radius=10,
                    padding=20,
                    expand=True,
                ),
            ], spacing=20),
        ], scroll=ft.ScrollMode.AUTO)
    
    def _build_schedule(self):
        """Build schedule view."""
        from ..database.models import Schedule as ScheduleModel
        from ..database.models import BlockList as BlockListModel

        schedules = self.db.query(ScheduleModel).filter_by(is_active=True).all()

        # Form fields
        name_field = ft.TextField(label="Name", bgcolor="#1a1a1a", value="Work Block")
        start_field = ft.TextField(label="Start (HH:MM)", bgcolor="#1a1a1a", value="09:00", width=160)
        end_field = ft.TextField(label="End (HH:MM)", bgcolor="#1a1a1a", value="12:00", width=160)

        # Days of week checkboxes 0=Mon .. 6=Sun to match CronTrigger in code
        days_map = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        day_checks = [ft.Checkbox(label=d, value=(i<5)) for i, d in enumerate(days_map)]

        # Select apps/websites to block
        apps = self.db.query(BlockListModel).filter_by(item_type="app", is_active=True).all()
        sites = self.db.query(BlockListModel).filter_by(item_type="website", is_active=True).all()
        app_checks = [ft.Checkbox(label=a.name, value=True, data=a.pattern) for a in apps]
        site_checks = [ft.Checkbox(label=s.name, value=True, data=s.pattern) for s in sites]

        msg = ft.Text(visible=False)

        def add_schedule(_):
            try:
                # Validate times
                def _valid_time(v: str) -> bool:
                    try:
                        h,m = map(int, v.split(':'))
                        return 0 <= h <= 23 and 0 <= m <= 59
                    except Exception:
                        return False
                if not (_valid_time(start_field.value) and _valid_time(end_field.value)):
                    raise ValueError("Invalid time format. Use HH:MM")

                selected_days = [str(i) for i, cb in enumerate(day_checks) if cb.value]
                blocked_apps = [cb.data for cb in app_checks if cb.value]
                blocked_sites = [cb.data for cb in site_checks if cb.value]

                if not selected_days:
                    raise ValueError("Select at least one day")

                # Persist schedule
                sched = ScheduleModel(
                    name=name_field.value or "Focus",
                    start_time=start_field.value,
                    end_time=end_field.value,
                    days_of_week=",".join(selected_days),
                    blocked_apps=json.dumps(blocked_apps),
                    blocked_websites=json.dumps(blocked_sites),
                    is_active=True,
                )
                self.db.add(sched)
                self.db.commit()

                # Register with scheduler service
                self.scheduler.add_schedule(
                    schedule_id=sched.id,
                    name=sched.name,
                    start_time=sched.start_time,
                    end_time=sched.end_time,
                    days=sched.days_of_week,
                    blocked_apps=blocked_apps,
                    blocked_websites=blocked_sites,
                )

                msg.value = "✅ Schedule added"
                msg.color = ft.Colors.GREEN
                msg.visible = True
                self._navigate_to("schedule")
            except Exception as ex:
                msg.value = f"❌ {ex}"
                msg.color = ft.Colors.RED
                msg.visible = True
                self.page.update()

        # Build UI
        return ft.Column([
            ft.Text("📅 Schedule", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(height=16),

            # Create form
            ft.Container(
                content=ft.Column([
                    ft.Text("Create Schedule", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(height=8),
                    name_field,
                    ft.Row([start_field, end_field], spacing=16),
                    ft.Text("Days", size=14, color=ft.Colors.WHITE70),
                    ft.Row(day_checks, wrap=True, spacing=10),
                    ft.Container(height=6),
                    ft.Text("Apps to block", size=14, color=ft.Colors.WHITE70),
                    ft.Row(app_checks, wrap=True, spacing=10),
                    ft.Container(height=6),
                    ft.Text("Websites to block", size=14, color=ft.Colors.WHITE70),
                    ft.Row(site_checks, wrap=True, spacing=10),
                    ft.Container(height=10),
                    ft.Row([
                        ft.ElevatedButton("➕ Add Schedule", on_click=add_schedule, bgcolor="#667eea"),
                        msg
                    ]),
                ]),
                bgcolor="#1a1a1a",
                border_radius=10,
                padding=20,
            ),

            ft.Container(height=20),
            ft.Text("Active Schedules", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(height=8),
            *[self._schedule_card(sched) for sched in schedules],
        ], scroll=ft.ScrollMode.AUTO)
    
    def _schedule_card(self, schedule):
        """Create schedule card."""
        def remove(_):
            try:
                # Disable in DB
                from ..database.models import Schedule as ScheduleModel
                s = self.db.query(ScheduleModel).filter_by(id=schedule.id).first()
                if s:
                    s.is_active = False
                    self.db.commit()
                # Remove from scheduler
                self.scheduler.remove_schedule(schedule.id)
                self._navigate_to("schedule")
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(str(ex)), bgcolor=ft.Colors.RED)
                self.page.snack_bar.open = True
                self.page.update()

        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(schedule.name, size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{schedule.start_time} - {schedule.end_time} | Days: {schedule.days_of_week}",
                           size=14, color=ft.Colors.WHITE70),
                ], expand=True),
                ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=remove),
            ]),
            bgcolor="#1a1a1a",
            border_radius=10,
            padding=15,
            margin=ft.margin.only(bottom=10),
        )
    
    def _build_settings(self):
        """Build settings view."""
        return ft.Column([
            ft.Text("⚙️ Settings", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(height=20),
            
            ft.Container(
                content=ft.Column([
                    ft.Text("General Settings", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(height=20),
                    ft.Switch(label="Dark Mode", value=True),
                    ft.Switch(label="Notifications", value=True),
                    ft.Switch(label="Sound Effects", value=True),
                ]),
                bgcolor="#1a1a1a",
                border_radius=10,
                padding=20,
            ),
        ], scroll=ft.ScrollMode.AUTO)


def create_ui(blocker_service, scheduler_service):
    """Create and return the UI."""
    ui = FocusForgeUI(blocker_service, scheduler_service)
    return ui.main
