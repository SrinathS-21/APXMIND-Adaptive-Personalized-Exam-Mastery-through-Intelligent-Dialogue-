import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardBody,
  Chip,
  Accordion,
  AccordionItem,
} from '@heroui/react';
import { motion } from 'framer-motion';
import { BookOpen, Atom, FlaskConical, Dna, ExternalLink } from 'lucide-react';
import { useProfileStore } from '../store/profileStore';
import { tUi } from '../lib/uiI18n';

interface BookChapter {
  title: string;
  pdfFile: string;
}

interface BookEntry {
  classLevel: string;
  subject: string;
  chapters: BookChapter[];
}

// NCERT book catalog — paths relative to data/raw/NCRTBooks/
const bookCatalog: BookEntry[] = [
  // ── Physics Class 11 ──────────────────────────────────────────────
  {
    classLevel: '11',
    subject: 'physics',
    chapters: [
      { title: 'Chapter 1: Physical World', pdfFile: 'Physics/11Physics1/keph101.pdf' },
      { title: 'Chapter 2: Units and Measurements', pdfFile: 'Physics/11Physics1/keph102.pdf' },
      { title: 'Chapter 3: Motion in a Straight Line', pdfFile: 'Physics/11Physics1/keph103.pdf' },
      { title: 'Chapter 4: Motion in a Plane', pdfFile: 'Physics/11Physics1/keph104.pdf' },
      { title: 'Chapter 5: Laws of Motion', pdfFile: 'Physics/11Physics1/keph105.pdf' },
      { title: 'Chapter 6: Work, Energy and Power', pdfFile: 'Physics/11Physics1/keph106.pdf' },
      { title: 'Chapter 7: System of Particles', pdfFile: 'Physics/11Physics1/keph107.pdf' },
      { title: 'Chapter 8: Mechanical Properties of Solids', pdfFile: 'Physics/11Physics2/keph201.pdf' },
      { title: 'Chapter 9: Mechanical Properties of Fluids', pdfFile: 'Physics/11Physics2/keph202.pdf' },
      { title: 'Chapter 10: Thermal Properties of Matter', pdfFile: 'Physics/11Physics2/keph203.pdf' },
      { title: 'Chapter 11: Thermodynamics', pdfFile: 'Physics/11Physics2/keph204.pdf' },
      { title: 'Chapter 12: Kinetic Theory', pdfFile: 'Physics/11Physics2/keph205.pdf' },
      { title: 'Chapter 13: Oscillations', pdfFile: 'Physics/11Physics2/keph206.pdf' },
      { title: 'Chapter 14: Waves', pdfFile: 'Physics/11Physics2/keph207.pdf' },
    ],
  },
  // ── Physics Class 12 ──────────────────────────────────────────────
  {
    classLevel: '12',
    subject: 'physics',
    chapters: [
      { title: 'Chapter 1: Electric Charges and Fields', pdfFile: 'Physics/12Physics1/leph101.pdf' },
      { title: 'Chapter 2: Electrostatic Potential and Capacitance', pdfFile: 'Physics/12Physics1/leph102.pdf' },
      { title: 'Chapter 3: Current Electricity', pdfFile: 'Physics/12Physics1/leph103.pdf' },
      { title: 'Chapter 4: Moving Charges and Magnetism', pdfFile: 'Physics/12Physics1/leph104.pdf' },
      { title: 'Chapter 5: Magnetism and Matter', pdfFile: 'Physics/12Physics1/leph105.pdf' },
      { title: 'Chapter 6: Electromagnetic Induction', pdfFile: 'Physics/12Physics1/leph106.pdf' },
      { title: 'Chapter 7: Alternating Current', pdfFile: 'Physics/12Physics1/leph107.pdf' },
      { title: 'Chapter 8: Electromagnetic Waves', pdfFile: 'Physics/12Physics1/leph108.pdf' },
      { title: 'Chapter 9: Ray Optics and Optical Instruments', pdfFile: 'Physics/12Physics2/leph201.pdf' },
      { title: 'Chapter 10: Wave Optics', pdfFile: 'Physics/12Physics2/leph202.pdf' },
      { title: 'Chapter 11: Dual Nature of Radiation and Matter', pdfFile: 'Physics/12Physics2/leph203.pdf' },
      { title: 'Chapter 12: Atoms', pdfFile: 'Physics/12Physics2/leph204.pdf' },
      { title: 'Chapter 13: Nuclei', pdfFile: 'Physics/12Physics2/leph205.pdf' },
      { title: 'Chapter 14: Semiconductor Electronics', pdfFile: 'Physics/12Physics2/leph206.pdf' },
    ],
  },
  // ── Chemistry Class 11 ────────────────────────────────────────────
  {
    classLevel: '11',
    subject: 'chemistry',
    chapters: [
      { title: 'Chapter 1: Some Basic Concepts of Chemistry', pdfFile: 'chemistry/11ChemPart1/kech101.pdf' },
      { title: 'Chapter 2: Structure of Atom', pdfFile: 'chemistry/11ChemPart1/kech102.pdf' },
      { title: 'Chapter 3: Classification of Elements and Periodicity', pdfFile: 'chemistry/11ChemPart1/kech103.pdf' },
      { title: 'Chapter 4: Chemical Bonding and Molecular Structure', pdfFile: 'chemistry/11ChemPart1/kech104.pdf' },
      { title: 'Chapter 5: Thermodynamics', pdfFile: 'chemistry/11ChemPart1/kech105.pdf' },
      { title: 'Chapter 6: Equilibrium', pdfFile: 'chemistry/11ChemPart1/kech106.pdf' },
      { title: 'Chapter 7: Redox Reactions', pdfFile: 'chemistry/11ChemPart2/kech201.pdf' },
      { title: 'Chapter 8: Organic Chemistry — Some Basic Principles', pdfFile: 'chemistry/11ChemPart2/kech202.pdf' },
      { title: 'Chapter 9: Hydrocarbons', pdfFile: 'chemistry/11ChemPart2/kech203.pdf' },
    ],
  },
  // ── Chemistry Class 12 ────────────────────────────────────────────
  {
    classLevel: '12',
    subject: 'chemistry',
    chapters: [
      { title: 'Chapter 1: Solutions', pdfFile: 'chemistry/12ChemPart1/lech101.pdf' },
      { title: 'Chapter 2: Electrochemistry', pdfFile: 'chemistry/12ChemPart1/lech102.pdf' },
      { title: 'Chapter 3: Chemical Kinetics', pdfFile: 'chemistry/12ChemPart1/lech103.pdf' },
      { title: 'Chapter 4: d- and f-Block Elements', pdfFile: 'chemistry/12ChemPart1/lech104.pdf' },
      { title: 'Chapter 5: Coordination Compounds', pdfFile: 'chemistry/12ChemPart1/lech105.pdf' },
      { title: 'Chapter 6: Haloalkanes and Haloarenes', pdfFile: 'chemistry/12ChemPart2/lech201.pdf' },
      { title: 'Chapter 7: Alcohols, Phenols and Ethers', pdfFile: 'chemistry/12ChemPart2/lech202.pdf' },
      { title: 'Chapter 8: Aldehydes, Ketones and Carboxylic Acids', pdfFile: 'chemistry/12ChemPart2/lech203.pdf' },
      { title: 'Chapter 9: Amines', pdfFile: 'chemistry/12ChemPart2/lech204.pdf' },
      { title: 'Chapter 10: Biomolecules', pdfFile: 'chemistry/12ChemPart2/lech205.pdf' },
    ],
  },
  // ── Biology Class 11 ──────────────────────────────────────────────
  {
    classLevel: '11',
    subject: 'biology',
    chapters: [
      { title: 'Chapter 1: The Living World', pdfFile: 'Biology/11Bio1/kebo101.pdf' },
      { title: 'Chapter 2: Biological Classification', pdfFile: 'Biology/11Bio1/kebo102.pdf' },
      { title: 'Chapter 3: Plant Kingdom', pdfFile: 'Biology/11Bio1/kebo103.pdf' },
      { title: 'Chapter 4: Animal Kingdom', pdfFile: 'Biology/11Bio1/kebo104.pdf' },
      { title: 'Chapter 5: Morphology of Flowering Plants', pdfFile: 'Biology/11Bio1/kebo105.pdf' },
      { title: 'Chapter 6: Anatomy of Flowering Plants', pdfFile: 'Biology/11Bio1/kebo106.pdf' },
      { title: 'Chapter 7: Structural Organisation in Animals', pdfFile: 'Biology/11Bio1/kebo107.pdf' },
      { title: 'Chapter 8: Cell — The Unit of Life', pdfFile: 'Biology/11Bio1/kebo108.pdf' },
      { title: 'Chapter 9: Biomolecules', pdfFile: 'Biology/11Bio1/kebo109.pdf' },
      { title: 'Chapter 10: Cell Cycle and Cell Division', pdfFile: 'Biology/11Bio1/kebo110.pdf' },
      { title: 'Chapter 11: Photosynthesis in Higher Plants', pdfFile: 'Biology/11Bio1/kebo111.pdf' },
      { title: 'Chapter 12: Respiration in Plants', pdfFile: 'Biology/11Bio1/kebo112.pdf' },
      { title: 'Chapter 13: Plant Growth and Development', pdfFile: 'Biology/11Bio1/kebo113.pdf' },
      { title: 'Chapter 14: Breathing and Exchange of Gases', pdfFile: 'Biology/11Bio1/kebo114.pdf' },
      { title: 'Chapter 15: Body Fluids and Circulation', pdfFile: 'Biology/11Bio1/kebo115.pdf' },
      { title: 'Chapter 16: Excretory Products and Elimination', pdfFile: 'Biology/11Bio1/kebo116.pdf' },
      { title: 'Chapter 17: Locomotion and Movement', pdfFile: 'Biology/11Bio1/kebo117.pdf' },
      { title: 'Chapter 18: Neural Control and Coordination', pdfFile: 'Biology/11Bio1/kebo118.pdf' },
      { title: 'Chapter 19: Chemical Coordination and Integration', pdfFile: 'Biology/11Bio1/kebo119.pdf' },
    ],
  },
  // ── Biology Class 12 ──────────────────────────────────────────────
  {
    classLevel: '12',
    subject: 'biology',
    chapters: [
      { title: 'Chapter 1: Reproduction in Organisms', pdfFile: 'Biology/12Bio1/lebo101.pdf' },
      { title: 'Chapter 2: Sexual Reproduction in Flowering Plants', pdfFile: 'Biology/12Bio1/lebo102.pdf' },
      { title: 'Chapter 3: Human Reproduction', pdfFile: 'Biology/12Bio1/lebo103.pdf' },
      { title: 'Chapter 4: Reproductive Health', pdfFile: 'Biology/12Bio1/lebo104.pdf' },
      { title: 'Chapter 5: Principles of Inheritance and Variation', pdfFile: 'Biology/12Bio1/lebo105.pdf' },
      { title: 'Chapter 6: Molecular Basis of Inheritance', pdfFile: 'Biology/12Bio1/lebo106.pdf' },
      { title: 'Chapter 7: Evolution', pdfFile: 'Biology/12Bio1/lebo107.pdf' },
      { title: 'Chapter 8: Human Health and Disease', pdfFile: 'Biology/12Bio1/lebo108.pdf' },
      { title: 'Chapter 9: Strategies for Enhancement in Food Production', pdfFile: 'Biology/12Bio1/lebo109.pdf' },
      { title: 'Chapter 10: Microbes in Human Welfare', pdfFile: 'Biology/12Bio1/lebo110.pdf' },
      { title: 'Chapter 11: Biotechnology — Principles and Processes', pdfFile: 'Biology/12Bio1/lebo111.pdf' },
      { title: 'Chapter 12: Biotechnology and Its Applications', pdfFile: 'Biology/12Bio1/lebo112.pdf' },
      { title: 'Chapter 13: Organisms and Populations', pdfFile: 'Biology/12Bio1/lebo113.pdf' },
    ],
  },
];

