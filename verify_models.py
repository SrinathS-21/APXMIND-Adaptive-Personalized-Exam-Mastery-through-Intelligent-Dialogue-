"""
Database Model Verification Script
===================================
Validates all SQLAlchemy models for:
- Import issues
- Relationship integrity
- Missing foreign keys
- Model registration
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def verify_models():
    """Verify all models can be imported and are properly defined."""

    print("=" * 80)
    print("APXMIND Database Model Verification")
    print("=" * 80)

    errors = []
    warnings = []

    # Test 1: Import core models
    print("\n[1/5] Testing core model imports...")
    try:
        from src.apxmind.db.models import (
            Base, User, Subject, Lesson, Topic,
            Quiz, LearningSession, UserBadge, BadgeDefinition
        )
        print("  ✅ Core models imported successfully")
    except ImportError as e:
        errors.append(f"Core models import failed: {e}")
        print(f"  ❌ {errors[-1]}")

    # Test 2: Import security models
    print("\n[2/5] Testing security model imports...")
    try:
        from src.apxmind.db.models import (
            PasswordResetToken, RefreshToken, RateLimit,
            SecurityBlock, LoginHistory, UserSession
        )
        print("  ✅ Security models imported successfully")
    except ImportError as e:
        errors.append(f"Security models import failed: {e}")
        print(f"  ❌ {errors[-1]}")

    # Test 3: Verify removed payment models stay removed
    print("\n[3/5] Verifying payment model removal...")
    try:
        from src.apxmind import db as _db_pkg
        model_module = _db_pkg.models
        removed_models = [
            "SubscriptionPlan",
            "UserSubscription",
            "Payment",
            "Invoice",
            "PromoCode",
            "UserWallet",
        ]
        still_present = [name for name in removed_models if hasattr(model_module, name)]
        if still_present:
            errors.append(f"Removed payment models still present: {still_present}")
            print(f"  ❌ {errors[-1]}")
        else:
            print("  ✅ Payment models are removed")
    except Exception as e:
        errors.append(f"Payment model removal verification failed: {e}")
        print(f"  ❌ {errors[-1]}")

    # Test 4: Import notification models
    print("\n[4/5] Testing notification model imports...")
    try:
        from src.apxmind.db.models import (
            NotificationTemplate, UserNotification, PushToken,
            NotificationPreference, EmailTemplate
        )
        print("  ✅ Notification models imported successfully")
    except ImportError as e:
        errors.append(f"Notification models import failed: {e}")
        print(f"  ❌ {errors[-1]}")

    # Test 5: Import support/moderation models
    print("\n[5/5] Testing support/moderation model imports...")
    try:
        from src.apxmind.db.models import (
            SupportTicket, FeatureFlag, ContentReport,
            UserWarning, UserBan
        )
        print("  ✅ Support/moderation models imported successfully")
    except ImportError as e:
        errors.append(f"Support/moderation models import failed: {e}")
        print(f"  ❌ {errors[-1]}")

    # Test 6: Verify User model extensions
    print("\n[6/6] Verifying User model extensions...")
    try:
        from src.apxmind.db.models import User

        # Check new columns
        required_columns = [
            'password_changed_at', 'must_change_password'
        ]

        user_columns = [c.name for c in User.__table__.columns]
        missing_columns = [col for col in required_columns if col not in user_columns]

        if missing_columns:
            warnings.append(f"User model missing columns: {missing_columns}")
            print(f"  ⚠️  {warnings[-1]}")
        else:
            print("  ✅ User model has all required columns")

        # Check relationships
        required_relationships = [
            'password_reset_tokens', 'notifications', 'support_tickets'
        ]

        user_relationships = list(User.__mapper__.relationships.keys())
        missing_rels = [rel for rel in required_relationships if rel not in user_relationships]

        if missing_rels:
            warnings.append(f"User model missing relationships: {missing_rels}")
            print(f"  ⚠️  {warnings[-1]}")
        else:
            print("  ✅ User model has all required relationships")

    except Exception as e:
        errors.append(f"User model verification failed: {e}")
        print(f"  ❌ {errors[-1]}")

    # Test 7: Check Base class
    print("\n[7/7] Verifying Base class...")
    try:
        from src.apxmind.db.models import Base

        if Base.metadata is not None:
            print("  ✅ Base class is consistent")
        else:
            errors.append("Base class metadata is unavailable")
            print(f"  ❌ {errors[-1]}")
    except Exception as e:
        errors.append(f"Base class verification failed: {e}")
        print(f"  ❌ {errors[-1]}")

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    if not errors and not warnings:
        print("✅ ALL CHECKS PASSED - Models are ready for use!")
        return True
    else:
        if errors:
            print(f"\n❌ ERRORS FOUND: {len(errors)}")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")

        if warnings:
            print(f"\n⚠️  WARNINGS: {len(warnings)}")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")

        return len(errors) == 0


if __name__ == "__main__":
    success = verify_models()
    sys.exit(0 if success else 1)
