import { Button, Card, CardBody, Chip, Slider, Textarea } from '@heroui/react';
import { Brain, CheckCircle2 } from 'lucide-react';

interface CheckpointPulseCardProps {
  conceptKey: string;
  prompt: string;
  responseText: string;
  confidence: number;
  isSubmitting?: boolean;
  onResponseChange: (value: string) => void;
  onConfidenceChange: (value: number) => void;
  onSubmit: () => void;
  onSkip: () => void;
}

export function CheckpointPulseCard({
  conceptKey,
  prompt,
  responseText,
  confidence,
  isSubmitting,
  onResponseChange,
  onConfidenceChange,
  onSubmit,
  onSkip,
}: CheckpointPulseCardProps) {
  return (
    <Card className="glass border-border-strong">
      <CardBody className="p-3.5 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Brain className="w-4 h-4" style={{ color: 'var(--accent)' }} />
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>
                Checkpoint Pulse
              </p>
              <p className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                {conceptKey}
              </p>
            </div>
          </div>
          <Chip size="sm" variant="flat" color="secondary" startContent={<CheckCircle2 className="w-3 h-3" />}>
            Quick Check
          </Chip>
        </div>

        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{prompt}</p>

        <Textarea
          aria-label="Checkpoint response"
          minRows={2}
          placeholder="Write your answer in 2-4 lines..."
          value={responseText}
          onValueChange={onResponseChange}
          isDisabled={isSubmitting}
          variant="bordered"
          classNames={{
            inputWrapper: 'border-border-strong hover:border-accent/50 focus-within:!border-accent bg-bg-2',
            input: 'text-text-primary placeholder:text-[#8B7D6D]',
          }}
        />

        <div>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
            Confidence: <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{confidence}</span> / 100
          </label>
          <Slider
            aria-label="Checkpoint confidence"
            step={1}
            minValue={0}
            maxValue={100}
            value={confidence}
            onChange={(value) => onConfidenceChange(value as number)}
            isDisabled={isSubmitting}
            color="secondary"
            classNames={{
              track: 'bg-bg-5 h-[4px] rounded-[var(--r-pill)]',
              filler: 'bg-accent',
              thumb: 'w-[16px] h-[16px] bg-accent border-2 border-white',
            }}
          />
        </div>

        <div className="flex items-center gap-2 justify-end">
          <Button size="sm" variant="flat" onPress={onSkip} isDisabled={isSubmitting}>
            Skip
          </Button>
          <Button
            size="sm"
            color="secondary"
            onPress={onSubmit}
            isLoading={isSubmitting}
            isDisabled={responseText.trim().length < 8}
          >
            Submit Checkpoint
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}
