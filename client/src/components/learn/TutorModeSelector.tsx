import { Button, Card, CardBody } from '@heroui/react';
import { Compass, Gauge, Swords } from 'lucide-react';
import type { TutorMode } from '../../lib/learnSessionService';

interface TutorModeSelectorProps {
  selectedMode: TutorMode;
  onChange: (mode: TutorMode) => void;
  isDisabled?: boolean;
  compact?: boolean;
}

const MODES: Array<{
  mode: TutorMode;
  label: string;
  compactLabel: string;
  description: string;
  icon: React.ReactNode;
}> = [
  {
    mode: 'guided',
    label: 'Guided Learn',
    compactLabel: 'Guided',
    description: 'Step-by-step teaching with examples',
    icon: <Compass className="w-4 h-4" />,
  },
  {
    mode: 'revision',
    label: 'Rapid Revision',
    compactLabel: 'Revision',
    description: 'High-yield recap with key exam points',
    icon: <Gauge className="w-4 h-4" />,
  },
  {
    mode: 'drill',
    label: 'Exam Drill',
    compactLabel: 'Drill',
    description: 'Question-first NEET-style practice',
    icon: <Swords className="w-4 h-4" />,
  },
];

export function TutorModeSelector({ selectedMode, onChange, isDisabled, compact = false }: TutorModeSelectorProps) {
  if (compact) {
    const activeMode = MODES.find((mode) => mode.mode === selectedMode);

    return (
      <Card className="glass border-border-strong">
        <CardBody className="p-2.5 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>
              Tutor Mode
            </p>
            <p className="text-[11px] font-medium" style={{ color: 'var(--text-secondary)' }}>
              Active: {activeMode?.label ?? 'Guided Learn'}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-1.5">
            {MODES.map((option) => {
              const selected = option.mode === selectedMode;
              return (
                <Button
                  key={option.mode}
                  size="sm"
                  variant={selected ? 'solid' : 'flat'}
                  color={selected ? 'secondary' : 'default'}
                  isDisabled={isDisabled}
                  onPress={() => onChange(option.mode)}
                  className="h-8 min-h-0 justify-center px-2"
                  style={{
                    borderRadius: 'var(--r-md)',
                    border: selected ? '1px solid var(--accent-border)' : '1px solid var(--border-subtle)',
                    background: selected ? 'var(--accent-glow)' : 'var(--bg-2)',
                  }}
                >
                  <span className="inline-flex items-center gap-1" style={{ fontSize: 11, fontWeight: 600 }}>
                    {option.icon}
                    {option.compactLabel}
                  </span>
                </Button>
              );
            })}
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card className="glass border-border-strong">
      <CardBody className="p-3.5 space-y-3">
        <div>
          <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>
            Tutor Mode
          </p>
          <h2 className="ui-section-title mt-1" style={{ fontSize: 14 }}>
            Choose Your Session Style
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {MODES.map((option) => {
            const selected = option.mode === selectedMode;
            return (
              <Button
                key={option.mode}
                variant={selected ? 'solid' : 'flat'}
                color={selected ? 'secondary' : 'default'}
                isDisabled={isDisabled}
                onPress={() => onChange(option.mode)}
                className="h-auto min-h-[72px] justify-start"
                style={{
                  borderRadius: 'var(--r-md)',
                  border: selected ? '1px solid var(--accent-border)' : '1px solid var(--border-subtle)',
                  background: selected ? 'var(--accent-glow)' : 'var(--bg-2)',
                  padding: '9px 11px',
                }}
              >
                <div className="w-full text-left space-y-0.5">
                  <div className="flex items-center gap-1.5" style={{ color: selected ? 'var(--accent)' : 'var(--text-secondary)' }}>
                    {option.icon}
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{option.label}</span>
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'normal', lineHeight: 1.35 }}>
                    {option.description}
                  </p>
                </div>
              </Button>
            );
          })}
        </div>
      </CardBody>
    </Card>
  );
}
