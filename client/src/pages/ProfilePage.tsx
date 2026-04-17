import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardBody,
  CardHeader,
  Input,
  Button,
  Select,
  SelectItem,
  Slider,
  DatePicker,
} from '@heroui/react';
import { CalendarDate, today, getLocalTimeZone, parseDate } from '@internationalized/date';
import { motion } from 'framer-motion';
import { User, Save, Trash2 } from 'lucide-react';
import apiClient from '../lib/api';
import { normalizeLanguage } from '../lib/language';
import { normalizeApiUserProfile, useProfileStore, type UserProfile } from '../store/profileStore';
import { useGamificationStore } from '../store/gamificationStore';

export function ProfilePage() {
  const navigate = useNavigate();
  const { profile, setProfile, updateProfile, clearProfile } = useProfileStore();
  const { totalXP, currentLevel, currentStreak, badges } = useGamificationStore();
  const [isSaving, setIsSaving] = useState(false);

  const [name, setName] = useState(profile?.name || '');
  const [dob, setDob] = useState<CalendarDate | null>(
    profile?.dateOfBirth ? parseDate(profile.dateOfBirth) : null
  );
  const [currentClass, setCurrentClass] = useState(profile?.currentClass || '12th');
  const [attemptNumber, setAttemptNumber] = useState(profile?.attemptNumber || 1);
  const [targetYear, setTargetYear] = useState(String(profile?.targetYear || new Date().getFullYear() + 1));
  const [targetScore, setTargetScore] = useState(profile?.targetScore || 650);
  const [dailyStudyTarget, setDailyStudyTarget] = useState(profile?.dailyStudyTarget || 4);

  async function handleSave() {
    const payload = {
      name: name.trim(),
      dob: dob ? `${dob.year}-${String(dob.month).padStart(2, '0')}-${String(dob.day).padStart(2, '0')}` : null,
      current_class: currentClass,
      attempt_number: attemptNumber,
      target_year: String(targetYear),
      target_score: targetScore,
      strong_subjects: profile?.strongSubjects ?? [],
      weak_subjects: profile?.weakSubjects ?? [],
      daily_study_target: dailyStudyTarget,
      preferred_language: normalizeLanguage(profile?.preferredLanguage),
    };

    setIsSaving(true);
    try {
      const res = await apiClient.put('/api/auth/profile', payload);
      setProfile(normalizeApiUserProfile(res.data));
    } catch (err: unknown) {
      console.error(err);
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(error.response?.data?.detail || error.message || 'Failed to save profile');
      updateProfile({
        name: name.trim(),
        dateOfBirth: payload.dob ?? '',
        currentClass: currentClass as UserProfile['currentClass'],
        attemptNumber,
        targetYear: Number(targetYear),
        targetScore,
        dailyStudyTarget,
      });
    } finally {
      setIsSaving(false);
    }
  }

  function handleReset() {
    if (confirm('This will erase all your data including XP, badges, and progress. Are you sure?')) {
      clearProfile();
      void useGamificationStore.getState().totalXP; // Clear gamification too
      localStorage.removeItem('APXMIND-gamification');
      localStorage.removeItem('APXMIND-profile');
      navigate('/register', { replace: true });
    }
  }

  const age = dob
    ? Math.floor((Date.now() - new Date(dob.year, dob.month - 1, dob.day).getTime()) / 3.156e10)
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto space-y-5"
    >
      <h1 className="flex items-center gap-2" style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
        <User className="w-6 h-6 text-secondary" />
        Profile
      </h1>

      {/* Stats summary */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Level', value: currentLevel },
          { label: 'XP', value: totalXP.toLocaleString() },
          { label: 'Streak', value: `${currentStreak}d` },
          { label: 'Badges', value: badges.length },
        ].map((s) => (
          <Card key={s.label} className="glass">
            <CardBody className="text-center p-3">
              <p className="text-lg font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{s.value}</p>
              <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.label}</p>
            </CardBody>
          </Card>
        ))}
      </div>

      {/* Edit profile */}
      <Card className="glass">
        <CardHeader className="pb-2">
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, marginBottom: 16, color: 'var(--text-primary)' }}>Personal Information</h2>
        </CardHeader>
        <CardBody className="gap-4">
          <Input
            label="Full Name"
            value={name}
            onValueChange={setName}
            variant="bordered"
            startContent={<User className="w-4 h-4 text-text-faint" />}
            classNames={{
              inputWrapper: 'bg-bg-3 border-border-default rounded-[var(--r-md)] px-[14px] py-[9px]',
              label: 'text-[11px] text-text-muted mb-[5px]',
              input: 'text-text-primary text-[13px]',
            }}
          />
          <div className="grid grid-cols-2 gap-3">
            <DatePicker
              label="Date of Birth"
              value={dob}
              onChange={setDob}
              variant="bordered"
              showMonthAndYearPickers
              maxValue={today(getLocalTimeZone())}
              minValue={new CalendarDate(1996, 1, 1)}
              classNames={{
                inputWrapper: 'bg-bg-3 border-border-default rounded-[var(--r-md)]',
                label: 'text-[11px] text-text-muted mb-[5px]',
              }}
            />
            {age !== null && (
              <Input
                label="Age"
                value={`${age} years`}
                isReadOnly
                variant="flat"
                classNames={{ inputWrapper: 'bg-bg-3 border border-border-default rounded-[var(--r-md)]', label: 'text-[11px] text-text-muted', input: 'text-[13px] text-text-primary' }}
              />
            )}
          </div>
        </CardBody>
      </Card>

      <Card className="glass">
        <CardHeader className="pb-2">
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, marginBottom: 16, color: 'var(--text-primary)' }}>NEET Details</h2>
        </CardHeader>
        <CardBody className="gap-4">
          <Select
            label="Current Class / Status"
            selectedKeys={new Set([currentClass])}
            onSelectionChange={(keys) => setCurrentClass(Array.from(keys)[0] as '11th' | '12th' | 'dropper')}
            variant="bordered"
            classNames={{ trigger: 'bg-bg-3 border-border-default rounded-[var(--r-md)] text-text-primary text-[13px]', label: 'text-[11px] text-text-muted mb-[5px]' }}
          >
            <SelectItem key="11th" textValue="Class 11th">Class 11th</SelectItem>
            <SelectItem key="12th" textValue="Class 12th">Class 12th</SelectItem>
            <SelectItem key="dropper" textValue="Dropper / Repeater">Dropper / Repeater</SelectItem>
          </Select>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>Attempt</label>
              <div className="flex gap-2">
                {[1, 2, 3].map((n) => (
                  <Button
                    key={n}
                    variant={attemptNumber === n ? 'solid' : 'bordered'}
                    color={attemptNumber === n ? 'secondary' : 'default'}
                    size="sm"
                    onPress={() => setAttemptNumber(n)}
                    style={
                      attemptNumber === n
                        ? { background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 'var(--r-sm)', width: 36, height: 36, fontSize: 13 }
                        : { background: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border-default)', borderRadius: 'var(--r-sm)', width: 36, height: 36, fontSize: 13 }
                    }
                  >
                    {n === 3 ? '3+' : n}
                  </Button>
                ))}
              </div>
            </div>
            <Select
              label="Target Year"
              selectedKeys={new Set([targetYear])}
              onSelectionChange={(keys) => setTargetYear(Array.from(keys)[0] as string)}
              variant="bordered"
              classNames={{ trigger: 'bg-bg-3 border-border-default rounded-[var(--r-md)] text-text-primary text-[13px]', label: 'text-[11px] text-text-muted mb-[5px]' }}
            >
              {[0, 1, 2].map((offset) => {
                const y = String(new Date().getFullYear() + offset);
                return <SelectItem key={y} textValue={`NEET ${y}`}>NEET {y}</SelectItem>;
              })}
            </Select>
          </div>

          <div>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>
              Target Score: <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{targetScore}</span> / 720
            </label>
            <Slider
              aria-label="Target score"
              step={10}
              minValue={100}
              maxValue={720}
              value={targetScore}
              onChange={(v) => setTargetScore(v as number)}
              color="secondary"
              classNames={{ track: 'bg-bg-5 h-[4px] rounded-[var(--r-pill)]', filler: 'bg-accent', thumb: 'w-[18px] h-[18px] bg-accent border-2 border-white' }}
            />
          </div>

          <div>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>
              Daily Study Target: <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{dailyStudyTarget}h</span>
            </label>
            <Slider
              aria-label="Daily study target"
              step={0.5}
              minValue={1}
              maxValue={12}
              value={dailyStudyTarget}
              onChange={(v) => setDailyStudyTarget(v as number)}
              color="secondary"
              classNames={{ track: 'bg-bg-5 h-[4px] rounded-[var(--r-pill)]', filler: 'bg-accent', thumb: 'w-[18px] h-[18px] bg-accent border-2 border-white' }}
            />
          </div>
        </CardBody>
      </Card>

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          color="secondary"
          className="flex-1"
          onPress={handleSave}
          isLoading={isSaving}
          startContent={<Save className="w-4 h-4" />}
          style={{ width: '100%', padding: '11px 18px', fontSize: 14 }}
        >
          Save Changes
        </Button>
        <Button
          color="danger"
          variant="flat"
          onPress={handleReset}
          startContent={<Trash2 className="w-4 h-4" />}
          style={{ padding: '11px 18px', fontSize: 14 }}
        >
          Reset All Data
        </Button>
      </div>
    </motion.div>
  );
}
