import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Input,
  Button,
  Select,
  SelectItem,
  Slider,
} from '@heroui/react';
import { CalendarDate } from '@internationalized/date';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight,
  ArrowLeft,
  Sparkles,
  User,
  Lock,
  GraduationCap,
  Target,
  BookOpen,
  CheckCircle2,
  Atom,
  FlaskConical,
  Dna,
} from 'lucide-react';
import apiClient from '../lib/api';
import { normalizeApiUserProfile, useProfileStore } from '../store/profileStore';

const STEPS = ['Personal Info', 'Academic Details', 'NEET Goals', 'Study Preferences'];

const subjects = [
  { key: 'physics', label: 'Physics', icon: <Atom className="w-4 h-4" />, color: '#3b82f6' },
  { key: 'chemistry', label: 'Chemistry', icon: <FlaskConical className="w-4 h-4" />, color: '#10b981' },
  { key: 'biology', label: 'Biology', icon: <Dna className="w-4 h-4" />, color: '#7c3aed' },
] as const;

const classOptions = [
  { key: '11th', label: 'Class 11th' },
  { key: '12th', label: 'Class 12th' },
  { key: 'dropper', label: 'Dropper / Repeater' },
];

const currentYear = new Date().getFullYear();
const targetYears = [
  { key: String(currentYear), label: `NEET ${currentYear}` },
  { key: String(currentYear + 1), label: `NEET ${currentYear + 1}` },
  { key: String(currentYear + 2), label: `NEET ${currentYear + 2}` },
];

const stepIcons = [User,
  Lock, GraduationCap, Target, BookOpen];

