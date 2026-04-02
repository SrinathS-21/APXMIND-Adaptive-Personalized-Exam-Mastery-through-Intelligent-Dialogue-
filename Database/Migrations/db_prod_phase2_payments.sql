-- ============================================================================
-- APXMIND Production Schema - Phase 2: Payments & Subscriptions
-- ============================================================================
-- For Indian market: Primarily Razorpay integration
-- ============================================================================

-- ============================================================================
-- 2.1 SUBSCRIPTION PLANS
-- ============================================================================
-- Define available subscription tiers

CREATE TABLE IF NOT EXISTS subscription_plans (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,      -- 'free', 'plus_monthly', 'pro_monthly', 'pro_annual', 'pro_exam_cycle'
    name VARCHAR(100) NOT NULL,            -- Internal name
    display_name VARCHAR(100) NOT NULL,    -- "Pro Plan"
    description TEXT,

-- Pricing (store in INR rupees as integer values)
price_inr INTEGER NOT NULL, -- Price in INR (example: 999 = ₹999)
price_usd INTEGER, -- Price in USD dollars (optional for international)
original_price_inr INTEGER, -- For showing "was ₹X" strikethrough

-- Duration
billing_period VARCHAR(20) NOT NULL, -- 'monthly', 'yearly', 'lifetime', 'exam_cycle'
duration_days INTEGER NOT NULL, -- 30, 90, 365, 36500

-- Features
features JSON NOT NULL, -- See example below
/*
{
"subjects": ["biology", "chemistry", "physics"],
"max_daily_queries": 100,
"mock_tests": true,
"mock_tests_per_month": 10,
"study_groups": true,
"offline_access": true,
"priority_support": false,
"ad_free": true,
"personalized_schedule": true
}
*/

-- Display
is_featured BOOLEAN DEFAULT FALSE, -- Highlight as "Most Popular"
badge_text VARCHAR(50), -- "Best Value", "Most Popular"
sort_order INTEGER DEFAULT 0,

-- Availability

is_active BOOLEAN DEFAULT TRUE,
    available_from DATETIME,
    available_until DATETIME,
    target_segments JSON,                  -- ["new_users", "returning"]

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_plan_active ON subscription_plans (is_active, sort_order);

-- ============================================================================
-- 2.2 USER SUBSCRIPTIONS
-- ============================================================================
-- Track active and historical subscriptions

CREATE TABLE IF NOT EXISTS user_subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_id VARCHAR(36) NOT NULL REFERENCES subscription_plans(id),

-- Status
status VARCHAR(20) NOT NULL DEFAULT 'active',
-- 'pending', 'active', 'cancelled', 'expired', 'paused', 'past_due'

-- Dates
started_at DATETIME NOT NULL,
expires_at DATETIME NOT NULL,
cancelled_at DATETIME,
paused_at DATETIME,
resumed_at DATETIME,

-- Cancellation
cancel_reason VARCHAR(100), -- 'too_expensive', 'not_using', 'switching_competitor'
cancel_feedback TEXT,

-- Renewal
auto_renew BOOLEAN DEFAULT TRUE,
renewal_reminder_sent BOOLEAN DEFAULT FALSE,

-- Payment
payment_method VARCHAR(30), -- 'razorpay', 'upi', 'card', 'netbanking'
razorpay_subscription_id VARCHAR(100), -- If using Razorpay subscriptions

-- Source tracking

acquired_via VARCHAR(50),              -- 'organic', 'promo_code', 'referral', 'trial_conversion'
    promo_code_used VARCHAR(50),
    referrer_id INTEGER REFERENCES users(id),

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sub_user_status ON user_subscriptions (user_id, status);

CREATE INDEX IF NOT EXISTS idx_sub_expires ON user_subscriptions (expires_at);

CREATE INDEX IF NOT EXISTS idx_sub_renewal ON user_subscriptions (auto_renew, expires_at);

-- ============================================================================
-- 2.3 PAYMENTS
-- ============================================================================
-- All payment transactions

CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    subscription_id VARCHAR(36) REFERENCES user_subscriptions(id),

-- Amount
amount INTEGER NOT NULL, -- In INR rupees
currency VARCHAR(3) NOT NULL DEFAULT 'INR',
tax_amount INTEGER DEFAULT 0, -- GST
discount_amount INTEGER DEFAULT 0, -- Promo discount
final_amount INTEGER NOT NULL, -- amount + tax - discount

-- Status
status VARCHAR(20) NOT NULL,
-- 'pending', 'processing', 'completed', 'failed', 'refunded', 'partially_refunded'

-- Payment Method
payment_method VARCHAR(30) NOT NULL, -- 'upi', 'card', 'netbanking', 'wallet'
payment_method_details JSON, -- {"upi_id": "user@paytm", "card_last4": "1234"}

-- Gateway (Razorpay)
gateway VARCHAR(30) NOT NULL DEFAULT 'razorpay',
gateway_order_id VARCHAR(100), -- Razorpay order_id
gateway_payment_id VARCHAR(100), -- Razorpay payment_id
gateway_signature VARCHAR(512), -- For verification
gateway_response JSON, -- Full gateway response

-- Failure
failure_code VARCHAR(50),
failure_reason TEXT,
retry_count INTEGER DEFAULT 0,

-- Refund
refund_amount INTEGER,
refund_reason TEXT,
refund_gateway_id VARCHAR(100),
refunded_at DATETIME,

-- Metadata
ip_address VARCHAR(45),
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_payment_user ON payments (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_payment_status ON payments (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_payment_gateway ON payments (gateway_payment_id);

CREATE INDEX IF NOT EXISTS idx_payment_order ON payments (gateway_order_id);

-- ============================================================================
-- 2.4 INVOICES
-- ============================================================================
-- Tax-compliant invoices for payments

CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    payment_id VARCHAR(36) REFERENCES payments(id),

-- Invoice Number (e.g., APX/2026/03/0001)
invoice_number VARCHAR(50) UNIQUE NOT NULL,
fiscal_year VARCHAR(10) NOT NULL, -- '2025-26'

-- Amounts
subtotal INTEGER NOT NULL, -- In INR rupees
discount_amount INTEGER DEFAULT 0,
taxable_amount INTEGER NOT NULL,
cgst_percent NUMERIC(5, 2) DEFAULT 9, -- 9% CGST
cgst_amount INTEGER DEFAULT 0,
sgst_percent NUMERIC(5, 2) DEFAULT 9, -- 9% SGST
sgst_amount INTEGER DEFAULT 0,
igst_percent NUMERIC(5, 2), -- 18% IGST (for inter-state)
igst_amount INTEGER DEFAULT 0,
total_amount INTEGER NOT NULL,

-- Billing Details
billing_name VARCHAR(100) NOT NULL,
billing_email VARCHAR(120),
billing_phone VARCHAR(20),
billing_address_line1 VARCHAR(255),
billing_address_line2 VARCHAR(255),
billing_city VARCHAR(100),
billing_state VARCHAR(50),
billing_pincode VARCHAR(10),
billing_country VARCHAR(50) DEFAULT 'India',
billing_gst VARCHAR(20), -- Customer GST number (optional)

-- Seller Details
seller_name VARCHAR(100) DEFAULT 'ApxMind EdTech Pvt Ltd',
seller_gst VARCHAR(20),
seller_pan VARCHAR(20),
seller_address TEXT,

-- Status
status VARCHAR(20) DEFAULT 'draft', -- 'draft', 'issued', 'paid', 'cancelled'
invoice_date DATE NOT NULL,
due_date DATE,
paid_at DATETIME,

-- PDF
pdf_generated BOOLEAN DEFAULT FALSE, pdf_url TEXT,

-- Notes
notes TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP );

CREATE INDEX IF NOT EXISTS idx_invoice_user ON invoices (user_id, invoice_date DESC);

CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoices (invoice_number);

CREATE INDEX IF NOT EXISTS idx_invoice_fiscal ON invoices (fiscal_year);

-- ============================================================================
-- 2.5 PROMO CODES
-- ============================================================================
-- Discount codes and coupons

CREATE TABLE IF NOT EXISTS promo_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) UNIQUE NOT NULL,      -- 'NEET2026', 'FIRST50'

-- Description
name VARCHAR(100) NOT NULL, -- Internal name
description TEXT,
display_text VARCHAR(100), -- "Get 50% off!"

-- Discount
discount_type VARCHAR(20) NOT NULL, -- 'percentage', 'fixed'
discount_value INTEGER NOT NULL, -- 50 (percent) or 500 (INR)
max_discount INTEGER, -- Max discount in INR (for percentage)
min_purchase INTEGER, -- Minimum order amount in INR

-- Applicability
applicable_plans JSON, -- NULL = all plans, or ["plan_id_1", "plan_id_2"]
applicable_users JSON, -- NULL = all, or specific user segments
first_purchase_only BOOLEAN DEFAULT FALSE,

-- Limits
max_total_uses INTEGER, -- Total redemptions allowed
max_uses_per_user INTEGER DEFAULT 1, -- Per user limit
current_uses INTEGER DEFAULT 0,

-- Validity
valid_from DATETIME,
valid_until DATETIME,
is_active BOOLEAN DEFAULT TRUE,

-- Metadata
campaign_name VARCHAR(100),            -- Marketing campaign tracking
    created_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_promo_code ON promo_codes (code, is_active);

CREATE INDEX IF NOT EXISTS idx_promo_validity ON promo_codes (
    valid_from,
    valid_until,
    is_active
);

-- ============================================================================
-- 2.6 PROMO REDEMPTIONS
-- ============================================================================
-- Track who used which promo code

CREATE TABLE IF NOT EXISTS promo_redemptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    promo_id INTEGER NOT NULL REFERENCES promo_codes (id),
    user_id INTEGER NOT NULL REFERENCES users (id),
    payment_id VARCHAR(36) REFERENCES payments (id),
    original_amount INTEGER NOT NULL, -- Amount before discount
    discount_applied INTEGER NOT NULL, -- Discount given in INR
    final_amount INTEGER NOT NULL, -- Amount after discount
    redeemed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (promo_id, user_id, payment_id)
);

