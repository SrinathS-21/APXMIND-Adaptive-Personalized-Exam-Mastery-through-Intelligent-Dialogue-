import {
  Card,
  CardBody,
  Progress,
  Chip,
  Button,
} from '@heroui/react';
import { motion } from 'framer-motion';
import { useEffect, useMemo, useState } from 'react';
import { Trophy, Zap, Flame, Star, Lock } from 'lucide-react';
import apiClient, { getApiErrorMessage } from '../lib/api';
import { useToast } from '../hooks/useToast';
import { useProfileStore } from '../store/profileStore';
import { localizeBadgeMetadata, tUi, uiLocale } from '../lib/uiI18n';

interface ApiBadge {
  id: string;
  name: string;
  description: string;
  icon: string;
  earned: boolean;
  earned_at: string | null;
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 15 }, show: { opacity: 1, y: 0 } };

export function AchievementsPage() {
  const { addToast } = useToast();
  const language = useProfileStore((s) => s.profile?.preferredLanguage);
  const locale = uiLocale(language);
  const t = (key: string, vars?: Record<string, string | number>) => tUi(language, key, vars);
  const [badges, setBadges] = useState<ApiBadge[]>([]);
  const [totalXP, setTotalXP] = useState(0);
  const [currentLevel, setCurrentLevel] = useState(1);
  const [xpForNextLevel, setXpForNextLevel] = useState(500);
  const [currentStreak, setCurrentStreak] = useState(0);
  const [longestStreak, setLongestStreak] = useState(0);
  const [requestKey, setRequestKey] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadData() {
      setIsLoading(true);
      setError(null);
      try {
        const [achievementsRes, progressRes] = await Promise.all([
          apiClient.get('/api/achievements'),
          apiClient.get('/api/progress/gamification'),
        ]);

        if (!active) return;

        if (achievementsRes.data?.success) {
          setBadges(achievementsRes.data.badges ?? []);
        }

        const progress = progressRes.data;
        if (progress?.success) {
          setTotalXP(progress.total_xp ?? 0);
          setCurrentLevel(progress.current_level ?? 1);
          setXpForNextLevel(progress.xp_to_next_level ?? 500);
          setCurrentStreak(progress.current_streak ?? 0);
          setLongestStreak(progress.longest_streak ?? 0);
        }
        if (requestKey > 0) {
          addToast(t('ach.refreshed'), 'success');
        }
      } catch (error) {
        if (active) {
          const message = getApiErrorMessage(error, t('ach.loadError'));
          setError(message);
          addToast(message, 'error');
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    void loadData();
    return () => {
      active = false;
    };
  }, [addToast, requestKey]);

  const earnedBadges = useMemo(() => badges.filter((b) => b.earned), [badges]);
  const xpProgress = useMemo(() => {
    const levelSpan = 500;
    const progressed = Math.max(0, levelSpan - xpForNextLevel);
    return Math.min(100, Math.round((progressed / levelSpan) * 100));
  }, [xpForNextLevel]);

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="max-w-4xl mx-auto space-y-6">
      <motion.div variants={item}>
        <h1 className="flex items-center gap-2" style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
          <Trophy className="w-6 h-6 text-warning" />
          {t('ach.title')}
        </h1>
      </motion.div>

      {error && (
        <motion.div variants={item}>
          <Card className="glass">
            <CardBody className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3" style={{ padding: 14 }}>
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>{error}</p>
              <Button
                size="sm"
                variant="flat"
                color="secondary"
                isLoading={isLoading}
                onPress={() => setRequestKey((value) => value + 1)}
              >
                {t('home.retry')}
              </Button>
            </CardBody>
          </Card>
        </motion.div>
      )}

      {/* Stats overview */}
      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="glass">
          <CardBody className="text-center p-4" style={{ borderRadius: 'var(--r-md)' }}>
            <Zap className="w-6 h-6 mx-auto mb-1" style={{ color: 'var(--amber)' }} />
            <p className="text-2xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{totalXP.toLocaleString()}</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('ach.totalXp')}</p>
          </CardBody>
        </Card>
        <Card className="glass">
          <CardBody className="text-center p-4" style={{ borderRadius: 'var(--r-md)' }}>
            <Star className="w-6 h-6 text-secondary mx-auto mb-1" />
            <p className="text-2xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{currentLevel}</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('ach.levelLabel')}</p>
          </CardBody>
        </Card>
        <Card className="glass">
          <CardBody className="text-center p-4" style={{ borderRadius: 'var(--r-md)' }}>
            <Flame className="w-6 h-6 text-danger mx-auto mb-1" />
            <p className="text-2xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{currentStreak}d</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('ach.currentStreak')}</p>
          </CardBody>
        </Card>
        <Card className="glass">
          <CardBody className="text-center p-4" style={{ borderRadius: 'var(--r-md)' }}>
            <Trophy className="w-6 h-6 mx-auto mb-1" style={{ color: 'var(--purple)' }} />
            <p className="text-2xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{earnedBadges.length}/{badges.length}</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('ach.badgesEarned')}</p>
          </CardBody>
        </Card>
      </motion.div>

      {/* Level progress */}
      <motion.div variants={item}>
        <Card className="glass">
          <CardBody className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{t('app.level', { level: currentLevel })}</span>
              <span style={{ fontSize: 11, color: 'var(--text-faint)' }}>{t('ach.xpToNext', { xp: xpForNextLevel })}</span>
            </div>
            <Progress value={xpProgress} color="secondary" size="md" classNames={{ track: 'bg-bg-5', indicator: 'bg-linear-to-r from-[var(--accent)] to-[#A89CF8]' }} />
            <div className="flex justify-between mt-1" style={{ fontSize: 11, color: 'var(--text-faint)' }}>
              <span>{t('ach.bestStreak', { days: longestStreak })}</span>
              <span>{totalXP} / {currentLevel * 500} XP</span>
            </div>
          </CardBody>
        </Card>
      </motion.div>

      {/* Badges grid */}
      <motion.div variants={item}>
        <h2 className="mb-3" style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{t('ach.badges')}</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {badges.map((badge) => {
            const earned = badge.earned;
            const localizedBadge = localizeBadgeMetadata(language, badge.id, badge.name, badge.description);
            return (
              <motion.div key={badge.id} variants={item}>
                <Card
                  className="h-full"
                  style={
                    earned
                      ? {
                          background: 'var(--accent-glow)',
                          border: '1px solid var(--accent-border)',
                          borderRadius: 'var(--r-md)',
                        }
                      : {
                          background: 'var(--bg-3)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--r-md)',
                        }
                  }
                >
                  <CardBody className="text-center" style={{ padding: '16px 12px' }}>
                    <div className="mb-2 mx-auto flex items-center justify-center" style={{ width: 40, height: 40, borderRadius: 'var(--r-md)', background: earned ? 'var(--accent-soft)' : 'var(--bg-4)' }}>
                      {earned ? <span className="text-lg">{badge.icon}</span> : <Lock className="w-6 h-6 mx-auto text-default-300" />}
                    </div>
                    <p style={{ fontSize: 11, lineHeight: 1.4, color: earned ? 'var(--text-secondary)' : 'var(--text-faint)' }}>{localizedBadge.name}</p>
                    <p className="mt-1" style={{ fontSize: 11, color: 'var(--text-faint)' }}>{localizedBadge.description}</p>
                    {earned && badge.earned_at && (
                      <Chip size="sm" variant="flat" color="success" className="mt-2 text-[10px]" style={{ borderRadius: 'var(--r-pill)' }}>
                        {t('ach.earned', { date: new Date(badge.earned_at).toLocaleDateString(locale) })}
                      </Chip>
                    )}
                  </CardBody>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </motion.div>
  );
}
