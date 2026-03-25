"""
Payments Router
================

Subscription plans, checkout, verification, and billing endpoints.
"""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...db.models import (
    Invoice,
    Payment,
    PromoCode,
    PromoRedemption,
    SubscriptionPlan,
    User,
    UserSubscription,
    UserWallet,
    WalletTransaction,
)
from ...db.session import get_db

router = APIRouter()


@router.get("/plans")
async def list_plans(
    include_inactive: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order.asc(), SubscriptionPlan.price_inr.asc())
    if not include_inactive:
        stmt = stmt.where(SubscriptionPlan.is_active.is_(True))

    result = await db.execute(stmt)
    plans = result.scalars().all()

    return {
        "success": True,
        "plans": [
            {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
                "price_inr": p.price_inr,
                "original_price_inr": p.original_price_inr,
                "billing_period": p.billing_period,
                "duration_days": p.duration_days,
                "features": p.features,
                "is_featured": p.is_featured,
                "badge_text": p.badge_text,
            }
            for p in plans
        ],
    }


@router.get("/subscriptions/current")
async def get_current_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSubscription)
        .where(UserSubscription.user_id == user.id)
        .order_by(UserSubscription.created_at.desc())
    )
    subscription = result.scalars().first()

    if not subscription:
        return {"success": True, "subscription": None}

    return {
        "success": True,
        "subscription": {
            "id": subscription.id,
            "plan_id": subscription.plan_id,
            "status": subscription.status,
            "started_at": subscription.started_at.isoformat() if subscription.started_at else None,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "auto_renew": subscription.auto_renew,
            "payment_method": subscription.payment_method,
        },
    }


@router.post("/checkout")
async def create_checkout(
    plan_id: str = Body(...),
    payment_method: str = Body(default="razorpay"),
    promo_code: str | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plan not found or inactive")

    amount = int(plan.price_inr)
    discount_amount = 0
    promo = None

    if promo_code:
        promo_result = await db.execute(select(PromoCode).where(PromoCode.code == promo_code, PromoCode.is_active.is_(True)))
        promo = promo_result.scalar_one_or_none()
        if not promo:
            raise HTTPException(status_code=400, detail="Invalid promo code")

        if promo.discount_type == "percentage":
            discount_amount = (amount * promo.discount_value) // 100
            if promo.max_discount:
                discount_amount = min(discount_amount, promo.max_discount)
        else:
            discount_amount = min(amount, promo.discount_value)

    final_amount = max(0, amount - discount_amount)

    if payment_method in {"manual", "demo", "test"}:
        discount_amount = amount
        final_amount = 0
    now = datetime.utcnow()

    subscription = UserSubscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        plan_id=plan.id,
        status="pending",
        started_at=now,
        expires_at=now + timedelta(days=max(1, plan.duration_days or 30)),
        payment_method=payment_method,
        promo_code_used=promo_code,
    )
    db.add(subscription)

    payment = Payment(
        id=str(uuid.uuid4()),
        user_id=user.id,
        subscription_id=subscription.id,
        amount=amount,
        discount_amount=discount_amount,
        tax_amount=0,
        final_amount=final_amount,
        status="pending",
        payment_method=payment_method,
        gateway="razorpay",
        gateway_order_id=f"order_{uuid.uuid4().hex[:16]}",
    )
    db.add(payment)
    await db.flush()

    if promo:
        db.add(
            PromoRedemption(
                promo_id=promo.id,
                user_id=user.id,
                payment_id=payment.id,
                original_amount=amount,
                discount_applied=discount_amount,
                final_amount=final_amount,
            )
        )

    await db.commit()

    return {
        "success": True,
        "checkout": {
            "payment_id": payment.id,
            "subscription_id": subscription.id,
            "gateway": payment.gateway,
            "gateway_order_id": payment.gateway_order_id,
            "amount": amount,
            "discount_amount": discount_amount,
            "final_amount": final_amount,
            "currency": payment.currency,
        },
    }


