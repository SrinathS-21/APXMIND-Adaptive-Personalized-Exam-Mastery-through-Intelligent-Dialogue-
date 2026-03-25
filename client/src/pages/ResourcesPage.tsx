import {
  Card,
  CardBody,
  Button,
  Chip,
  Divider,
  Link,
} from '@heroui/react';
import { motion } from 'framer-motion';
import {
  Globe,
  Youtube,
  BookOpen,
  GraduationCap,
  ExternalLink,
} from 'lucide-react';

interface Resource {
  title: string;
  description: string;
  url: string;
  type: 'youtube' | 'website' | 'app';
  subjects: string[];
  free: boolean;
}

const resources: Resource[] = [
  {
    title: 'NCERT Official Website',
    description: 'Official NCERT textbooks and solutions — download PDFs for free',
    url: 'https://ncert.nic.in/textbook.php',
    type: 'website',
    subjects: ['physics', 'chemistry', 'biology'],
    free: true,
  },
  {
    title: 'Physics Wallah (YouTube)',
    description: 'Comprehensive NEET lectures by Alakh Pandey',
    url: 'https://www.youtube.com/@PhysicsWallah',
    type: 'youtube',
    subjects: ['physics', 'chemistry', 'biology'],
    free: true,
  },
  {
    title: 'Unacademy NEET',
    description: 'NEET preparation platform with top educators',
    url: 'https://unacademy.com/goal/neet-ug/YOTUH',
    type: 'website',
    subjects: ['physics', 'chemistry', 'biology'],
    free: false,
  },
  {
    title: 'Khan Academy (Biology)',
    description: 'High-quality biology lectures and practice',
    url: 'https://www.khanacademy.org/science/biology',
    type: 'website',
    subjects: ['biology'],
    free: true,
  },
  {
    title: 'Organic Chemistry — Vedantu (YouTube)',
    description: 'Organic chemistry crash course for NEET',
    url: 'https://www.youtube.com/@VedantuNEET',
    type: 'youtube',
    subjects: ['chemistry'],
    free: true,
  },
  {
    title: 'HC Verma Solutions',
    description: 'Concepts of Physics solutions and discussions',
    url: 'https://www.youtube.com/results?search_query=hc+verma+solutions+neet',
    type: 'youtube',
    subjects: ['physics'],
    free: true,
  },
  {
    title: 'NEET PYQs (NTA)',
    description: 'Previous year question papers from National Testing Agency',
    url: 'https://neet.nta.nic.in/',
    type: 'website',
    subjects: ['physics', 'chemistry', 'biology'],
    free: true,
  },
  {
    title: 'Aakash Digital (YouTube)',
    description: 'NEET concepts and problem-solving by Aakash Institute',
    url: 'https://www.youtube.com/@AakashInstitute',
    type: 'youtube',
    subjects: ['physics', 'chemistry', 'biology'],
    free: true,
  },
  {
    title: 'Allen Career Institute',
    description: 'Study material and test series for NEET',
    url: 'https://www.allen.ac.in/',
    type: 'website',
    subjects: ['physics', 'chemistry', 'biology'],
    free: false,
  },
  {
    title: 'Biology by Shumon Sensei (YouTube)',
    description: 'Animated biology lessons — great for visual learners',
    url: 'https://www.youtube.com/results?search_query=neet+biology+animated',
    type: 'youtube',
    subjects: ['biology'],
    free: true,
  },
  {
    title: 'LearnCBSE NEET',
    description: 'NCERT solutions, notes, and MCQs chapter-wise',
    url: 'https://www.learncbse.in/neet/',
    type: 'website',
    subjects: ['physics', 'chemistry', 'biology'],
    free: true,
  },
];



const subjectColors: Record<string, 'primary' | 'success' | 'secondary'> = {
  physics: 'primary',
  chemistry: 'success',
  biology: 'secondary',
};

const typeIcons: Record<string, React.ReactNode> = {
  youtube: <Youtube className="w-4 h-4 text-red-500" />,
  website: <Globe className="w-4 h-4 text-blue-500" />,
  app: <GraduationCap className="w-4 h-4 text-emerald-500" />,
};

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item = { hidden: { opacity: 0, y: 15 }, show: { opacity: 1, y: 0 } };

export function ResourcesPage() {
  return (
    <motion.div variants={container} initial="hidden" animate="show" className="max-w-4xl mx-auto space-y-5">
      <motion.div variants={item}>
        <h1 className="flex items-center gap-2" style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
          <Globe className="w-6 h-6 text-primary" />
          Learning Resources
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Curated NEET preparation resources from across the internet
        </p>
      </motion.div>

      {/* YouTube channels */}
      <motion.div variants={item}>
        <h2 className="flex items-center gap-2 mb-3" style={{ fontSize: 10, fontWeight: 500, letterSpacing: '0.10em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
          <Youtube className="w-5 h-5 text-red-500" />
          YouTube Channels
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {resources
            .filter((r) => r.type === 'youtube')
            .map((r) => (
              <ResourceCard key={r.url} resource={r} />
            ))}
        </div>
      </motion.div>

      <Divider />

      {/* Websites */}
      <motion.div variants={item}>
        <h2 className="flex items-center gap-2 mb-3" style={{ fontSize: 10, fontWeight: 500, letterSpacing: '0.10em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
          <BookOpen className="w-5 h-5 text-blue-500" />
          Websites & Platforms
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {resources
            .filter((r) => r.type === 'website')
            .map((r) => (
              <ResourceCard key={r.url} resource={r} />
            ))}
        </div>
      </motion.div>
    </motion.div>
  );
}

function ResourceCard({ resource }: { resource: Resource }) {
  return (
    <Card className="glass h-full" style={{ background: 'var(--bg-2)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--r-md)' }}>
      <CardBody className="p-4" style={{ gap: 12 }}>
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <div
              className="flex items-center justify-center shrink-0"
              style={{
                width: 36,
                height: 36,
                borderRadius: 'var(--r-sm)',
                background: resource.type === 'youtube' ? 'var(--red-soft)' : resource.type === 'website' ? 'var(--blue-soft)' : 'var(--amber-soft)',
                fontSize: 15,
              }}
            >
              {typeIcons[resource.type]}
            </div>
            <h3 style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{resource.title}</h3>
          </div>
          {resource.free ? (
            <Chip size="sm" color="success" variant="flat" style={{ borderRadius: 'var(--r-pill)', fontSize: 11, fontWeight: 500, padding: '3px 10px' }}>Free</Chip>
          ) : (
            <Chip size="sm" color="warning" variant="flat" style={{ borderRadius: 'var(--r-pill)', fontSize: 11, fontWeight: 500, padding: '3px 10px' }}>Paid</Chip>
          )}
        </div>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>{resource.description}</p>
        <div className="flex items-center justify-between">
          <div className="flex gap-1">
            {resource.subjects.map((s) => (
              <Chip
                key={s}
                size="sm"
                variant="dot"
                color={subjectColors[s]}
                className="text-[10px]"
                style={{ borderRadius: 'var(--r-pill)', fontSize: 11, fontWeight: 500, padding: '3px 10px' }}
              >
                {s}
              </Chip>
            ))}
          </div>
          <Button
            as={Link}
            href={resource.url}
            isExternal
            size="sm"
            variant="flat"
            color="primary"
            endContent={<ExternalLink className="w-3 h-3" />}
            style={{ color: 'var(--accent)', fontSize: 12, textDecoration: 'none' }}
          >
            Visit
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}
