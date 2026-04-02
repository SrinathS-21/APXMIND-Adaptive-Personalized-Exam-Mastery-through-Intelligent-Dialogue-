import { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Button,
  Breadcrumbs,
  BreadcrumbItem,
  Chip,
} from '@heroui/react';
import { ArrowLeft, Maximize2, Minimize2 } from 'lucide-react';

export function BookReaderPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const file = params.get('file') || '';
  // #toolbar=1&navpanes=1 hints Chrome/Edge built-in PDF viewer to show controls
  const pdfUrl = `/api/books/${file}#toolbar=1&navpanes=1`;
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Extract a readable chapter name from the path
  const parts = file.split('/');
  const folder = parts.length > 1 ? parts[parts.length - 2] : '';
  const fileName = parts[parts.length - 1]?.replace('.pdf', '') || 'Book';
  const displayName = folder ? `${folder} / ${fileName}` : fileName;

  function toggleFullscreen() {
    const el = document.getElementById('pdf-container');
    if (!el) return;
    if (!document.fullscreenElement) {
      el.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => { });
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => { });
    }
  }

  return (
    <div className="ui-page-shell space-y-3">
      {/* Breadcrumbs */}
      <Breadcrumbs aria-label="Book reader breadcrumbs">
        <BreadcrumbItem onPress={() => navigate('/home')}>Home</BreadcrumbItem>
        <BreadcrumbItem onPress={() => navigate('/books')}>Books</BreadcrumbItem>
        <BreadcrumbItem>{displayName}</BreadcrumbItem>
      </Breadcrumbs>

      <div>
        <h1 className="ui-page-title">Book Reader</h1>
        <p className="ui-page-subtitle">{displayName}</p>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <Button
          variant="light"
          size="sm"
          startContent={<ArrowLeft className="w-4 h-4" />}
          onPress={() => navigate('/books')}
        >
          Back to Books
        </Button>

        <div className="flex items-center gap-2">
          <Chip size="sm" variant="flat" className="ui-pill ui-chip-neutral">
            PDF Viewer
          </Chip>
          <Button
            variant="flat"
            size="sm"
            isIconOnly
            aria-label="Toggle fullscreen"
            onPress={toggleFullscreen}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* PDF viewer — uses browser's native PDF renderer */}
      <div
        id="pdf-container"
        className="glass ui-card-md overflow-hidden"
        style={{ height: 'calc(100dvh - 10rem)' }}
      >
        <embed
          src={pdfUrl}
          type="application/pdf"
          className="w-full h-full"
          style={{ minHeight: '100%' }}
        />
      </div>

      {/* Fallback for browsers without inline PDF support */}
      <noscript>
        <p className="text-center text-default-500">
          Your browser does not support inline PDF viewing.{' '}
          <a href={`/api/books/${file}`} className="text-primary underline">
            Click here to open the PDF
          </a>
        </p>
      </noscript>
    </div>
  );
}
