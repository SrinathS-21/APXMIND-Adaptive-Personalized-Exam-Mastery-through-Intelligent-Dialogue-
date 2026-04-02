"""
APXMIND Account Demo Seed
=========================

Seeds demo data for account-related features:
- Notifications settings/preferences
- Sample user notifications
- Sample security events
- Sample user sessions (best effort)

Usage:
    python -m scripts.seed_account_demo_data
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.apxmind.core.config import Settings
from src.apxmind.db import session as db_session
from src.apxmind.db.models import (
    NotificationPreference,
    NotificationSetting,
    SecurityEvent,
    User,
    UserNotification,
    UserSession,
)


async def seed_for_user(session, user: User):
    print(f"\nSeeding account demo data for user #{user.id} ({user.email})")

    settings = await session.execute(
        select(NotificationSetting).where(NotificationSetting.user_id == user.id)
    )
    if not settings.scalar_one_or_none():
        session.add(
            NotificationSetting(
                user_id=user.id,
                all_notifications_enabled=True,
                push_enabled=True,
                email_enabled=True,
                sms_enabled=False,
            )
        )
        print("  + Notification settings created")

    categories = ["study", "quiz", "account", "security"]
    for category in categories:
        pref = await session.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user.id,
                NotificationPreference.category == category,
            )
        )
        if pref.scalar_one_or_none():
            continue

        session.add(
            NotificationPreference(
                user_id=user.id,
                category=category,
                in_app=True,
                push=True,
                email=category in {"account", "security"},
                sms=False,
            )
        )
    print("  + Notification preferences ensured")

    notifications_result = await session.execute(
        select(UserNotification).where(UserNotification.user_id == user.id).limit(1)
    )
    if not notifications_result.scalar_one_or_none():
        now = datetime.utcnow()
        session.add_all(
            [
                UserNotification(
                    user_id=user.id,
                    title="Welcome to APXMIND Notifications",
                    body="You will now receive study reminders and progress updates.",
                    category="study",
                    priority="normal",
                    is_read=False,
                    is_seen=False,
                    created_at=now,
                ),
                UserNotification(
                    user_id=user.id,
                    title="Weekly Progress Ready",
                    body="Your weekly progress report is available in dashboard insights.",
                    category="quiz",
                    priority="normal",
                    is_read=False,
                    is_seen=False,
                    created_at=now - timedelta(hours=4),
                ),
                UserNotification(
                    user_id=user.id,
                    title="Account Safety Tip",
                    body="Review active sessions in Security Center regularly.",
                    category="account",
                    priority="high",
                    is_read=True,
                    read_at=now - timedelta(hours=2),
                    is_seen=True,
                    seen_at=now - timedelta(hours=2),
                    created_at=now - timedelta(days=1),
                ),
            ]
        )
        print("  + Sample notifications created")

    events_result = await session.execute(
        select(SecurityEvent).where(SecurityEvent.user_id == user.id).limit(1)
    )
    if not events_result.scalar_one_or_none():
        now = datetime.utcnow()
        session.add_all(
            [
                SecurityEvent(
                    user_id=user.id,
                    event_type="login_success",
                    severity="info",
                    description="Successful login from known device",
                    ip_address="127.0.0.1",
                    created_at=now - timedelta(hours=1),
                ),
                SecurityEvent(
                    user_id=user.id,
                    event_type="password_change_reminder",
                    severity="warning",
                    description="Password has not been changed in the last 90 days",
                    ip_address="127.0.0.1",
                    created_at=now - timedelta(days=2),
                ),
            ]
        )
        print("  + Sample security events created")

    try:
        sessions_result = await session.execute(
            select(UserSession).where(UserSession.user_id == user.id).limit(1)
        )
        if not sessions_result.scalar_one_or_none():
            now = datetime.utcnow()
            session.add(
                UserSession(
                    user_id=user.id,
                    device_id=None,
                    ip_address="127.0.0.1",
                    user_agent="APXMIND Demo Session",
                    location="Localhost",
                    is_revoked=False,
                    expires_at=now + timedelta(days=14),
                    last_activity=now,
                    created_at=now,
                )
            )
            print("  + Sample session created")
    except SQLAlchemyError:
        print("  ! Skipped session seed (user_sessions table/columns unavailable)")


async def seed_account_demo_data():
    settings = Settings()
    db_session.init_db_engine(settings)
    await db_session.create_tables()

    async with db_session._async_session_factory() as session:
        users_result = await session.execute(select(User).order_by(User.id.asc()).limit(5))
        users = users_result.scalars().all()

        if not users:
            print("\nNo users found. Create at least one user, then run this script again.")
            await session.commit()
            return

        for user in users:
            await seed_for_user(session, user)

        await session.commit()
        print("\n✅ Account demo data seeding completed.")


def main():
    print("\n" + "=" * 56)
    print(" APXMIND — Account Demo Seed")
    print("=" * 56)
    asyncio.run(seed_account_demo_data())


if __name__ == "__main__":
    main()