CREATE INDEX IF NOT EXISTS idx_redemption_user ON promo_redemptions (user_id);

CREATE INDEX IF NOT EXISTS idx_redemption_promo ON promo_redemptions (promo_id);

-- ============================================================================
-- 2.7 REFERRAL PROGRAM
-- ============================================================================
-- Track referrals and rewards

CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL REFERENCES users(id),
    referee_id INTEGER NOT NULL REFERENCES users(id),

-- Status
status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'qualified', 'rewarded', 'invalid'

-- Qualification (referee must subscribe)
qualified_at DATETIME,
qualifying_payment_id VARCHAR(36) REFERENCES payments (id),

-- Rewards

referrer_reward_type VARCHAR(20),      -- 'discount', 'credits', 'extension'
    referrer_reward_value INTEGER,         -- INR or days
    referrer_reward_applied BOOLEAN DEFAULT FALSE,
    referrer_rewarded_at DATETIME,

    referee_reward_type VARCHAR(20),
    referee_reward_value INTEGER,
    referee_reward_applied BOOLEAN DEFAULT FALSE,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(referrer_id, referee_id)
);

CREATE INDEX IF NOT EXISTS idx_referral_referrer ON referrals (referrer_id, status);

CREATE INDEX IF NOT EXISTS idx_referral_referee ON referrals (referee_id);

