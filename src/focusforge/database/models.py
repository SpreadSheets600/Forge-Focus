"""Database models for FocusForge."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class AppActivity(Base):
    """Track desktop app usage."""
    __tablename__ = 'app_activity'
    
    id = Column(Integer, primary_key=True)
    app_name = Column(String(255), nullable=False)
    window_title = Column(String(500))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    total_seconds = Column(Float, default=0.0)
    is_productive = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<AppActivity(app={self.app_name}, duration={self.total_seconds}s)>"


class WebActivity(Base):
    """Track website usage."""
    __tablename__ = 'web_activity'
    
    id = Column(Integer, primary_key=True)
    domain = Column(String(255), nullable=False)
    url = Column(String(1000))
    title = Column(String(500))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    total_seconds = Column(Float, default=0.0)
    is_productive = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<WebActivity(domain={self.domain}, duration={self.total_seconds}s)>"


class FocusSession(Base):
    """Store focus session data."""
    __tablename__ = 'focus_sessions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_minutes = Column(Integer, nullable=False)
    blocked_apps = Column(Text)  # JSON array
    blocked_websites = Column(Text)  # JSON array
    completed = Column(Boolean, default=False)
    success_rate = Column(Float, default=0.0)
    
    def __repr__(self):
        return f"<FocusSession(name={self.name}, duration={self.duration_minutes}m)>"


class Schedule(Base):
    """Scheduled focus times."""
    __tablename__ = 'schedules'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    start_time = Column(String(10))  # HH:MM format
    end_time = Column(String(10))
    days_of_week = Column(String(50))  # Comma-separated: "0,1,2,3,4"
    blocked_apps = Column(Text)
    blocked_websites = Column(Text)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Schedule(name={self.name}, time={self.start_time}-{self.end_time})>"


class BlockList(Base):
    """Apps and websites to block."""
    __tablename__ = 'blocklist'
    
    id = Column(Integer, primary_key=True)
    item_type = Column(String(20))  # 'app' or 'website'
    name = Column(String(255), nullable=False)
    pattern = Column(String(255))  # Process name or domain pattern
    is_active = Column(Boolean, default=True)
    category = Column(String(50))  # 'social', 'gaming', 'entertainment', etc.
    # Optional per-day time limit in seconds; when reached, enforce block
    daily_limit_seconds = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<BlockList(type={self.item_type}, name={self.name})>"


class Settings(Base):
    """App settings."""
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    
    def __repr__(self):
        return f"<Settings(key={self.key})>"


# Database initialization
def init_database(db_path: str = "data/focusforge.db"):
    """Initialize the database and create tables."""
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    # Lightweight migration: ensure new columns exist
    try:
        with engine.connect() as conn:
            # Check if daily_limit_seconds exists in blocklist
            res = conn.execute("PRAGMA table_info(blocklist)")
            cols = [row[1] for row in res]
            if 'daily_limit_seconds' not in cols:
                conn.execute("ALTER TABLE blocklist ADD COLUMN daily_limit_seconds INTEGER")
    except Exception:
        # Best-effort migration; ignore if not supported
        pass
    Session = sessionmaker(bind=engine)
    return Session()


def get_session(db_path: str = "data/focusforge.db"):
    """Get a database session."""
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Session = sessionmaker(bind=engine)
    return Session()
