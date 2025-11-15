"""FastAPI server for FocusForge."""
import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..database.models import (
    AppActivity, WebActivity, FocusSession, Schedule, BlockList, Settings, get_session
)
from ..services.time_limits import TimeLimitService

# Global instances (will be set by main app)
blocker_service = None
scheduler_service = None
limits_service: TimeLimitService | None = None

app = FastAPI(
    title="FocusForge API",
    description="Backend API for FocusForge productivity app",
    version="1.0.0"
)

# Enable CORS for browser extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your extension ID
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class WebActivityCreate(BaseModel):
    domain: str
    url: Optional[str] = None
    title: Optional[str] = None
    timestamp: datetime
    duration: Optional[float] = None


class LimitItem(BaseModel):
    id: int
    item_type: str
    name: str
    pattern: str
    daily_limit_seconds: Optional[int]
    used_today_seconds: float


class LimitSetRequest(BaseModel):
    # Select item either by id or by (item_type + pattern)
    id: Optional[int] = None
    item_type: Optional[str] = None  # 'app' | 'website'
    pattern: Optional[str] = None
    minutes: int  # New limit in minutes; use 0 to clear


class LimitStatusResponse(BaseModel):
    item_type: str
    pattern: str
    used_today_seconds: float
    limit_seconds: Optional[int]
    over_limit: bool


class FocusSessionCreate(BaseModel):
    name: str
    duration_minutes: int
    blocked_apps: List[str]
    blocked_websites: List[str]
    strict_mode: bool = False


class ScheduleCreate(BaseModel):
    name: str
    start_time: str  # HH:MM
    end_time: str
    days_of_week: str  # "0,1,2,3,4"
    blocked_apps: List[str]
    blocked_websites: List[str]


class BlockListItem(BaseModel):
    item_type: str  # 'app' or 'website'
    name: str
    pattern: str
    category: Optional[str] = None


class StopBlockingRequest(BaseModel):
    passphrase: Optional[str] = None