export function ProfileSetup() {
  const navigate = useNavigate();
  const setProfile = useProfileStore((s) => s.setProfile);
  const [step, setStep] = useState(0);

  // Form state
  const [name, setName] = useState('');

  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [dob, setDob] = useState<CalendarDate | null>(null);
  const [currentClass, setCurrentClass] = useState<string>('12th');
  const [attemptNumber, setAttemptNumber] = useState(1);
  const [targetYear, setTargetYear] = useState(String(currentYear + 1));
  const [targetScore, setTargetScore] = useState(650);
  const [strongSubjects, setStrongSubjects] = useState<Set<string>>(new Set());
  const [weakSubjects, setWeakSubjects] = useState<Set<string>>(new Set());
  const [dailyStudyTarget, setDailyStudyTarget] = useState(4);
  const [preferredLanguage, setPreferredLanguage] = useState<string>('english');

  const [errors, setErrors] = useState<Record<string, string>>({});

  function validateStep(): boolean {
    const newErrors: Record<string, string> = {};
    if (step === 0) {
      if (!name.trim()) newErrors.name = 'Name is required';
      if (!password || password.length < 4) newErrors.password = 'Password/PIN must be at least 4 chars';
      else if (name.trim().length < 2) newErrors.name = 'Name must be at least 2 characters';
      if (!dob) newErrors.dob = 'Date of birth is required';
      else {
        const birthDate = new Date(dob.year, dob.month - 1, dob.day);
        const age = Math.floor((Date.now() - birthDate.getTime()) / 3.156e10);
        if (age < 14 || age > 30) newErrors.dob = 'Age must be between 14 and 30';
      }
    }
    if (step === 1 && !currentClass) newErrors.currentClass = 'Select your current class';
    if (step === 2) {
      if (!targetYear) newErrors.targetYear = 'Select target NEET year';
      if (targetScore < 100 || targetScore > 720) newErrors.targetScore = 'Score must be between 100 and 720';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function handleNext() {
    if (!validateStep()) return;
    if (step < STEPS.length - 1) setStep(step + 1);
  }

  function handleBack() {
    if (step > 0) setStep(step - 1);
  }

  function toggleSubject(
    subject: string,
    set: Set<string>,
    setter: (s: Set<string>) => void,
    otherSet: Set<string>,
    otherSetter: (s: Set<string>) => void,
  ) {
    const next = new Set(set);
    if (next.has(subject)) {
      next.delete(subject);
    } else {
      next.add(subject);
      const otherNext = new Set(otherSet);
      otherNext.delete(subject);
      otherSetter(otherNext);
    }
    setter(next);
  }

  async function handleFinish() {
    if (!validateStep()) return;
    setIsSubmitting(true);

    // Default dob to a default properly formatted if they skip or it throws
    const dobString = dob
      ? `${dob.year}-${String(dob.month).padStart(2, '0')}-${String(dob.day).padStart(2, '0')}`
      : '2000-01-01'; // Default

    const data = {
      name: name.trim(),
      password: password,
      dob: dobString,
      current_class: currentClass,
      attempt_number: attemptNumber,
      target_year: String(targetYear),
      target_score: targetScore,
      strong_subjects: Array.from(strongSubjects),
      weak_subjects: Array.from(weakSubjects),
      daily_study_target: dailyStudyTarget,
      preferred_language: preferredLanguage,
    };

    try {
      const res = await apiClient.post('/api/auth/register', data);
      if (res.data.success && res.data.token) {
        localStorage.setItem('APXMIND_token', res.data.token);
        setProfile(normalizeApiUserProfile(res.data.user));
        navigate('/home', { replace: true });
      }
    } catch (err: unknown) {
      console.error(err);
      const error = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };
      if (error.response?.status === 409) {
        setErrors(prev => ({ ...prev, name: 'Name already exists. Please choose another.' }));
        setStep(0); // push back to step 0
      } else {
        alert('Registration failed: ' + (error.response?.data?.detail || error.message || 'Unknown error'));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  const progressPercent = ((step + 1) / STEPS.length) * 100;

  const stepDescriptions = [
    "Let's get to know you better",
    'Tell us about your academic journey',
    'Set your target — aim high!',
    'Personalize your study experience',
  ];

  return (
    <div className="min-h-dvh flex items-center justify-center relative overflow-hidden p-4">
      {/* Solid background */}
      <div className="fixed inset-0 bg-bg-0" />

      <div className="w-full max-w-md relative z-10">
        {/* Logo & branding */}
        <motion.div
          initial={{ opacity: 0, y: -30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-8"
        >
          <motion.div
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-bg-2 border border-border-default mb-4"
            animate={{ rotate: [0, 5, -5, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          >
            <Sparkles className="w-8 h-8 text-accent" />
          </motion.div>
          <h1 className="text-4xl font-extrabold tracking-tight text-text-primary">
            APXMIND
          </h1>
          <p className="text-text-muted text-sm mt-1.5 font-medium">
            Your AI-Powered NEET Companion
          </p>
        </motion.div>

        {/* Step progress bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="mb-6"
        >
          <div className="flex items-center justify-between mb-3">
            {STEPS.map((s, i) => {
              const Icon = stepIcons[i];
              const isActive = i === step;
              const isDone = i < step;
              return (
                <button
                  key={s}
                  onClick={() => isDone && setStep(i)}
                  className="flex flex-col items-center gap-1.5 group relative"
                  disabled={i > step}
                >
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-300 ${isActive
                        ? 'bg-accent text-text-primary shadow-lg scale-110'
                        : isDone
                          ? 'bg-bg-2 text-accent border border-accent/50 cursor-pointer hover:scale-105'
                          : 'bg-bg-2 text-text-muted border border-border-default'
                      }`}
                  >
                    {isDone ? <CheckCircle2 className="w-5 h-5" /> : <Icon className="w-5 h-5" />}
                  </div>
                  <span
                    className={`text-[11px] font-medium transition-colors hidden sm:block ${isActive ? 'text-accent' : isDone ? 'text-accent/70' : 'text-text-faint'
                      }`}
                  >
                    {s}
                  </span>
                </button>
              );
            })}
          </div>
          <div className="relative h-1 bg-apxmind-border rounded-full overflow-hidden">
            <motion.div
              className="absolute inset-y-0 left-0 bg-accent rounded-full"
              initial={false}
              animate={{ width: `${progressPercent}%` }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            />
          </div>
        </motion.div>

        {/* Main card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 40, scale: 0.98 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: -40, scale: 0.98 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="bg-bg-2/80 backdrop-blur-xl border border-border-default rounded-2xl shadow-2xl shadow-black/50">
              <div className="flex flex-col items-start gap-1 px-6 pt-6 pb-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-accent" />
                  <h2 className="text-xl font-bold text-text-primary">{STEPS[step]}</h2>
                </div>
                <p className="text-text-muted text-sm pl-4">{stepDescriptions[step]}</p>
              </div>

              <div className="flex flex-col gap-5 py-5 px-6">
                {step === 0 && (
                  <>
                    <Input
                      label="Full Name"
                      placeholder="Enter your name"
                      value={name}
                      onValueChange={setName}
                      isInvalid={!!errors.name}
                      errorMessage={errors.name}
                      variant="bordered"
                      size="lg"
                      startContent={<User className="w-4 h-4 text-text-secondary" />}
                      classNames={{
                        inputWrapper: 'border-border-default hover:border-accent focus-within:!border-accent bg-bg-3',
                        label: 'text-text-secondary',
                        input: 'text-text-primary placeholder:text-text-faint',
                      }}
                      autoFocus
                    />
                    <Input
                      label="Password"
                      placeholder="Create a password"
                      value={password}
                      onValueChange={setPassword}
                      isInvalid={!!errors.password}
                      errorMessage={errors.password}
                      variant="bordered"
                      size="lg"
                      type="password"
                      startContent={<Lock className="w-4 h-4 text-text-secondary" />}
                      classNames={{
                        inputWrapper: 'border-border-default hover:border-accent focus-within:!border-accent bg-bg-3',
                        label: 'text-text-secondary',
                        input: 'text-text-primary placeholder:text-text-faint',
                      }}
                    />
                    <Input
                      label="Date of Birth"
                      placeholder="DD/MM/YYYY"
                      type="date"
                      value={dob ? `${dob.year}-${String(dob.month).padStart(2, '0')}-${String(dob.day).padStart(2, '0')}` : ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val) {
                          const [y, m, d] = val.split('-').map(Number);
                          setDob(new CalendarDate(y, m, d));
                        } else {
                          setDob(null as unknown as CalendarDate);
                        }
                      }}
                      isInvalid={!!errors.dob}
                      errorMessage={errors.dob}
                      variant="bordered"
                      size="lg"
                      classNames={{
                        inputWrapper: 'border-border-default hover:border-accent focus-within:!border-accent bg-bg-3',
                        label: 'text-text-secondary',
                        input: 'text-text-primary placeholder:text-text-faint',
                      }}
                    />
                  </>
                )}

                {step === 1 && (
                  <>
                    <Select
                      label="Current Class / Status"
                      selectedKeys={new Set([currentClass])}
                      onSelectionChange={(keys) => setCurrentClass(Array.from(keys)[0] as string)}
                      isInvalid={!!errors.currentClass}
                      errorMessage={errors.currentClass}
                      variant="bordered"
                      size="lg"
                      classNames={{
                        trigger: 'border-border-default hover:border-accent bg-bg-3',
                        label: 'text-text-secondary',
                        value: 'text-text-primary',
                      }}
                    >
                      {classOptions.map((o) => (
                        <SelectItem key={o.key} textValue={o.label}>{o.label}</SelectItem>
                      ))}
                    </Select>
                    <div>
                      <label className="text-sm font-semibold text-text-secondary mb-3 block">
                        NEET Attempt Number
                      </label>
                      <div className="flex gap-3">
                        {[1, 2, 3].map((n) => (
                          <motion.button
                            key={n}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => setAttemptNumber(n)}
                            className={`flex-1 py-3 rounded-xl text-sm font-semibold transition-all duration-200 ${attemptNumber === n
                                ? 'bg-accent text-text-primary shadow-lg'
                                : 'bg-bg-3 text-text-secondary border border-border-default hover:border-accent hover:text-text-primary'
                              }`}
                          >
                            {n === 3 ? '3+' : n === 1 ? '1st' : '2nd'}
                          </motion.button>
                        ))}
                      </div>
                    </div>
                  </>
                )}

                {step === 2 && (
                  <>
                    <Select
                      label="Target NEET Year"
                      selectedKeys={new Set([targetYear])}
                      onSelectionChange={(keys) => setTargetYear(Array.from(keys)[0] as string)}
                      isInvalid={!!errors.targetYear}
                      errorMessage={errors.targetYear}
                      variant="bordered"
                      size="lg"
                      classNames={{
                        trigger: 'border-border-default hover:border-accent bg-bg-3',
                        label: 'text-text-secondary',
                        value: 'text-text-primary',
                      }}
                    >
                      {targetYears.map((y) => (
                        <SelectItem key={y.key} textValue={y.label}>{y.label}</SelectItem>
                      ))}
                    </Select>
                    <div>
                      <div className="flex items-baseline justify-between mb-2">
                        <label className="text-sm font-semibold text-text-secondary">Target Score</label>
                        <span className="text-2xl font-bold text-accent">
                          {targetScore}
                          <span className="text-sm text-text-faint font-normal"> / 720</span>
                        </span>
                      </div>
                      <Slider
                        aria-label="Target score"
                        step={10}
                        minValue={100}
                        maxValue={720}
                        value={targetScore}
                        onChange={(v) => setTargetScore(v as number)}
                        color="secondary"
                        showTooltip
                        tooltipProps={{ content: `${targetScore} / 720` }}
                        className="mt-1"
                        classNames={{
                          track: 'bg-apxmind-border',
                          filler: 'bg-accent',
                        }}
                      />
                      <div className="flex justify-between text-xs text-text-faint mt-1">
                        <span>100</span>
                        <span>Good: 550+</span>
                        <span>Top: 650+</span>
                        <span>720</span>
                      </div>
                      {errors.targetScore && (
                        <p className="text-danger text-xs mt-1">{errors.targetScore}</p>
                      )}
                    </div>
                  </>
                )}

                {step === 3 && (
                  <>
                    <div>
                      <label className="text-sm font-semibold text-text-secondary mb-3 block">
                        💪 Strong Subjects
                      </label>
                      <div className="flex gap-2 flex-wrap">
                        {subjects.map((s) => {
                          const selected = strongSubjects.has(s.key);
                          return (
                            <motion.button
                              key={s.key}
                              whileHover={{ scale: 1.03 }}
                              whileTap={{ scale: 0.97 }}
                              onClick={() =>
                                toggleSubject(s.key, strongSubjects, setStrongSubjects, weakSubjects, setWeakSubjects)
                              }
                              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${selected
                                  ? 'bg-accent/20 text-accent border border-accent/60'
                                  : 'bg-bg-3 text-text-muted border border-border-default hover:border-accent/40 hover:text-text-secondary'
                                }`}
                            >
                              {s.icon}
                              {s.label}
                              {selected && <CheckCircle2 className="w-3.5 h-3.5" />}
                            </motion.button>
                          );
                        })}
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-semibold text-text-secondary mb-3 block">
                        📈 Subjects to Improve
                      </label>
                      <div className="flex gap-2 flex-wrap">
                        {subjects.map((s) => {
                          const selected = weakSubjects.has(s.key);
                          return (
                            <motion.button
                              key={s.key}
                              whileHover={{ scale: 1.03 }}
                              whileTap={{ scale: 0.97 }}
                              onClick={() =>
                                toggleSubject(s.key, weakSubjects, setWeakSubjects, strongSubjects, setStrongSubjects)
                              }
                              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${selected
                                  ? 'bg-accent/20 text-accent border border-accent/60'
                                  : 'bg-bg-3 text-text-muted border border-border-default hover:border-accent/40 hover:text-text-secondary'
                                }`}
                            >
                              {s.icon}
                              {s.label}
                              {selected && <CheckCircle2 className="w-3.5 h-3.5" />}
                            </motion.button>
                          );
                        })}
                      </div>
                    </div>
                    <div>
                      <div className="flex items-baseline justify-between mb-2">
                        <label className="text-sm font-semibold text-text-secondary">Daily Study Target</label>
                        <span className="text-lg font-bold text-accent">
                          {dailyStudyTarget}
                          <span className="text-sm text-text-muted font-normal"> hrs/day</span>
                        </span>
                      </div>
                      <Slider
                        aria-label="Daily study target"
                        step={0.5}
                        minValue={1}
                        maxValue={12}
                        value={dailyStudyTarget}
                        onChange={(v) => setDailyStudyTarget(v as number)}
                        color="secondary"
                        showTooltip
                        tooltipProps={{ content: `${dailyStudyTarget} hours / day` }}
                        classNames={{
                          track: 'bg-apxmind-border',
                          filler: 'bg-accent',
                        }}
                      />
                    </div>
                    <Select
                      label="Preferred Language"
                      selectedKeys={new Set([preferredLanguage])}
                      onSelectionChange={(keys) => setPreferredLanguage(Array.from(keys)[0] as string)}
                      variant="bordered"
                      size="lg"
                      classNames={{
                        trigger: 'border-border-default hover:border-accent bg-bg-3',
                        label: 'text-text-secondary',
                        value: 'text-text-primary',
                      }}
                    >
                      <SelectItem key="english" textValue="English">🇬🇧 English</SelectItem>
                      <SelectItem key="hindi" textValue="Hindi">🇮🇳 Hindi</SelectItem>
                    </Select>
                  </>
                )}
              </div>

              <div className="flex justify-between gap-3 px-6 pb-6 pt-2">
                <Button
                  variant="flat"
                  onPress={handleBack}
                  isDisabled={step === 0}
                  startContent={<ArrowLeft className="w-4 h-4" />}
                  className="text-text-secondary bg-bg-3 border border-border-default"
                >
                  Back
                </Button>
                {step < STEPS.length - 1 ? (
                  <Button
                    onPress={handleNext}
                    endContent={<ArrowRight className="w-4 h-4" />}
                    className="bg-accent text-text-primary font-semibold px-8 hover:opacity-90"
                    size="lg"
                  >
                    Continue
                  </Button>
                ) : (
                  <Button
                    onPress={handleFinish}
                    isLoading={isSubmitting}
                    endContent={!isSubmitting && <Sparkles className="w-4 h-4" />}
                    className="bg-accent text-text-primary font-semibold px-8 hover:opacity-90"
                    size="lg"
                  >
                    Start Learning
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-center mt-6 space-y-1"
        >
          <p className="text-text-muted text-xs">
            🔒 Your data stays on your device. No account needed.
          </p>
          <p className="text-text-faint text-[10px]">
            Step {step + 1} of {STEPS.length}
          </p>
        </motion.div>
      </div>
    </div>
  );
}
