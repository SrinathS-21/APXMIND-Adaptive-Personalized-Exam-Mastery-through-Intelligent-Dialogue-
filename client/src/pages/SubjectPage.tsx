import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  CardBody,
  Button,
  Chip,
  Spinner,
  Breadcrumbs,
  BreadcrumbItem,
  Input,
} from '@heroui/react';
import { motion } from 'framer-motion';
import {
  Play,
  BrainCircuit,
  Clock,
  Search,
  SlidersHorizontal,
  Atom,
  FlaskConical,
  Dna,
  BookOpen,
} from 'lucide-react';
import { getSubjectLessons, type Lesson } from '../lib/subjectService';

type LessonViewSize = 'small' | 'medium' | 'large';

const LESSON_VIEW_STORAGE_KEY = 'APXMIND_subject_lesson_view_v1';

const subjectMeta: Record<string, { icon: React.ReactNode; color: 'primary' | 'success' | 'secondary'; label: string }> = {
  physics: { icon: <Atom className="w-5 h-5" />, color: 'primary', label: 'Physics' },
  chemistry: { icon: <FlaskConical className="w-5 h-5" />, color: 'success', label: 'Chemistry' },
  biology: { icon: <Dna className="w-5 h-5" />, color: 'secondary', label: 'Biology' },
};

const difficultyColor: Record<string, 'success' | 'warning' | 'danger'> = {
  easy: 'success',
  medium: 'warning',
  hard: 'danger',
};

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item = { hidden: { opacity: 0, y: 15 }, show: { opacity: 1, y: 0 } };

const KEYWORD_STOPWORDS = new Set([
  'and',
  'the',
  'for',
  'with',
  'from',
  'that',
  'this',
  'into',
  'about',
  'lesson',
  'chapter',
  'topic',
]);

