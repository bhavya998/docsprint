"""Usage service — track page usage, check quotas, get plan limits."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from docsprint.config import settings
from docsprint.models.usage import UsageRecord
from docsprint.models.user import User


def get_plan_pages_limit(plan: str) -> int:
    """Get the monthly page limit for a given plan.

    Args:
        plan: Plan tier name ("free", "starter", "pro").

    Returns:
        Maximum pages per month for this plan.
    """
    limits = {
        "free": settings.FREE_TIER_PAGES,
        "starter": settings.STARTER_PAGES,
        "pro": settings.PRO_PAGES,
    }
    return limits.get(plan, settings.FREE_TIER_PAGES)


def get_current_usage(db: Session, user_id: int, month: int | None = None, year: int | None = None) -> int:
    """Get the number of pages processed this month for a user.

    Args:
        db: Database session.
        user_id: The user's ID.
        month: Month (1-12). Defaults to current month.
        year: Year. Defaults to current year.

    Returns:
        Number of pages processed this period.
    """
    now = datetime.now(timezone.utc)
    m = month or now.month
    y = year or now.year

    record = (
        db.query(UsageRecord)
        .filter(
            UsageRecord.user_id == user_id,
            UsageRecord.month == m,
            UsageRecord.year == y,
        )
        .first()
    )
    return record.pages_processed if record else 0


def check_quota(db: Session, user: User, additional_pages: int = 0) -> bool:
    """Check if a user has remaining quota for processing.

    Args:
        db: Database session.
        user: The User model instance.
        additional_pages: Pages to be added if check passes.

    Returns:
        True if the user is within quota, False otherwise.
    """
    limit = get_plan_pages_limit(user.plan)
    used = get_current_usage(db, user.id)
    return (used + additional_pages) <= limit


def increment_usage(db: Session, user_id: int, pages: int, month: int | None = None, year: int | None = None) -> UsageRecord:
    """Increment page usage for a user in the current period.

    Creates a new UsageRecord if one doesn't exist for this period,
    otherwise increments the existing one.

    Args:
        db: Database session.
        user_id: The user's ID.
        pages: Number of pages to add.
        month: Month (1-12). Defaults to current month.
        year: Year. Defaults to current year.

    Returns:
        The updated UsageRecord.
    """
    now = datetime.now(timezone.utc)
    m = month or now.month
    y = year or now.year

    record = (
        db.query(UsageRecord)
        .filter(
            UsageRecord.user_id == user_id,
            UsageRecord.month == m,
            UsageRecord.year == y,
        )
        .first()
    )

    if record:
        record.pages_processed += pages
    else:
        record = UsageRecord(
            user_id=user_id,
            pages_processed=pages,
            month=m,
            year=y,
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


def get_usage_history(db: Session, user_id: int) -> list[UsageRecord]:
    """Get full usage history for a user.

    Args:
        db: Database session.
        user_id: The user's ID.

    Returns:
        List of UsageRecord instances ordered by date descending.
    """
    return (
        db.query(UsageRecord)
        .filter(UsageRecord.user_id == user_id)
        .order_by(UsageRecord.year.desc(), UsageRecord.month.desc())
        .all()
    )