"""App and website blocking service."""
import time
import platform
import psutil
from typing import List, Set, Callable, Optional, Dict
from datetime import datetime


class BlockingService:
    """Service to block apps and websites during focus sessions."""

    def __init__(self, session):
        self.session = session
        self.system = platform.system()
        self.blocked_apps: Set[str] = set()
        self.blocked_websites: Set[str] = set()
        self.active = False
        self.strict_mode = False
        self.session_start = None
        # UI integration
        self.warning_callback: Optional[Callable[[str, int], None]] = None
        self.warned_pids: Dict[int, float] = {}  # pid -> last warning timestamp
        self.warning_cooldown = 15

    def set_blocked_apps(self, apps: List[str]):
        """Set list of apps to block."""
        self.blocked_apps = set(app.lower() for app in apps)

    def set_blocked_websites(self, websites: List[str]):
        """Set list of websites to block."""
        self.blocked_websites = set(site.lower() for site in websites)

    def set_warning_callback(self, callback: Callable[[str, int], None]):
        """Register a UI callback to show a warning for blocked apps."""
        self.warning_callback = callback

    def start_blocking(self, strict_mode: bool = False):
        """Start blocking service."""
        self.active = True
        self.strict_mode = strict_mode
        self.session_start = datetime.now()
        self.warned_pids.clear()
        print(f"🚫 Blocking started (Strict: {strict_mode})")
        print(f"📱 Blocked apps: {', '.join(self.blocked_apps)}")
        print(f"🌐 Blocked websites: {', '.join(self.blocked_websites)}")

    def stop_blocking(self, passphrase: str = None) -> bool:
        """Stop blocking service with optional strict-mode passphrase."""
        if self.strict_mode:
            if not passphrase:
                return False
            if self.session_start:
                elapsed = (datetime.now() - self.session_start).total_seconds()
                if elapsed < 900:  # 15 minutes
                    print(f"⏱️ Cooldown active. {int(900 - elapsed)} seconds remaining.")
                    return False
            required = "I choose discipline today and commit to my goals"
            if passphrase.strip() != required:
                print("❌ Incorrect passphrase")
                return False

        self.active = False
        self.strict_mode = False
        self.warned_pids.clear()
        print("✅ Blocking stopped")
        return True

    def kill_process(self, process_name: str) -> bool:
        """Kill a process by executable name."""
        killed = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if (proc.info['name'] or '').lower() == process_name.lower():
                    psutil.Process(proc.info['pid']).terminate()
                    killed = True
                    print(f"⚡ Terminated: {process_name}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return killed

    def force_kill_pid(self, pid: int) -> bool:
        """Force kill a process by PID (called from UI warning)."""
        try:
            psutil.Process(pid).terminate()
            if pid in self.warned_pids:
                del self.warned_pids[pid]
            print(f"⚡ Terminated PID: {pid}")
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

    def monitor_and_block(self):
        """Monitor running processes and show warnings for blocked apps."""
        if not self.active:
            return

        now = time.time()
        # Cleanup stale PIDs
        self.warned_pids = {pid: ts for pid, ts in self.warned_pids.items() if psutil.pid_exists(pid)}

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = (proc.info['name'] or '').lower()
                pid = proc.info['pid']
                for blocked in self.blocked_apps:
                    if blocked in proc_name:
                        print(f"🚨 Detected blocked app running: {proc.info['name']} (pid={pid}) matches pattern '{blocked}'")
                        last = self.warned_pids.get(pid, 0)
                        if now - last > self.warning_cooldown:
                            if self.warning_callback:
                                try:
                                    self.warning_callback(proc.info['name'] or 'Unknown', pid)
                                except Exception as e:
                                    print(f"Warning callback error: {e}")
                            else:
                                # Fallback: kill if UI not connected
                                self.kill_process(proc.info['name'] or '')
                            self.warned_pids[pid] = now
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def is_website_blocked(self, domain: str) -> bool:
        """Check if a website is blocked by pattern match."""
        domain = domain.lower()
        for blocked in self.blocked_websites:
            if blocked in domain:
                return True
        return False

    def trigger_warning_for_pattern(self, process_pattern: str):
        """Trigger warnings for any running process matching the given pattern."""
        patt = process_pattern.lower()
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = (proc.info['name'] or '').lower()
                if patt in name:
                    now = time.time()
                    last = self.warned_pids.get(proc.info['pid'], 0)
                    if now - last > self.warning_cooldown:
                        self.warned_pids[proc.info['pid']] = now
                        if self.warning_callback:
                            try:
                                self.warning_callback(proc.info['name'] or 'Unknown', proc.info['pid'])
                            except Exception as e:
                                print(f"Warning callback error: {e}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def get_block_status(self) -> dict:
        """Get current blocking status."""
        return {
            'active': self.active,
            'strict_mode': self.strict_mode,
            'blocked_apps': list(self.blocked_apps),
            'blocked_websites': list(self.blocked_websites),
            'session_duration': (datetime.now() - self.session_start).total_seconds() if self.session_start else 0,
        }


def run_blocking_service(blocker: BlockingService, interval: int = 1):
    """
    Run blocking service in background.
    
    Args:
        blocker: BlockingService instance
        interval: Check interval in seconds
    """
    print("🛡️ Blocking service started")
    
    try:
        while True:
            if blocker.active:
                blocker.monitor_and_block()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 Blocking service stopped")
