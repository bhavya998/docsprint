"""Usage endpoints — page usage tracking and quota information."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from docsprint.api.schemas import UsageHistoryResponse, UsageResponse
from docsprint.core.dependencies import get_current_user, get_db
from docsprint.models.user import User
from docsprint.services.usage_service import (
    get_current_usage,
    get_plan_pages_limit,
    get_usage_history,
)

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("", response_model=UsageResponse)
def get_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageResponse:
    """Get current usage stats and plan limits for the authenticated user.

    Args:
        current_user: Authenticated user.
        db: Database session.

    Returns:
        UsageResponse with plan, pages_used, pages_limit, and period string.
    """
    now = datetime.now(timezone.utc)
    pages_used = get_current_usage(db, current_user.id)
    pages_limit = get_plan_pages_limit(current_user.plan)
    period = f"{now.year}-{now.month:02d}"

    return UsageResponse(
        plan=current_user.plan,
        pages_used=pages_used,
        pages_limit=pages_limit,
        period=period,
    )


@router.get("/history", response_model=UsageHistoryResponse)
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageHistoryResponse:
    """Get full usage history for the authenticated user.

    Args:
        current_user: Authenticated user.
        db: Database session.

    Returns:
        UsageHistoryResponse with all monthly records.
    """
    records = get_usage_history(db, current_user.id)
    return UsageHistoryResponse(
        records=[
            {
                "month": r.month,
                "year": r.year,
                "pages_processed": r.pages_processed,
            }
            for r in records
        ],
        total=len(records),
    )