@router.post("/verify")
async def verify_payment(
    payment_id: str = Body(...),
    gateway_payment_id: str | None = Body(default=None),
    gateway_signature: str | None = Body(default=None),
    status_value: str = Body(default="completed"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Payment).where(Payment.id == payment_id, Payment.user_id == user.id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.status = status_value
    payment.gateway_payment_id = gateway_payment_id
    payment.gateway_signature = gateway_signature
    payment.completed_at = datetime.utcnow() if status_value == "completed" else None

    sub = None
    if payment.subscription_id:
        sub_result = await db.execute(select(UserSubscription).where(UserSubscription.id == payment.subscription_id))
        sub = sub_result.scalar_one_or_none()

    if status_value == "completed":
        if sub:
            sub.status = "active"
            sub.started_at = datetime.utcnow()
            user.subscription_status = "active"
            user.subscription_expires_at = sub.expires_at
            user.lifetime_value_inr = int(user.lifetime_value_inr or 0) + int(payment.final_amount or 0)

        invoice = Invoice(
            id=str(uuid.uuid4()),
            user_id=user.id,
            payment_id=payment.id,
            invoice_number=f"APX-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            fiscal_year=f"{datetime.utcnow().year}-{str(datetime.utcnow().year + 1)[-2:]}",
            subtotal=payment.amount,
            discount_amount=payment.discount_amount or 0,
            taxable_amount=payment.final_amount,
            total_amount=payment.final_amount,
            billing_name=user.name,
            billing_email=user.email,
            status="paid",
            invoice_date=datetime.utcnow().date(),
            paid_at=datetime.utcnow(),
        )
        db.add(invoice)

    await db.commit()

    return {
        "success": True,
        "payment": {
            "id": payment.id,
            "status": payment.status,
            "gateway_payment_id": payment.gateway_payment_id,
            "completed_at": payment.completed_at.isoformat() if payment.completed_at else None,
        },
        "subscription": {
            "id": sub.id,
            "status": sub.status,
        } if sub else None,
    }


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: str,
    payload: dict | str | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reason: str | None = None
    if isinstance(payload, str):
        reason = payload
    elif isinstance(payload, dict):
        value = payload.get("reason")
        if isinstance(value, str):
            reason = value

    result = await db.execute(
        select(UserSubscription).where(UserSubscription.id == subscription_id, UserSubscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    subscription.status = "cancelled"
    subscription.cancelled_at = datetime.utcnow()
    subscription.cancel_reason = reason
    user.subscription_status = "cancelled"

    await db.commit()
    return {"success": True, "message": "Subscription cancelled"}


@router.get("/payments")
async def list_payments(
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
    )
    payments = result.scalars().all()

    return {
        "success": True,
        "payments": [
            {
                "id": p.id,
                "subscription_id": p.subscription_id,
                "amount": p.amount,
                "discount_amount": p.discount_amount,
                "final_amount": p.final_amount,
                "currency": p.currency,
                "status": p.status,
                "payment_method": p.payment_method,
                "gateway_order_id": p.gateway_order_id,
                "gateway_payment_id": p.gateway_payment_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "completed_at": p.completed_at.isoformat() if p.completed_at else None,
            }
            for p in payments
        ],
    }


@router.get("/invoices")
async def list_invoices(
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice)
        .where(Invoice.user_id == user.id)
        .order_by(Invoice.created_at.desc())
        .limit(limit)
    )
    invoices = result.scalars().all()

    return {
        "success": True,
        "invoices": [
            {
                "id": inv.id,
                "payment_id": inv.payment_id,
                "invoice_number": inv.invoice_number,
                "total_amount": inv.total_amount,
                "status": inv.status,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                "pdf_url": inv.pdf_url,
            }
            for inv in invoices
        ],
    }


@router.post("/promo/validate")
async def validate_promo_code(
    code: str = Body(..., embed=True),
    amount: int = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromoCode).where(PromoCode.code == code, PromoCode.is_active.is_(True)))
    promo = result.scalar_one_or_none()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")

    if promo.min_purchase and amount < promo.min_purchase:
        raise HTTPException(status_code=400, detail="Order amount does not meet promo minimum")

    if promo.discount_type == "percentage":
        discount = (amount * promo.discount_value) // 100
        if promo.max_discount:
            discount = min(discount, promo.max_discount)
    else:
        discount = min(amount, promo.discount_value)

    return {
        "success": True,
        "promo": {
            "id": promo.id,
            "code": promo.code,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value,
            "calculated_discount": discount,
            "final_amount": max(0, amount - discount),
        },
    }


@router.get("/wallet")
async def get_wallet(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserWallet).where(UserWallet.user_id == user.id))
    wallet = result.scalar_one_or_none()

    if not wallet:
        wallet = UserWallet(user_id=user.id, balance=0)
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)

    return {
        "success": True,
        "wallet": {
            "user_id": wallet.user_id,
            "balance": wallet.balance,
            "lifetime_earned": wallet.lifetime_earned,
            "lifetime_spent": wallet.lifetime_spent,
            "last_transaction_at": wallet.last_transaction_at.isoformat() if wallet.last_transaction_at else None,
            "updated_at": wallet.updated_at.isoformat() if wallet.updated_at else None,
        },
    }


@router.get("/wallet/transactions")
async def list_wallet_transactions(
    limit: int = Query(default=30, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.user_id == user.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    return {
        "success": True,
        "transactions": [
            {
                "id": row.id,
                "transaction_type": row.transaction_type,
                "amount": row.amount,
                "balance_after": row.balance_after,
                "description": row.description,
                "reference_type": row.reference_type,
                "reference_id": row.reference_id,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }
