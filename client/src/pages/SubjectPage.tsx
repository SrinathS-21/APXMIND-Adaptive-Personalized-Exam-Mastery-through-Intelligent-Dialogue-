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
  Atom,
  FlaskConical,
  Dna,
  BookOpen,
} from 'lucide-react';
import { getSubjectLessons, type Lesson } from '../lib/subjectService';

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

export function SubjectPage() {
  const { subject } = useParams<{ subject: string }>();
  const navigate = useNavigate();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

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

  const filtered = lessons.filter(
    (l) =>
      l.title.toLowerCase().includes(search.toLowerCase()) ||
      l.topics?.some((t) => t.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      {/* Breadcrumbs */}
      <Breadcrumbs aria-label="Subject page breadcrumbs">
        <BreadcrumbItem onPress={() => navigate('/dashboard')}>Dashboard</BreadcrumbItem>
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
      <Input
        aria-label="Search lessons"
        placeholder="Search lessons or topics..."
        value={search}
        onValueChange={setSearch}
        startContent={<Search className="w-4 h-4 text-text-faint" />}
        variant="bordered"
        size="sm"
        isClearable
        onClear={() => setSearch('')}
        classNames={{
          inputWrapper: 'border-border-default hover:border-accent/50 focus-within:!border-accent bg-bg-2',
          input: 'text-text-primary placeholder:text-text-faint',
        }}
      />

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
        <motion.div variants={container} initial="hidden" animate="show" className="space-y-3">
          {filtered.map((lesson) => (
            <motion.div key={lesson.id} variants={item}>
              <Card
                isPressable
                onPress={() => navigate(`/subject/${subject}/lesson/${lesson.id}/learn`)}
                className="glass hover:border-border-strong transition-all duration-200 hover:scale-[1.01]"
              >
                <CardBody className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-default-400 font-mono">#{lesson.order}</span>
                        <h3 className="text-md font-semibold truncate">{lesson.title}</h3>
                      </div>
                      {lesson.description && (
                        <p className="text-sm text-default-500 line-clamp-1 mb-2">{lesson.description}</p>
                      )}
                      <div className="flex flex-wrap gap-1.5">
                        <Chip size="sm" color={difficultyColor[lesson.difficulty] || 'default'} variant="flat">
                          {lesson.difficulty}
                        </Chip>
                        <Chip size="sm" variant="flat" startContent={<Clock className="w-3 h-3" />}>
                          {lesson.estimated_time}m
                        </Chip>
                        {lesson.topics?.slice(0, 3).map((t) => (
                          <Chip key={t} size="sm" variant="dot" color={meta.color}>
                            {t}
                          </Chip>
                        ))}
                        {(lesson.topics?.length || 0) > 3 && (
                          <Chip size="sm" variant="flat">+{lesson.topics!.length - 3}</Chip>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col gap-1 shrink-0">
                      <div
                        className={`inline-flex items-center justify-center rounded-small min-w-unit-8 h-unit-8 px-0 ${
                          meta.color === 'primary'
                            ? 'bg-primary/20 text-primary'
                            : meta.color === 'success'
                              ? 'bg-success/20 text-success'
                              : 'bg-secondary/20 text-secondary'
                        }`}
                        aria-hidden="true"
                      >
                        <Play className="w-4 h-4" />
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