function normalizeKeyword(raw: string): string | null {
  const cleaned = raw.trim();
  if (!cleaned) return null;
  if (/^\+\d+$/.test(cleaned)) return null;
  return cleaned
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function deriveKeywordsFromText(text: string, limit = 8): string[] {
  const words = text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .map((w) => w.trim())
    .filter((w) => w.length >= 3 && !KEYWORD_STOPWORDS.has(w) && !/^\d+$/.test(w));

  const seen = new Set<string>();
  const picked: string[] = [];
  for (const word of words) {
    if (seen.has(word)) continue;
    seen.add(word);
    picked.push(word);
    if (picked.length >= limit) break;
  }
  return picked;
}

function getLessonKeywords(lesson: Lesson): string[] {
  const cleanedTopics = (lesson.topics || [])
    .map(normalizeKeyword)
    .filter((v): v is string => Boolean(v));

  if (cleanedTopics.length > 0) {
    const seen = new Set<string>();
    const deduped: string[] = [];
    for (const topic of cleanedTopics) {
      const key = topic.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      deduped.push(topic);
    }
    return deduped;
  }

  return deriveKeywordsFromText(`${lesson.title} ${lesson.description || ''}`);
}

export function SubjectPage() {
  const { subject } = useParams<{ subject: string }>();
  const navigate = useNavigate();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [viewSize, setViewSize] = useState<LessonViewSize>(() => {
    if (typeof window === 'undefined') return 'medium';
    const raw = window.localStorage.getItem(LESSON_VIEW_STORAGE_KEY);
    if (raw === 'small' || raw === 'medium' || raw === 'large') return raw;
    return 'medium';
  });

  const meta = subjectMeta[subject || ''] || subjectMeta.physics;

  useEffect(() => {
    if (!subject) return;
    setLoading(true);
    setError(null);
    getSubjectLessons(subject)
      .then((res) => {
        if (res.success && res.data) setLessons(res.data);
        else setError('Failed to load lessons');
      })
      .catch(() => setError('Network error — check your connection'))
      .finally(() => setLoading(false));
  }, [subject]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(LESSON_VIEW_STORAGE_KEY, viewSize);
  }, [viewSize]);

  const filtered = lessons.filter((l) => {
    const needle = search.toLowerCase();
    const keywords = getLessonKeywords(l);
    return (
      l.title.toLowerCase().includes(needle) ||
      keywords.some((k) => k.toLowerCase().includes(needle))
    );
  });

  function cycleViewSize() {
    setViewSize((prev) => (prev === 'small' ? 'medium' : prev === 'medium' ? 'large' : 'small'));
  }

  const layoutClass =
    viewSize === 'small'
      ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5'
      : viewSize === 'large'
        ? 'grid grid-cols-1 gap-4'
        : 'grid grid-cols-1 md:grid-cols-2 gap-3';

  const cardPaddingClass = viewSize === 'large' ? 'p-4' : viewSize === 'small' ? 'p-2.5' : 'p-3';
  const titleClass = viewSize === 'large' ? 'text-lg font-semibold truncate' : viewSize === 'small' ? 'text-sm font-semibold truncate' : 'text-md font-semibold truncate';
  const descriptionClass = viewSize === 'large' ? 'text-sm text-default-600 line-clamp-2 mb-2.5' : 'text-sm text-default-500 line-clamp-1 mb-2';
  const showDescription = viewSize !== 'small';
  const keywordAreaClass = viewSize === 'large' ? 'max-h-[84px]' : viewSize === 'small' ? 'max-h-[64px]' : 'max-h-[74px]';
  const playBadgeSizeClass = viewSize === 'large' ? 'min-w-unit-10 h-unit-10' : viewSize === 'small' ? 'min-w-unit-7 h-unit-7' : 'min-w-unit-8 h-unit-8';
  const playIconClass = viewSize === 'large' ? 'w-5 h-5' : viewSize === 'small' ? 'w-3.5 h-3.5' : 'w-4 h-4';

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      {/* Breadcrumbs */}
      <Breadcrumbs aria-label="Subject page breadcrumbs">
        <BreadcrumbItem onPress={() => navigate('/home')}>Home</BreadcrumbItem>
        <BreadcrumbItem>{meta.label}</BreadcrumbItem>
      </Breadcrumbs>

      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className="ui-icon-badge"
            style={{
              background: meta.color === 'primary' ? 'var(--blue-soft)' : meta.color === 'success' ? 'var(--green-soft)' : 'var(--purple-soft)',
              color: meta.color === 'primary' ? 'var(--blue)' : meta.color === 'success' ? 'var(--green)' : 'var(--purple)',
            }}
          >
            {meta.icon}
          </div>
          <div>
            <h1 className="ui-page-title">{meta.label}</h1>
            <p className="ui-page-subtitle mt-0">{lessons.length} lessons available</p>
          </div>
        </div>
        <Button
          color={meta.color}
          variant="flat"
          startContent={<BrainCircuit className="w-4 h-4" />}
          onPress={() => {
            if (lessons[0]) navigate(`/subject/${subject}/lesson/${lessons[0].id}/quiz`);
          }}
        >
          Quick Quiz
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <Input
          aria-label="Search lessons"
          placeholder="Search lessons or topics..."
          value={search}
          onValueChange={setSearch}
          startContent={<Search className="w-4 h-4 text-text-faint" />}
          variant="bordered"
          size="sm"
          classNames={{
            inputWrapper: 'border-border-default hover:border-accent/50 focus-within:!border-accent bg-bg-2 pr-10',
            input: 'text-text-primary placeholder:text-text-faint',
          }}
        />
        <button
          type="button"
          aria-label={`Change lesson view size (current: ${viewSize})`}
          title={`View: ${viewSize}. Click to switch size.`}
          onClick={cycleViewSize}
          className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex items-center justify-center rounded-md border border-border-default bg-bg-1 text-text-secondary h-7 w-7 transition-colors hover:bg-bg-2 hover:text-text-primary"
        >
          <SlidersHorizontal className="w-4 h-4" />
        </button>
      </div>

      {/* Lessons list */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner color={meta.color} size="lg" label="Loading lessons..." />
        </div>
      ) : error ? (
        <Card className="glass border-danger/30">
          <CardBody className="text-center py-12">
            <p className="text-danger font-medium mb-2">{error}</p>
            <Button size="sm" variant="flat" color="danger" onPress={() => window.location.reload()}>
              Retry
            </Button>
          </CardBody>
        </Card>
      ) : filtered.length === 0 ? (
        <Card className="glass">
          <CardBody className="text-center py-12">
            <BookOpen className="w-10 h-10 mx-auto text-default-300 mb-3" />
            <p className="text-default-500">{search ? 'No matching lessons found' : 'No lessons yet'}</p>
          </CardBody>
        </Card>
      ) : (
        <motion.div variants={container} initial="hidden" animate="show" className={layoutClass}>
          {filtered.map((lesson) => (
            <motion.div key={lesson.id} variants={item} className="w-full">
              <Card
                isPressable
                onPress={() => navigate(`/subject/${subject}/lesson/${lesson.id}/learn`)}
                className="glass w-full hover:border-border-strong transition-all duration-200 hover:scale-[1.01]"
              >
                <CardBody className={cardPaddingClass}>
                  <div className="flex items-start justify-between gap-2.5">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-default-400 font-mono">#{lesson.order}</span>
                        <h3 className={titleClass}>{lesson.title}</h3>
                      </div>
                      {showDescription && lesson.description && (
                        <p className={descriptionClass}>{lesson.description}</p>
                      )}
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        <Chip size="sm" color={difficultyColor[lesson.difficulty] || 'default'} variant="flat">
                          {lesson.difficulty}
                        </Chip>
                        <Chip size="sm" variant="flat" startContent={<Clock className="w-3 h-3" />}>
                          {lesson.estimated_time}m
                        </Chip>
                      </div>

                      <div className={`${keywordAreaClass} overflow-y-auto pr-1`} style={{ scrollbarGutter: 'stable' }}>
                        <div className="flex flex-wrap gap-1.5">
                          {getLessonKeywords(lesson).map((topic) => (
                            <Chip key={topic} size="sm" variant="dot" color={meta.color}>
                              {topic}
                            </Chip>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-col gap-1 shrink-0">
                      <div
                        className={`inline-flex items-center justify-center rounded-small px-0 ${playBadgeSizeClass} ${meta.color === 'primary'
                          ? 'bg-primary/20 text-primary'
                          : meta.color === 'success'
                            ? 'bg-success/20 text-success'
                            : 'bg-secondary/20 text-secondary'
                          }`}
                        aria-hidden="true"
                      >
                        <Play className={playIconClass} />
                      </div>
                    </div>
                  </div>
                </CardBody>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