# Dependency
def get_db():
    """Get database session."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


# Health check
@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "app": "FocusForge API",
        "version": "1.0.0"
    }


# Website activity endpoints
@app.post("/website-activity")
def log_website_activity(activity: WebActivityCreate, db: Session = Depends(get_db)):
    """Log website activity from browser extension."""
    record = WebActivity(
        domain=activity.domain,
        url=activity.url,
        title=activity.title,
        start_time=activity.timestamp,
        end_time=activity.timestamp,
        total_seconds=float(activity.duration or 1.0)
    )
    db.add(record)
    db.commit()
    return {"status": "success", "id": record.id}


@app.get("/website-activity/check-blocked/{domain}")
def check_website_blocked(domain: str):
    """Check if a website is blocked."""
    # Block when in focus session list OR over configured time limit
    if blocker_service and blocker_service.is_website_blocked(domain):
        return {
            "blocked": True,
            "message": "This website is blocked during focus time"
        }
    if limits_service and limits_service.is_website_over_limit(domain):
        return {
            "blocked": True,
            "message": "Daily time limit reached for this site"
        }
    return {"blocked": False}


# Focus session endpoints
@app.post("/focus/start")
def start_focus_session(session_data: FocusSessionCreate, db: Session = Depends(get_db)):
    """Start a focus session."""
    if not blocker_service:
        raise HTTPException(status_code=503, detail="Blocker service not available")
    
    # Create session record
    focus_session = FocusSession(
        name=session_data.name,
        start_time=datetime.now(),
        duration_minutes=session_data.duration_minutes,
        blocked_apps=json.dumps(session_data.blocked_apps),
        blocked_websites=json.dumps(session_data.blocked_websites),
        completed=False
    )
    db.add(focus_session)
    db.commit()
    
    # Start blocking
    blocker_service.set_blocked_apps(session_data.blocked_apps)
    blocker_service.set_blocked_websites(session_data.blocked_websites)
    blocker_service.start_blocking(strict_mode=session_data.strict_mode)
    
    return {
        "status": "success",
        "session_id": focus_session.id,
        "message": "Focus session started"
    }


@app.post("/focus/stop")
def stop_focus_session(request: StopBlockingRequest, db: Session = Depends(get_db)):
    """Stop the current focus session."""
    if not blocker_service:
        raise HTTPException(status_code=503, detail="Blocker service not available")
    
    success = blocker_service.stop_blocking(passphrase=request.passphrase)
    
    if not success:
        raise HTTPException(
            status_code=403,
            detail="Cannot stop focus session. Passphrase required or incorrect."
        )
    
    # Update last session
    last_session = db.query(FocusSession).filter_by(completed=False).order_by(
        FocusSession.start_time.desc()
    ).first()
    
    if last_session:
        last_session.end_time = datetime.now()
        last_session.completed = True
        db.commit()
    
    return {"status": "success", "message": "Focus session stopped"}


@app.get("/focus/status")
def get_focus_status():
    """Get current focus session status."""
    if not blocker_service:
        return {"active": False}
    
    return blocker_service.get_block_status()


# === Time Limits API ===
@app.get("/limits", response_model=list[LimitItem])
def list_limits(db: Session = Depends(get_db)):
    from datetime import datetime
    start = datetime.combine(datetime.now().date(), datetime.min.time())
    end = datetime.combine(datetime.now().date(), datetime.max.time())

    items = db.query(BlockList).filter(BlockList.is_active == True).all()
    results: list[LimitItem] = []

    # Compute usage per item
    for it in items:
        if it.item_type == 'app':
            used = db.query(func.coalesce(func.sum(AppActivity.total_seconds), 0.0)).\
                filter(
                    and_(
                        AppActivity.start_time >= start,
                        AppActivity.start_time <= end,
                        func.lower(AppActivity.app_name).like(f"%{it.pattern.lower()}%")
                    )
                ).scalar() or 0.0
        else:
            used = db.query(func.coalesce(func.sum(WebActivity.total_seconds), 0.0)).\
                filter(
                    and_(
                        WebActivity.start_time >= start,
                        WebActivity.start_time <= end,
                        func.lower(WebActivity.domain).like(f"%{it.pattern.lower()}%")
                    )
                ).scalar() or 0.0

        results.append(LimitItem(
            id=it.id,
            item_type=it.item_type,
            name=it.name,
            pattern=it.pattern,
            daily_limit_seconds=it.daily_limit_seconds,
            used_today_seconds=float(used),
        ))

    return results


@app.post("/limits")
def set_limit(req: LimitSetRequest, db: Session = Depends(get_db)):
    if req.id is not None:
        item = db.query(BlockList).filter_by(id=req.id, is_active=True).first()
    else:
        if not (req.item_type and req.pattern):
            raise HTTPException(status_code=400, detail="Provide id or (item_type and pattern)")
        item = db.query(BlockList).filter_by(
            item_type=req.item_type, pattern=req.pattern, is_active=True
        ).first()
    if not item:
        raise HTTPException(status_code=404, detail="BlockList item not found")

    seconds = int(req.minutes) * 60
    if seconds <= 0:
        item.daily_limit_seconds = None
    else:
        item.daily_limit_seconds = seconds
    db.commit()
    return {"status": "success", "id": item.id, "daily_limit_seconds": item.daily_limit_seconds}


@app.delete("/limits/{item_id}")
def clear_limit(item_id: int, db: Session = Depends(get_db)):
    item = db.query(BlockList).filter_by(id=item_id, is_active=True).first()
    if not item:
        raise HTTPException(status_code=404, detail="BlockList item not found")
    item.daily_limit_seconds = None
    db.commit()
    return {"status": "success"}


@app.get("/limits/status", response_model=LimitStatusResponse)
def get_limit_status(item_type: str, pattern: str, db: Session = Depends(get_db)):
    from datetime import datetime
    if item_type not in ("app", "website"):
        raise HTTPException(status_code=400, detail="item_type must be 'app' or 'website'")

    start = datetime.combine(datetime.now().date(), datetime.min.time())
    end = datetime.combine(datetime.now().date(), datetime.max.time())

    item = db.query(BlockList).filter_by(item_type=item_type, pattern=pattern, is_active=True).first()
    limit = item.daily_limit_seconds if item else None

    if item_type == 'app':
        used = db.query(func.coalesce(func.sum(AppActivity.total_seconds), 0.0)).\
            filter(
                and_(
                    AppActivity.start_time >= start,
                    AppActivity.start_time <= end,
                    func.lower(AppActivity.app_name).like(f"%{pattern.lower()}%")
                )
            ).scalar() or 0.0
        over = bool(limit and float(used) >= float(limit))
    else:
        used = db.query(func.coalesce(func.sum(WebActivity.total_seconds), 0.0)).\
            filter(
                and_(
                    WebActivity.start_time >= start,
                    WebActivity.start_time <= end,
                    func.lower(WebActivity.domain).like(f"%{pattern.lower()}%")
                )
            ).scalar() or 0.0
        over = bool(limit and float(used) >= float(limit))

    return LimitStatusResponse(
        item_type=item_type,
        pattern=pattern,
        used_today_seconds=float(used),
        limit_seconds=limit,
        over_limit=over,
    )


# Statistics endpoints
@app.get("/stats/daily")
def get_daily_stats(date: Optional[str] = None, db: Session = Depends(get_db)):
    """Get daily statistics."""
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        target_date = datetime.now().date()
    
    start_time = datetime.combine(target_date, datetime.min.time())
    end_time = datetime.combine(target_date, datetime.max.time())
    
    # App usage
    app_stats = db.query(
        AppActivity.app_name,
        func.sum(AppActivity.total_seconds).label('total_time')
    ).filter(
        and_(AppActivity.start_time >= start_time, AppActivity.start_time <= end_time)
    ).group_by(AppActivity.app_name).all()
    
    # Website usage
    web_stats = db.query(
        WebActivity.domain,
        func.sum(WebActivity.total_seconds).label('total_time')
    ).filter(
        and_(WebActivity.start_time >= start_time, WebActivity.start_time <= end_time)
    ).group_by(WebActivity.domain).all()
    
    return {
        "date": str(target_date),
        "app_usage": [{"app": app, "seconds": time} for app, time in app_stats],
        "web_usage": [{"domain": domain, "seconds": time} for domain, time in web_stats]
    }


@app.get("/stats/weekly")
def get_weekly_stats(db: Session = Depends(get_db)):
    """Get weekly statistics."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Total focus time
    focus_sessions = db.query(FocusSession).filter(
        and_(FocusSession.start_time >= start_date, FocusSession.completed == True)
    ).all()
    
    total_focus_minutes = sum(s.duration_minutes for s in focus_sessions)
    
    # Top apps
    top_apps = db.query(
        AppActivity.app_name,
        func.sum(AppActivity.total_seconds).label('total_time')
    ).filter(
        AppActivity.start_time >= start_date
    ).group_by(AppActivity.app_name).order_by(
        func.sum(AppActivity.total_seconds).desc()
    ).limit(5).all()
    
    return {
        "period": f"{start_date.date()} to {end_date.date()}",
        "total_focus_minutes": total_focus_minutes,
        "completed_sessions": len(focus_sessions),
        "top_apps": [{"app": app, "seconds": time} for app, time in top_apps]
    }