-- ============================================================================
-- 2.8 USER CREDITS / WALLET
-- ============================================================================
-- Virtual wallet for rewards, refunds, etc.

CREATE TABLE IF NOT EXISTS user_wallet (
    user_id INTEGER PRIMARY KEY REFERENCES users (id),
    balance INTEGER NOT NULL DEFAULT 0, -- In INR
    lifetime_earned INTEGER DEFAULT 0,
    lifetime_spent INTEGER DEFAULT 0,
    last_transaction_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wallet_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id),
    transaction_type VARCHAR(30) NOT NULL,
    -- 'credit_referral', 'credit_refund', 'credit_promo', 'debit_purchase', 'debit_expired'
    amount INTEGER NOT NULL, -- Positive for credit, negative for debit
    balance_after INTEGER NOT NULL, -- Balance after transaction
    description TEXT NOT NULL,
    reference_type VARCHAR(30), -- 'referral', 'payment', 'promo'
    reference_id VARCHAR(64),
    expires_at DATETIME, -- Credits may expire
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wallet_tx_user ON wallet_transactions (user_id, created_at DESC);

-- ============================================================================
-- 2.9 ADD SUBSCRIPTION COLUMNS TO USERS
-- ============================================================================

ALTER TABLE users
ADD COLUMN subscription_status VARCHAR(20) DEFAULT 'free';

