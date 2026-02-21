from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.db import Base, engine
from app.deps import get_current_user, get_db
from app.models import Session, Tag, User
from app.schemas import AuthIn, SessionCreate, SessionUpdate, TagCreate, TokenOut
from app.security import create_access_token, hash_password, verify_password

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Learning Streak API", version="1.0.0")


def _compute_streaks(days_with_sessions: set[date]) -> tuple[int, int]:
    if not days_with_sessions:
        return 0, 0

    today = datetime.now(timezone.utc).date()
    current = 0
    d = today
    while d in days_with_sessions:
        current += 1
        d = d - timedelta(days=1)

    longest = 0
    for day in sorted(days_with_sessions):
        prev = day - timedelta(days=1)
        if prev in days_with_sessions:
            continue
        run = 1
        nxt = day + timedelta(days=1)
        while nxt in days_with_sessions:
            run += 1
            nxt = nxt + timedelta(days=1)
        longest = max(longest, run)

    return current, longest


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/auth/register", response_model=TokenOut)
def register(payload: AuthIn, db: DBSession = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"accessToken": create_access_token(str(user.id))}


@app.post("/auth/login", response_model=TokenOut)
def login(payload: AuthIn, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"accessToken": create_access_token(str(user.id))}


@app.post("/tags")
def create_tag(payload: TagCreate, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    existing = db.query(Tag).filter(Tag.user_id == user.id, Tag.name == payload.name.strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tag already exists")
    tag = Tag(user_id=user.id, name=payload.name.strip(), color=payload.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return {"id": str(tag.id), "name": tag.name, "color": tag.color, "createdAt": tag.created_at}


@app.get("/tags")
def list_tags(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    tags = db.query(Tag).filter(Tag.user_id == user.id).order_by(Tag.created_at.desc()).all()
    return [{"id": str(t.id), "name": t.name, "color": t.color, "createdAt": t.created_at} for t in tags]


@app.post("/sessions")
def create_session(payload: SessionCreate, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if payload.tagId is not None:
        tag = db.query(Tag).filter(Tag.id == payload.tagId, Tag.user_id == user.id).first()
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

    row = Session(
        user_id=user.id,
        tag_id=payload.tagId,
        session_date=payload.sessionDate,
        duration_min=payload.durationMin,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": str(row.id),
        "tagId": str(row.tag_id) if row.tag_id else None,
        "sessionDate": row.session_date,
        "durationMin": row.duration_min,
        "notes": row.notes,
        "createdAt": row.created_at,
    }


@app.get("/sessions")
def list_sessions(
    startDate: date | None = Query(default=None),
    endDate: date | None = Query(default=None),
    tagId: UUID | None = Query(default=None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    q = db.query(Session).filter(Session.user_id == user.id)
    if startDate is not None:
        q = q.filter(Session.session_date >= startDate)
    if endDate is not None:
        q = q.filter(Session.session_date <= endDate)
    if tagId is not None:
        q = q.filter(Session.tag_id == tagId)

    rows = q.order_by(Session.session_date.desc(), Session.created_at.desc()).offset(offset).limit(limit).all()

    return [{
        "id": str(r.id),
        "tagId": str(r.tag_id) if r.tag_id else None,
        "sessionDate": r.session_date,
        "durationMin": r.duration_min,
        "notes": r.notes,
        "createdAt": r.created_at,
    } for r in rows]


@app.patch("/sessions/{session_id}")
def update_session(session_id: UUID, payload: SessionUpdate, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    row = db.query(Session).filter(Session.id == session_id, Session.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    if payload.tagId is not None:
        tag = db.query(Tag).filter(Tag.id == payload.tagId, Tag.user_id == user.id).first()
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        row.tag_id = payload.tagId

    if payload.sessionDate is not None:
        row.session_date = payload.sessionDate
    if payload.durationMin is not None:
        row.duration_min = payload.durationMin
    if payload.notes is not None:
        row.notes = payload.notes

    db.commit()
    db.refresh(row)
    return {
        "id": str(row.id),
        "tagId": str(row.tag_id) if row.tag_id else None,
        "sessionDate": row.session_date,
        "durationMin": row.duration_min,
        "notes": row.notes,
        "createdAt": row.created_at,
    }


@app.delete("/sessions/{session_id}")
def delete_session(session_id: UUID, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    row = db.query(Session).filter(Session.id == session_id, Session.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get("/streak")
def streak(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    days = db.query(Session.session_date).filter(Session.user_id == user.id).distinct().all()
    day_set = {d[0] for d in days}
    current, longest = _compute_streaks(day_set)
    return {"currentStreak": current, "longestStreak": longest}


@app.get("/analytics/heatmap")
def heatmap(
    range: str = Query("90d"),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if not range.endswith("d"):
        raise HTTPException(status_code=400, detail="range must be Nd")
    try:
        days = int(range[:-1])
    except ValueError:
        raise HTTPException(status_code=400, detail="range must be Nd")
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="range must be 1..365d")

    start = datetime.now(timezone.utc).date() - timedelta(days=days - 1)

    rows = (
        db.query(Session.session_date, func.coalesce(func.sum(Session.duration_min), 0))
        .filter(Session.user_id == user.id, Session.session_date >= start)
        .group_by(Session.session_date)
        .order_by(Session.session_date)
        .all()
    )

    return {
        "range": range,
        "dailyMinutes": [{"day": r[0].isoformat(), "minutes": int(r[1])} for r in rows],
    }