# Blocklist endpoints
@app.get("/blocklist")
def get_blocklist(db: Session = Depends(get_db)):
    """Get all blocked items."""
    items = db.query(BlockList).filter_by(is_active=True).all()
    return {
        "apps": [{"id": i.id, "name": i.name, "pattern": i.pattern, "category": i.category}
                 for i in items if i.item_type == "app"],
        "websites": [{"id": i.id, "name": i.name, "pattern": i.pattern, "category": i.category}
                     for i in items if i.item_type == "website"]
    }


@app.post("/blocklist")
def add_to_blocklist(item: BlockListItem, db: Session = Depends(get_db)):
    """Add item to blocklist."""
    block_item = BlockList(
        item_type=item.item_type,
        name=item.name,
        pattern=item.pattern,
        category=item.category
    )
    db.add(block_item)
    db.commit()
    return {"status": "success", "id": block_item.id}


@app.delete("/blocklist/{item_id}")
def remove_from_blocklist(item_id: int, db: Session = Depends(get_db)):
    """Remove item from blocklist."""
    item = db.query(BlockList).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.is_active = False
    db.commit()
    return {"status": "success"}


# Schedule endpoints
@app.get("/schedules")
def get_schedules(db: Session = Depends(get_db)):
    """Get all schedules."""
    schedules = db.query(Schedule).filter_by(is_active=True).all()
    return {
        "schedules": [
            {
                "id": s.id,
                "name": s.name,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "days_of_week": s.days_of_week,
                "blocked_apps": json.loads(s.blocked_apps) if s.blocked_apps else [],
                "blocked_websites": json.loads(s.blocked_websites) if s.blocked_websites else []
            }
            for s in schedules
        ]
    }


@app.post("/schedules")
def create_schedule(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    """Create a new schedule."""
    sched = Schedule(
        name=schedule.name,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        days_of_week=schedule.days_of_week,
        blocked_apps=json.dumps(schedule.blocked_apps),
        blocked_websites=json.dumps(schedule.blocked_websites),
        is_active=True
    )
    db.add(sched)
    db.commit()
    
    # Add to scheduler if available
    if scheduler_service:
        scheduler_service.add_schedule(
            schedule_id=sched.id,
            name=schedule.name,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            days=schedule.days_of_week,
            blocked_apps=schedule.blocked_apps,
            blocked_websites=schedule.blocked_websites
        )
    
    return {"status": "success", "id": sched.id}


@app.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a schedule."""
    sched = db.query(Schedule).filter_by(id=schedule_id).first()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    sched.is_active = False
    db.commit()
    
    # Remove from scheduler
    if scheduler_service:
        scheduler_service.remove_schedule(schedule_id)
    
    return {"status": "success"}


def set_services(blocker, scheduler, limits: TimeLimitService | None = None):
    """Set global service instances."""
    global blocker_service, scheduler_service, limits_service
    blocker_service = blocker
    scheduler_service = scheduler
    limits_service = limits


def start():
    """Start the API server."""
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