ALTER TABLE users ADD COLUMN subscription_expires_at DATETIME;

ALTER TABLE users ADD COLUMN lifetime_value_inr INTEGER DEFAULT 0;

ALTER TABLE users ADD COLUMN referral_code VARCHAR(20);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_referral_code ON users (referral_code);

-- Generate unique referral codes for existing users
-- (Run this as a migration script in Python)

-- ============================================================================
-- 2.10 PAYMENT FAILURE RETRY QUEUE
-- ============================================================================
-- For automatic payment retry on failed subscriptions

CREATE TABLE IF NOT EXISTS payment_retry_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id VARCHAR(36) NOT NULL REFERENCES user_subscriptions (id),
    user_id INTEGER NOT NULL REFERENCES users (id),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_attempt_at DATETIME,
    next_attempt_at DATETIME NOT NULL,
    last_failure_reason TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'success', 'exhausted', 'cancelled'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_retry_pending ON payment_retry_queue (status, next_attempt_at);

-- ============================================================================
-- SEED DATA: Default Subscription Plans
-- ============================================================================

INSERT
    OR IGNORE INTO subscription_plans (
        id,
        code,
        name,
        display_name,
        description,
        price_inr,
        original_price_inr,
        billing_period,
        duration_days,
        features,
        is_featured,
        badge_text,
        sort_order,
        is_active
    )
VALUES (
        'plan_free',
        'free',
        'free',
        'Free',
        'Core NCERT learning with daily limits for AI and tests.',
        0,
        0,
        'lifetime',
        36500,
        '{"subjects": ["biology", "chemistry", "physics"], "max_daily_queries": 15, "mock_tests_per_month": 2, "analytics": "basic", "doubt_tools": "limited", "scholarship_eligible": true}',
        FALSE,
        'Always Free',
        0,
        TRUE
    ),
    (
        'plan_plus_monthly',
        'plus_monthly',
        'plus',
        'Plus Monthly',
        'Affordable monthly upgrade with stronger limits and analytics',
        199,
        299,
        'monthly',
        30,
        '{"subjects": ["biology", "chemistry", "physics"], "max_daily_queries": 80, "mock_tests_per_month": 12, "analytics": "advanced", "doubt_tools": "priority", "scholarship_eligible": true, "sponsored_seats_available": true}',
        TRUE,
        'Most Affordable',
        1,
        TRUE
    ),
    (
        'plan_pro_monthly',
        'pro_monthly',
        'pro',
        'Pro Monthly',
        'High-intensity preparation with premium planning and support',
        499,
        699,
        'monthly',
        30,
        '{"subjects": ["biology", "chemistry", "physics"], "max_daily_queries": -1, "mock_tests_per_month": 30, "analytics": "premium", "doubt_tools": "priority", "priority_support": true, "scholarship_eligible": true}',
        TRUE,
        'Recommended',
        2,
        TRUE
    ),
    (
        'plan_pro_annual',
        'pro_annual',
        'pro',
        'Pro Annual',
        'Best value for year-long prep with visible monthly savings',
        1299,
        1799,
        'yearly',
        365,
        '{"subjects": ["biology", "chemistry", "physics"], "max_daily_queries": -1, "mock_tests_per_month": -1, "analytics": "premium", "doubt_tools": "priority", "priority_support": true, "exam_readiness_reports": true, "scholarship_eligible": true, "sponsored_seats_available": true}',
        TRUE,
        'Best Value',
        3,
        TRUE
    ),
    (
        'plan_pro_exam_cycle',
        'pro_exam_cycle',
        'pro',
        'Pro Exam Cycle',
        'Exam-season bundle aligned with NEET timeline and revision cycles',
        1799,
        2499,
        'exam_cycle',
        400,
        '{"subjects": ["biology", "chemistry", "physics"], "max_daily_queries": -1, "mock_tests_per_month": -1, "analytics": "premium", "doubt_tools": "priority", "priority_support": true, "exam_season_intensive": true, "scholarship_eligible": true, "sponsored_seats_available": true}',
        FALSE,
        'Exam Ready',
        4,
        TRUE
    );

-- ============================================================================
-- END OF PHASE 2
-- ============================================================================