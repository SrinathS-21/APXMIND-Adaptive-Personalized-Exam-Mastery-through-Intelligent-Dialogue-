import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Input,
  Spinner,
  Breadcrumbs,
  BreadcrumbItem,
  Chip,
  Divider,
} from '@heroui/react';
import { motion } from 'framer-motion';
import { Send, Bot, User, Sparkles, ArrowLeft, BrainCircuit } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { processQuery } from '../lib/queryService';
import { useGamificationStore } from '../store/gamificationStore';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tier?: string;
  timestamp: Date;
}

export function LearnPage() {
  const { subject, lessonId } = useParams<{ subject: string; lessonId: string }>();
  const navigate = useNavigate();
  const { recordStudySession, addXP, recordSubjectStudied } = useGamificationStore();

  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content: `Hi! I'm APXMIND, your NEET study companion. Ask me anything about **${subject}**! I can explain concepts, solve problems, and help you prepare for NEET. 🎯`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef(Date.now());

  // Track subject studied for badge
  useEffect(() => {
    if (subject) recordSubjectStudied(subject);
  }, [subject, recordSubjectStudied]);

  // Track study time
  useEffect(() => {
    startTimeRef.current = Date.now();
    return () => {
      const minutes = Math.round((Date.now() - startTimeRef.current) / 60000);
      if (minutes >= 1) {
        recordStudySession(minutes);
      }
    };
  }, [recordStudySession]);

  useEffect(() => {
    const el = chatScrollRef.current;
    if (!el) return;
    const raf = requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
    return () => cancelAnimationFrame(raf);
  }, [messages, loading]);

  async function handleSend() {
    const q = input.trim();
    if (!q || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: q,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await processQuery(q, subject);
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: res.answer || 'Sorry, I could not process that question.',
        tier: res.metadata?.tier,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      addXP(10);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Oops! Something went wrong. Please make sure the APXMIND backend is running.',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const subjectLabels: Record<string, string> = {
    physics: 'Physics',
    chemistry: 'Chemistry',
    biology: 'Biology',
  };

  return (
    <div className="max-w-3xl mx-auto flex flex-col h-full min-h-0">
      {/* Breadcrumbs + header */}
      <div className="shrink-0 mb-3 space-y-2">
        <Breadcrumbs aria-label="Learn page breadcrumbs">
          <BreadcrumbItem onPress={() => navigate('/dashboard')}>Dashboard</BreadcrumbItem>
          <BreadcrumbItem onPress={() => navigate(`/subject/${subject}`)}>
            {subjectLabels[subject || ''] || subject}
          </BreadcrumbItem>
          <BreadcrumbItem>Learn</BreadcrumbItem>
        </Breadcrumbs>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button
              isIconOnly
              aria-label="Back to subject"
              variant="light"
              size="sm"
              onPress={() => navigate(`/subject/${subject}`)}
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5" style={{ color: 'var(--accent)' }} />
              <h1 className="ui-section-title">APXMIND AI Tutor</h1>
            </div>
          </div>
          <Button
            size="sm"
            color="secondary"
            variant="flat"
            startContent={<BrainCircuit className="w-3 h-3" />}
            onPress={() => navigate(`/subject/${subject}/lesson/${lessonId}/quiz`)}
          >
            Take Quiz
          </Button>
        </div>
      </div>

      {/* Chat area */}
      <Card className="flex-1 glass flex flex-col min-h-0">
        <div ref={chatScrollRef} className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="shrink-0 w-8 h-8 rounded-full bg-linear-to-br from-emerald-500 to-purple-500 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-linear-to-r from-purple-600 to-purple-500 text-white rounded-br-md shadow-lg shadow-purple-500/15'
                      : 'bg-bg-2 text-text-primary rounded-bl-md border border-border-default'
                  }`}
                >
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  ) : (
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  )}
                </div>
                  {msg.tier && (
                    <Chip size="sm" variant="flat" className="mt-1.5 text-[10px]">
                      {msg.tier}
                    </Chip>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="shrink-0 w-8 h-8 rounded-full bg-secondary/20 flex items-center justify-center">
                    <User className="w-4 h-4 text-secondary" />
                  </div>
                )}
              </motion.div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="shrink-0 w-8 h-8 rounded-full bg-linear-to-br from-emerald-500 to-purple-500 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="bg-bg-3 border border-border-default rounded-2xl rounded-bl-md px-4 py-3">
                  <Spinner size="sm" color="secondary" />
                </div>
              </div>
            )}
          </div>
        </div>

        <Divider />

        {/* Input */}
        <div className="p-3 flex gap-2">
          <Input
            aria-label="Message input"
            placeholder={`Ask about ${subjectLabels[subject || ''] || 'any subject'}...`}
            value={input}
            onValueChange={setInput}
            onKeyDown={handleKeyDown}
            variant="bordered"
            size="md"
            className="flex-1"
            isDisabled={loading}
            classNames={{
              inputWrapper: 'border-border-default hover:border-accent/50 focus-within:!border-accent bg-bg-2',
              input: 'text-text-primary placeholder:text-text-faint',
            }}
          />
          <Button
            isIconOnly
            aria-label="Send message"
            color="secondary"
            onPress={handleSend}
            isDisabled={!input.trim() || loading}
            isLoading={loading}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </Card>
    </div>
  );
}
