import { useEffect, useRef, useState } from 'react';
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Chip,
  Input,
  Spinner,
} from '@heroui/react';
import { CreditCard, Wallet, Receipt, Crown } from 'lucide-react';
import {
  cancelSubscription,
  getSubscriptionOverview,
  purchasePlan,
  type SubscriptionPlan,
  type UserSubscription,
} from '../lib/accountService';
import { getApiErrorMessage } from '../lib/api';

interface BillingSnapshot {
  plans: SubscriptionPlan[];
  currentSubscription: UserSubscription | null;
  payments: Array<{ id: string; final_amount: number; status: string; created_at?: string | null }>;
  invoices: Array<{ id: string; invoice_number: string; total_amount: number; status: string; invoice_date?: string | null }>;
  wallet: { balance: number; lifetime_earned: number; lifetime_spent: number };
}

export function SubscriptionPage() {
  const loadedOnceRef = useRef(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isBuying, setIsBuying] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [promoCode, setPromoCode] = useState('');
  const [data, setData] = useState<BillingSnapshot>({
    plans: [],
    currentSubscription: null,
    payments: [],
    invoices: [],
    wallet: { balance: 0, lifetime_earned: 0, lifetime_spent: 0 },
  });

  const totalInvoiceValue = data.invoices.reduce((sum, invoice) => sum + (invoice.total_amount || 0), 0);

  async function loadData() {
    setIsLoading(true);
    setError(null);
    try {
      const snapshot = await getSubscriptionOverview();
      setData(snapshot);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to load subscription data.'));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (loadedOnceRef.current) return;
    loadedOnceRef.current = true;
    void loadData();
  }, []);

  async function handleBuy(planId: string) {
    setIsBuying(planId);
    setError(null);
    try {
      await purchasePlan(planId, promoCode);
      setPromoCode('');
      await loadData();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Unable to complete purchase.'));
    } finally {
      setIsBuying(null);
    }
  }

  async function handleCancel() {
    if (!data.currentSubscription?.id) return;
    try {
      await cancelSubscription(data.currentSubscription.id);
      await loadData();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Unable to cancel subscription.'));
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <h1 className="flex items-center gap-2" style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
        <CreditCard className="w-6 h-6 text-secondary" />
        Subscription & Billing
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="glass">
          <CardBody className="p-4">
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Current Plan Status</p>
            <div className="mt-1 flex items-center gap-2">
              <Crown className="w-4 h-4 text-amber-500" />
              <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                {data.currentSubscription?.status ?? 'free'}
              </p>
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-faint)' }}>
              {data.currentSubscription?.expires_at ? `Expires: ${new Date(data.currentSubscription.expires_at).toLocaleDateString()}` : 'No active subscription'}
            </p>
          </CardBody>
        </Card>
        <Card className="glass">
          <CardBody className="p-4">
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Wallet Balance</p>
            <div className="mt-1 flex items-center gap-2">
              <Wallet className="w-4 h-4 text-emerald-500" />
              <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>₹{data.wallet.balance}</p>
            </div>
          </CardBody>
        </Card>
        <Card className="glass">
          <CardBody className="p-4">
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Invoice Value</p>
            <div className="mt-1 flex items-center gap-2">
              <Receipt className="w-4 h-4 text-blue-500" />
              <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>₹{totalInvoiceValue}</p>
            </div>
          </CardBody>
        </Card>
      </div>

      <Card className="glass">
        <CardHeader className="pb-2">
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Choose Plan</h2>
        </CardHeader>
        <CardBody className="space-y-4">
          <Input
            label="Promo Code (optional)"
            value={promoCode}
            onValueChange={setPromoCode}
            aria-label="Promo code"
            variant="bordered"
          />
          {isLoading ? (
            <div className="py-8 flex justify-center"><Spinner label="Loading plans" /></div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {data.plans.map((plan) => {
                const isCurrent = data.currentSubscription?.plan_id === plan.id && data.currentSubscription?.status === 'active';
                return (
                  <Card key={plan.id} className="glass" style={{ border: isCurrent ? '1px solid var(--accent)' : '1px solid var(--border-subtle)' }}>
                    <CardBody className="space-y-2">
                      <div className="flex items-center justify-between">
                        <p style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{plan.display_name}</p>
                        {plan.badge_text ? <Chip size="sm" variant="flat" color="warning">{plan.badge_text}</Chip> : null}
                      </div>
                      <p style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)' }}>₹{plan.price_inr}</p>
                      <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>{plan.billing_period} • {plan.duration_days} days</p>
                      <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{plan.description || 'Full access for this plan period.'}</p>
                      <Button
                        color={isCurrent ? 'success' : 'secondary'}
                        isDisabled={isCurrent}
                        isLoading={isBuying === plan.id}
                        onPress={() => void handleBuy(plan.id)}
                      >
                        {isCurrent ? 'Active Plan' : 'Buy Now'}
                      </Button>
                    </CardBody>
                  </Card>
                );
              })}
            </div>
          )}
          {data.currentSubscription?.status === 'active' ? (
            <Button color="danger" variant="flat" onPress={() => void handleCancel()}>
              Cancel Current Subscription
            </Button>
          ) : null}
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="glass">
          <CardHeader><h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Recent Payments</h2></CardHeader>
          <CardBody className="space-y-2">
            {data.payments.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No payments yet.</p>
            ) : data.payments.map((payment) => (
              <div key={payment.id} className="flex justify-between" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                <span>₹{payment.final_amount}</span>
                <span>{payment.status}</span>
                <span>{payment.created_at ? new Date(payment.created_at).toLocaleDateString() : '-'}</span>
              </div>
            ))}
          </CardBody>
        </Card>

        <Card className="glass">
          <CardHeader><h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Recent Invoices</h2></CardHeader>
          <CardBody className="space-y-2">
            {data.invoices.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No invoices yet.</p>
            ) : data.invoices.map((invoice) => (
              <div key={invoice.id} className="flex justify-between" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                <span>{invoice.invoice_number}</span>
                <span>₹{invoice.total_amount}</span>
                <span>{invoice.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString() : '-'}</span>
              </div>
            ))}
          </CardBody>
        </Card>
      </div>

      {error ? <p style={{ fontSize: 12, color: 'var(--red)' }}>{error}</p> : null}
    </div>
  );
}
