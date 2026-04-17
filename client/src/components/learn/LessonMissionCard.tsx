import { useState } from 'react';
import { Button, Card, CardBody, Chip, Spinner } from '@heroui/react';
import { CheckCircle2, Clock3, Sparkles, Target } from 'lucide-react';
import type { LessonMissionContext } from '../../lib/learnSessionService';

interface LessonMissionCardProps {
  context: LessonMissionContext | null;
  isLoading?: boolean;
  error?: string | null;
  onUsePrompt?: (prompt: string, mode: string) => void;
  compact?: boolean;
}

const MODE_LABELS: Record<string, string> = {
  guided: 'Guided',
  revision: 'Revision',
  drill: 'Drill',
};

export function LessonMissionCard({
  context,
  isLoading,
  error,
  onUsePrompt,
  compact = false,
}: LessonMissionCardProps) {
  const [showDetails, setShowDetails] = useState(false);

  if (isLoading) {
    return (
      <Card className="glass border-border-strong">
        <CardBody className={`${compact ? 'p-3' : 'p-4'} flex items-center justify-center`}>
          <Spinner size="sm" color="secondary" label="Loading lesson mission" />
        </CardBody>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="glass border-border-strong">
        <CardBody className={`${compact ? 'p-3' : 'p-4'} space-y-1`}>
          <h2 className="ui-section-title" style={{ fontSize: 14 }}>
            Lesson Mission
          </h2>
          <p style={{ fontSize: 12, color: 'var(--red)' }}>{error}</p>
        </CardBody>
      </Card>
    );
  }

  if (!context) {
    return (
      <Card className="glass border-border-strong">
        <CardBody className={`${compact ? 'p-3' : 'p-4'} space-y-1`}>
          <h2 className="ui-section-title" style={{ fontSize: 14 }}>
            Lesson Mission
          </h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Open a lesson to unlock a mission plan and smart starter prompts.
          </p>
        </CardBody>
      </Card>
    );
  }

  const focusTopics = compact ? context.focus_topics.slice(0, 4) : context.focus_topics;
  const starterEntries = Object.entries(context.starter_prompts);

  return (
    <Card className="glass border-border-strong">
      <CardBody className={compact ? 'p-3 space-y-2.5' : 'p-3.5 space-y-3'}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <Target className="w-4 h-4" style={{ color: 'var(--accent)' }} />
              <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>
                Lesson Mission
              </p>
            </div>
            <h2 className="ui-section-title mt-1" style={{ fontSize: 15 }}>
              {context.mission_title}
            </h2>
            {!compact && context.lesson_description ? (
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                {context.lesson_description}
              </p>
            ) : null}
          </div>

          <Chip
            size="sm"
            color={context.is_completed ? 'success' : 'warning'}
            variant="flat"
            startContent={context.is_completed ? <CheckCircle2 className="w-3 h-3" /> : <Sparkles className="w-3 h-3" />}
          >
            {context.is_completed ? 'Completed' : 'Active'}
          </Chip>
        </div>

        <div className="flex flex-wrap gap-1.5">
          <Chip size="sm" variant="flat" color="secondary">
            {context.difficulty}
          </Chip>
          <Chip size="sm" variant="flat" startContent={<Clock3 className="w-3 h-3" />}>
            {context.estimated_minutes} min
          </Chip>
          <Chip size="sm" variant="flat">
            {context.subject_display_name}
          </Chip>
          {compact && focusTopics[0] ? (
            <Chip size="sm" variant="flat" color="default" className="max-w-[220px]">
              {focusTopics[0]}
            </Chip>
          ) : null}
        </div>

        {compact ? (
          <>
            {(context.mission_objectives.length > 0 || starterEntries.length > 0) ? (
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                  Mission details and smart starters are hidden by default.
                </p>
                <Button
                  size="sm"
                  variant="light"
                  color="secondary"
                  onPress={() => setShowDetails((prev) => !prev)}
                >
                  {showDetails ? 'Hide Details' : 'Show Details'}
                </Button>
              </div>
            ) : null}

            {showDetails ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-2.5">
                <div className="rounded-md p-2.5" style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-2)' }}>
                  <p style={{ fontSize: 11, color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Objectives
                  </p>
                  <ul className="mt-1 space-y-1">
                    {context.mission_objectives.map((objective) => (
                      <li key={objective} style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        - {objective}
                      </li>
                    ))}
                  </ul>
                </div>

                {onUsePrompt && starterEntries.length ? (
                  <div className="rounded-md p-2.5" style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-2)' }}>
                    <p style={{ fontSize: 11, color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6 }}>
                      Smart Starters
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {starterEntries.map(([mode, prompt]) => (
                        <Button
                          key={mode}
                          size="sm"
                          variant="flat"
                          color="secondary"
                          onPress={() => onUsePrompt(prompt, mode)}
                        >
                          {MODE_LABELS[mode] ?? mode}
                        </Button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-md p-2.5" style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-2)' }}>
                    <p style={{ fontSize: 11, color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      Focus Topics
                    </p>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {focusTopics.map((topic) => (
                        <Chip key={topic} size="sm" variant="dot" color="secondary">
                          {topic}
                        </Chip>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </>
        ) : (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <div className="rounded-md p-2.5" style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-2)' }}>
                <p style={{ fontSize: 11, color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Objectives
                </p>
                <ul className="mt-1 space-y-1">
                  {context.mission_objectives.map((objective) => (
                    <li key={objective} style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      - {objective}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-md p-2.5" style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-2)' }}>
                <p style={{ fontSize: 11, color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Focus Topics
                </p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {focusTopics.map((topic) => (
                    <Chip key={topic} size="sm" variant="dot" color="secondary">
                      {topic}
                    </Chip>
                  ))}
                </div>
              </div>
            </div>

            {onUsePrompt ? (
              <div>
                <p style={{ fontSize: 11, color: 'var(--text-faint)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Smart Starters
                </p>
                <div className="flex flex-wrap gap-2">
                  {starterEntries.map(([mode, prompt]) => (
                    <Button
                      key={mode}
                      size="sm"
                      variant="flat"
                      color="secondary"
                      onPress={() => onUsePrompt(prompt, mode)}
                    >
                      {MODE_LABELS[mode] ?? mode}
                    </Button>
                  ))}
                </div>
              </div>
            ) : null}
          </>
        )}
      </CardBody>
    </Card>
  );
}
