"""
Sync Router
===========

Reliable batch sync APIs with per-operation idempotency.

POST /api/sync/batch
GET  /api/sync/status
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    SyncBatchRequest,
    SyncBatchResponse,
    SyncBatchResultItemOut,
    SyncStatusResponse,
)
from ...db.models import SyncJournal, User
from ...db.session import get_db

router = APIRouter()


@router.post("/batch", response_model=SyncBatchResponse)
async def sync_batch(
    request: SyncBatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()

    accepted_count = 0
    duplicate_count = 0
    failed_count = 0
    results: list[SyncBatchResultItemOut] = []

    batch_keys: set[str] = set()

    for operation in request.operations:
        key = operation.idempotency_key.strip()

        if key in batch_keys:
            duplicate_count += 1
            results.append(
                SyncBatchResultItemOut(
                    idempotency_key=key,
                    status="duplicate",
                    retryable=False,
                    message="Duplicate idempotency_key in current batch",
                )
            )
            continue
        batch_keys.add(key)

        existing_result = await db.execute(
            select(SyncJournal).where(SyncJournal.idempotency_key == key)
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            if existing.user_id == user.id:
                existing.attempt_count = (existing.attempt_count or 0) + 1
                existing.last_attempt_at = now
                duplicate_count += 1
                results.append(
                    SyncBatchResultItemOut(
                        idempotency_key=key,
                        status="duplicate",
                        journal_id=existing.id,
                        attempt_count=existing.attempt_count,
                        retryable=existing.status == "failed",
                        message="Already processed",
                    )
                )
            else:
                failed_count += 1
                results.append(
                    SyncBatchResultItemOut(
                        idempotency_key=key,
                        status="failed",
                        retryable=False,
                        message="idempotency_key is already used by another user",
                    )
                )
            continue

        journal_row = SyncJournal(
            user_id=user.id,
            operation_type=operation.operation_type,
            entity_type=operation.entity_type,
            entity_id=operation.entity_id,
            payload=operation.payload,
            idempotency_key=key,
            attempt_count=1,
            last_attempt_at=now,
            synced_at=now,
            status="synced",
        )

        try:
            async with db.begin_nested():
                db.add(journal_row)
                await db.flush()
        except IntegrityError:
            existing_result = await db.execute(
                select(SyncJournal).where(SyncJournal.idempotency_key == key)
            )
            race_existing = existing_result.scalar_one_or_none()
            if race_existing and race_existing.user_id == user.id:
                race_existing.attempt_count = (race_existing.attempt_count or 0) + 1
                race_existing.last_attempt_at = now
                duplicate_count += 1
                results.append(
                    SyncBatchResultItemOut(
                        idempotency_key=key,
                        status="duplicate",
                        journal_id=race_existing.id,
                        attempt_count=race_existing.attempt_count,
                        retryable=race_existing.status == "failed",
                        message="Already processed",
                    )
                )
            else:
                failed_count += 1
                results.append(
                    SyncBatchResultItemOut(
                        idempotency_key=key,
                        status="failed",
                        retryable=True,
                        message="Write conflict while recording sync operation",
                    )
                )
            continue

        accepted_count += 1
        results.append(
            SyncBatchResultItemOut(
                idempotency_key=key,
                status="accepted",
                journal_id=journal_row.id,
                attempt_count=journal_row.attempt_count,
                retryable=False,
            )
        )

    await db.commit()

    return SyncBatchResponse(
        accepted_count=accepted_count,
        duplicate_count=duplicate_count,
        failed_count=failed_count,
        results=results,
    )


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(
        select(SyncJournal.status, func.count(SyncJournal.id))
        .where(SyncJournal.user_id == user.id)
        .group_by(SyncJournal.status)
    )

    counts = {status: int(count) for status, count in count_result.all()}
    pending_count = counts.get("pending", 0)
    synced_count = counts.get("synced", 0)
    failed_count = counts.get("failed", 0)
    total_count = pending_count + synced_count + failed_count

    latest_synced_result = await db.execute(
        select(func.max(SyncJournal.synced_at)).where(SyncJournal.user_id == user.id)
    )
    latest_synced_at = latest_synced_result.scalar_one_or_none()

    return SyncStatusResponse(
        pending_count=pending_count,
        synced_count=synced_count,
        failed_count=failed_count,
        total_count=total_count,
        backlog_count=pending_count + failed_count,
        latest_synced_at=latest_synced_at.isoformat() if latest_synced_at else None,
    )