const subjectMeta: Record<string, { icon: React.ReactNode; color: string }> = {
  physics: { icon: <Atom className="w-5 h-5" />, color: 'text-blue-500' },
  chemistry: { icon: <FlaskConical className="w-5 h-5" />, color: 'text-emerald-500' },
  biology: { icon: <Dna className="w-5 h-5" />, color: 'text-purple-500' },
};

const selectedSubjectChipStyle = {
  background: 'var(--accent)',
  color: '#ffffff',
  border: 'none',
  borderRadius: 'var(--r-pill)',
  padding: '5px 16px',
  fontSize: 12,
  fontWeight: 500,
} as const;

const defaultSubjectChipStyle = {
  background: 'var(--bg-3)',
  color: 'var(--text-muted)',
  border: '1px solid var(--border-subtle)',
  borderRadius: 'var(--r-pill)',
  padding: '5px 16px',
  fontSize: 12,
} as const;

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 15 }, show: { opacity: 1, y: 0 } };

export function BooksPage() {
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
  const navigate = useNavigate();
  const language = useProfileStore((s) => s.profile?.preferredLanguage);
  const t = (key: string, vars?: Record<string, string | number>) => tUi(language, key, vars);

  const subjects = ['physics', 'chemistry', 'biology'];

  const filteredCatalog = selectedSubject
    ? bookCatalog.filter((b) => b.subject === selectedSubject)
    : bookCatalog;

  function handleOpenBook(pdfFile: string) {
    // Books will be served via backend API
    // For now navigate to a reader page
    const encoded = encodeURIComponent(pdfFile);
    navigate(`/books/reader?file=${encoded}`);
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="max-w-4xl mx-auto space-y-5 md:pt-4 lg:pt-6">
      <motion.div variants={item}>
        <h1 className="ui-page-title">
          <BookOpen className="w-6 h-6 text-success" />
          {t('books.title')}
        </h1>
        <p className="ui-page-subtitle">
          {t('books.subtitle')}
        </p>
      </motion.div>

      {/* Subject filter */}
      <motion.div variants={item} className="flex gap-2 flex-wrap">
        <Chip
          variant={selectedSubject === null ? 'solid' : 'bordered'}
          color="default"
          className="cursor-pointer"
          style={selectedSubject === null ? selectedSubjectChipStyle : defaultSubjectChipStyle}
          onClick={() => setSelectedSubject(null)}
        >
          {t('books.allSubjects')}
        </Chip>
        {subjects.map((s) => (
          <Chip
            key={s}
            variant={selectedSubject === s ? 'solid' : 'bordered'}
            color={s === 'physics' ? 'primary' : s === 'chemistry' ? 'success' : 'secondary'}
            className="cursor-pointer capitalize"
            style={selectedSubject === s ? selectedSubjectChipStyle : defaultSubjectChipStyle}
            onClick={() => setSelectedSubject(s === selectedSubject ? null : s)}
          >
            {t(`home.subject.${s}.label`)}
          </Chip>
        ))}
      </motion.div>

      {/* Book list */}
      <motion.div variants={item}>
        <Accordion variant="bordered" selectionMode="multiple">
          {filteredCatalog.map((book, idx) => {
            const meta = subjectMeta[book.subject];
            const subjectLabel = t(`home.subject.${book.subject}.label`);
            return (
              <AccordionItem
                key={`${book.subject}-${book.classLevel}-${idx}`}
                title={
                  <div className="flex items-center gap-2">
                    <span className={meta.color}>{meta.icon}</span>
                    <span className="font-semibold">
                      {t('books.classSubject', { classLevel: book.classLevel, subject: subjectLabel })}
                    </span>
                    <Chip size="sm" variant="flat" className="ui-pill ui-chip-neutral">{t('books.chapterCount', { count: book.chapters.length })}</Chip>
                  </div>
                }
              >
                <div className="space-y-2 pb-2">
                  {book.chapters.map((ch) => (
                    <Card
                      key={ch.pdfFile}
                      isPressable
                      onPress={() => handleOpenBook(ch.pdfFile)}
                      className="transition-colors"
                      style={{
                        background: 'var(--bg-2)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--r-md)',
                        padding: 0,
                        marginBottom: 8,
                      }}
                    >
                      <CardBody className="p-3 flex flex-row items-center justify-between">
                        <div className="flex items-center gap-2">
                          <BookOpen className="w-4 h-4" style={{ color: 'var(--text-faint)' }} />
                          <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{ch.title}</span>
                        </div>
                        <span
                          aria-hidden="true"
                          className="inline-flex items-center justify-center h-8 w-8 rounded-(--r-sm)"
                          style={{ color: 'var(--text-faint)' }}
                        >
                          <ExternalLink className="w-3 h-3" />
                        </span>
                      </CardBody>
                    </Card>
                  ))}
                </div>
              </AccordionItem>
            );
          })}
        </Accordion>
      </motion.div>
    </motion.div>
  );
}
