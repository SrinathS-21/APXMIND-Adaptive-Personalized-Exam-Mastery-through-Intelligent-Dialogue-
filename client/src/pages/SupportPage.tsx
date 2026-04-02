import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Input,
  Textarea,
  Chip,
  Select,
  SelectItem,
  Spinner,
} from '@heroui/react';
import { LifeBuoy, MessageCircle, Send } from 'lucide-react';
import { getApiErrorMessage } from '../lib/api';
import {
  SupportTicketDetail,
  SupportTicketItem,
  createSupportTicket,
  getSupportTicket,
  listSupportTickets,
  replySupportTicket,
  reportContent,
} from '../lib/supportService';

const categories = ['other', 'technical', 'billing', 'content', 'account'];
const priorities = ['low', 'normal', 'high'];

export function SupportPage() {
  const [tickets, setTickets] = useState<SupportTicketItem[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(null);
  const [selectedTicket, setSelectedTicket] = useState<SupportTicketDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmittingTicket, setIsSubmittingTicket] = useState(false);
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);
  const [isSubmittingReport, setIsSubmittingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('other');
  const [priority, setPriority] = useState('normal');

  const [replyMessage, setReplyMessage] = useState('');

  const [reportType, setReportType] = useState('chat_message');
  const [reportContentId, setReportContentId] = useState('');
  const [reportReason, setReportReason] = useState('');
  const [reportDescription, setReportDescription] = useState('');

  const selectedTicketSummary = useMemo(
    () => tickets.find((item) => item.id === selectedTicketId) ?? null,
    [tickets, selectedTicketId]
  );

  const loadTickets = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await listSupportTickets(undefined, 30);
      setTickets(list);
      setSelectedTicketId((prev) => prev ?? (list.length > 0 ? list[0].id : null));
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to load support tickets.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTickets();
  }, [loadTickets]);

  useEffect(() => {
    if (!selectedTicketId) {
      setSelectedTicket(null);
      return;
    }

    const ticketId = selectedTicketId;

    let active = true;
    async function loadTicketDetail() {
      try {
        const detail = await getSupportTicket(ticketId);
        if (active) {
          setSelectedTicket(detail);
        }
      } catch (err) {
        if (active) {
          setError(getApiErrorMessage(err, 'Unable to load ticket details.'));
        }
      }
    }

    void loadTicketDetail();
    return () => {
      active = false;
    };
  }, [selectedTicketId]);

  async function handleCreateTicket() {
    if (!subject.trim() || !description.trim()) {
      setError('Subject and description are required to create a ticket.');
      return;
    }

    setIsSubmittingTicket(true);
    setError(null);
    try {
      await createSupportTicket({
        subject: subject.trim(),
        description: description.trim(),
        category,
        priority,
      });
      setSubject('');
      setDescription('');
      await loadTickets();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to create support ticket.'));
    } finally {
      setIsSubmittingTicket(false);
    }
  }

  async function handleReply() {
    if (!selectedTicketId || !replyMessage.trim()) {
      return;
    }

    setIsSubmittingReply(true);
    setError(null);
    try {
      await replySupportTicket(selectedTicketId, replyMessage.trim());
      setReplyMessage('');
      const detail = await getSupportTicket(selectedTicketId);
      setSelectedTicket(detail);
      const list = await listSupportTickets(undefined, 30);
      setTickets(list);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to send ticket reply.'));
    } finally {
      setIsSubmittingReply(false);
    }
  }

  async function handleSubmitReport() {
    if (!reportType.trim() || !reportContentId.trim() || !reportReason.trim()) {
      setError('Content report requires type, content id, and reason.');
      return;
    }

    setIsSubmittingReport(true);
    setError(null);
    try {
      await reportContent({
        content_type: reportType.trim(),
        content_id: reportContentId.trim(),
        reason: reportReason.trim(),
        description: reportDescription.trim() || undefined,
      });
      setReportType('chat_message');
      setReportContentId('');
      setReportReason('');
      setReportDescription('');
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to submit content report.'));
    } finally {
      setIsSubmittingReport(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <h1 className="flex items-center gap-2" style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
        <LifeBuoy className="w-6 h-6 text-primary" />
        Support
      </h1>

      {error ? (
        <Card className="glass">
          <CardBody>
            <p style={{ fontSize: 12, color: 'var(--red)' }}>{error}</p>
          </CardBody>
        </Card>
      ) : null}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card className="glass xl:col-span-1">
          <CardHeader className="pb-2">
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
              Create Ticket
            </h2>
          </CardHeader>
          <CardBody className="space-y-2">
            <Input label="Subject" value={subject} onValueChange={setSubject} variant="bordered" />
            <Textarea
              label="Description"
              value={description}
              onValueChange={setDescription}
              minRows={4}
              variant="bordered"
            />
            <div className="grid grid-cols-2 gap-2">
              <Select
                label="Category"
                selectedKeys={new Set([category])}
                onSelectionChange={(keys) => setCategory(String(Array.from(keys)[0] || 'other'))}
                variant="bordered"
              >
                {categories.map((value) => (
                  <SelectItem key={value}>{value}</SelectItem>
                ))}
              </Select>
              <Select
                label="Priority"
                selectedKeys={new Set([priority])}
                onSelectionChange={(keys) => setPriority(String(Array.from(keys)[0] || 'normal'))}
                variant="bordered"
              >
                {priorities.map((value) => (
                  <SelectItem key={value}>{value}</SelectItem>
                ))}
              </Select>
            </div>
            <Button color="secondary" isLoading={isSubmittingTicket} onPress={() => void handleCreateTicket()}>
              Submit Ticket
            </Button>
          </CardBody>
        </Card>

        <Card className="glass xl:col-span-2">
          <CardHeader className="pb-2 flex items-center justify-between">
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
              My Tickets
            </h2>
            <Button size="sm" variant="flat" onPress={() => void loadTickets()}>
              Refresh
            </Button>
          </CardHeader>
          <CardBody className="space-y-3">
            {isLoading ? (
              <div className="py-8 flex justify-center">
                <Spinner label="Loading tickets" />
              </div>
            ) : tickets.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No tickets yet. Create one to start support chat.</p>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <div className="space-y-2 max-h-90 overflow-auto pr-1">
                  {tickets.map((ticket) => (
                    <button
                      key={ticket.id}
                      type="button"
                      onClick={() => setSelectedTicketId(ticket.id)}
                      className="w-full text-left rounded-lg p-2"
                      style={{
                        border: '1px solid var(--border-subtle)',
                        background: selectedTicketId === ticket.id ? 'var(--accent-glow)' : 'var(--bg-2)',
                      }}
                    >
                      <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
                        {ticket.subject}
                      </p>
                      <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{ticket.ticket_number}</p>
                      <div className="flex items-center gap-1.5 mt-1.5">
                        <Chip size="sm" variant="flat">{ticket.status}</Chip>
                        <Chip size="sm" variant="flat" color="secondary">{ticket.priority}</Chip>
                      </div>
                    </button>
                  ))}
                </div>

                <div className="rounded-lg p-3" style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-2)' }}>
                  {selectedTicketSummary ? (
                    <>
                      <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                        {selectedTicketSummary.subject}
                      </p>
                      <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {selectedTicketSummary.ticket_number}
                      </p>
                      <div className="space-y-2 mt-2 max-h-50 overflow-auto pr-1">
                        {(selectedTicket?.responses ?? []).map((response) => (
                          <div
                            key={response.id}
                            className="rounded-md p-2"
                            style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-3)' }}
                          >
                            <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>
                              {response.responder_name || 'Support'}
                            </p>
                            <p style={{ fontSize: 12, color: 'var(--text-primary)' }}>{response.message}</p>
                            <p style={{ fontSize: 10, color: 'var(--text-faint)' }}>
                              {response.created_at ? new Date(response.created_at).toLocaleString() : 'Unknown time'}
                            </p>
                          </div>
                        ))}
                      </div>
                      <div className="mt-2 space-y-2">
                        <Textarea
                          label="Reply"
                          value={replyMessage}
                          onValueChange={setReplyMessage}
                          minRows={2}
                          variant="bordered"
                        />
                        <Button
                          size="sm"
                          color="secondary"
                          startContent={<MessageCircle className="w-3 h-3" />}
                          isLoading={isSubmittingReply}
                          onPress={() => void handleReply()}
                        >
                          Send Reply
                        </Button>
                      </div>
                    </>
                  ) : (
                    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Select a ticket to view details.</p>
                  )}
                </div>
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      <Card className="glass">
        <CardHeader className="pb-2">
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
            Report Content
          </h2>
        </CardHeader>
        <CardBody className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <Input label="Content Type" value={reportType} onValueChange={setReportType} variant="bordered" />
          <Input label="Content ID" value={reportContentId} onValueChange={setReportContentId} variant="bordered" />
          <Input label="Reason" value={reportReason} onValueChange={setReportReason} variant="bordered" />
          <Input
            label="Description (optional)"
            value={reportDescription}
            onValueChange={setReportDescription}
            variant="bordered"
          />
          <div className="md:col-span-2">
            <Button
              color="secondary"
              startContent={<Send className="w-4 h-4" />}
              isLoading={isSubmittingReport}
              onPress={() => void handleSubmitReport()}
            >
              Submit Report
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
