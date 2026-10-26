import React from 'react';
import '../cv.css';

function PDFViewer({ pdfUrl, title = 'PDF Viewer', fileName = 'document.pdf', loading = false, error = null }) {
  if (loading) {
    return (
      <div className="pdf-container">
        <div className="pdf-placeholder">
          <div className="pdf-spinner"></div>
          <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>Generating and rendering PDF viewer...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pdf-container">
        <div className="pdf-placeholder error">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!pdfUrl) {
    return (
      <div className="pdf-container">
        <div className="pdf-placeholder">
          <p>No PDF document available to display.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pdf-viewer-wrapper">
      <div className="pdf-toolbar">
        <div className="pdf-toolbar-info">
          <svg className="pdf-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
          <span className="pdf-title">{title}</span>
          {fileName && <span className="pdf-badge">{fileName}</span>}
        </div>
        <div className="pdf-toolbar-actions">
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="pdf-btn pdf-btn-secondary"
            title="Open in new tab"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
              <polyline points="15 3 21 3 21 9"></polyline>
              <line x1="10" y1="14" x2="21" y2="3"></line>
            </svg>
            <span>Open New Tab</span>
          </a>
          <a
            href={pdfUrl}
            download={fileName}
            className="pdf-btn pdf-btn-primary"
            title="Download PDF"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <span>Download PDF</span>
          </a>
        </div>
      </div>
      <div className="pdf-embed-container">
        <object
          key={pdfUrl}
          data={`${pdfUrl}#toolbar=1`}
          type="application/pdf"
          className="pdf-embed-frame"
          aria-label={title}
        >
          <iframe
            key={pdfUrl}
            src={`${pdfUrl}#toolbar=1`}
            title={title}
            className="pdf-embed-frame"
          >
            <p style={{ padding: '2rem', textAlign: 'center' }}>
              Your browser does not support inline PDF viewing. <a href={pdfUrl} download={fileName}>Download the PDF</a> to view it.
            </p>
          </iframe>
        </object>
      </div>
    </div>
  );
}

export default PDFViewer;
