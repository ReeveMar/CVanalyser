import React from 'react';
import '../cv.css';

function parseInlineFormatting(text) {
  // Simple helper to process **bold** text
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index} className="cv-bold">{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function CVViewer({ content }) {
  if (!content) {
    return (
      <div className="cv-paper-container">
        <div className="cv-paper" style={{ textAlign: 'center', color: '#667069' }}>
          No CV content available.
        </div>
      </div>
    );
  }

  const lines = content.strip ? content.strip().split('\n') : content.split('\n');
  const elements = [];
  let currentList = [];
  let isFirstLine = true;

  const flushList = (keyPrefix) => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`${keyPrefix}-list`} className="cv-bullet-list">
          {currentList.map((item, idx) => (
            <li key={idx} className="cv-bullet-item">{parseInlineFormatting(item)}</li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  lines.forEach((rawLine, index) => {
    const line = rawLine.trim();

    if (!line) {
      flushList(index);
      return;
    }

    // Bullet point
    if (line.startswith?.('- ') || line.startswith?.('* ') || line.startsWith('- ') || line.startsWith('* ')) {
      const bulletText = line.substring(2).trim();
      currentList.push(bulletText);
      return;
    }

    // If we reach a non-bullet line, flush any active list first
    flushList(index);

    // H1 (Main Title / Candidate Name)
    if (line.startsWith('# ')) {
      const titleText = line.substring(2).trim();
      elements.push(
        <h1 key={index} className="cv-header-title">
          {titleText}
        </h1>
      );
      isFirstLine = false;
      return;
    }

    // H2 / H3 (Section Heading)
    if (line.startsWith('## ') || line.startsWith('### ')) {
      const headingText = line.replace(/^#+\s*/, '').trim();
      elements.push(
        <h2 key={index} className="cv-section-heading">
          {headingText}
        </h2>
      );
      return;
    }

    // First short line (Fallback Candidate Name if no # tag)
    if (isFirstLine && line.length < 60 && !line.endsWith('.')) {
      elements.push(
        <h1 key={index} className="cv-header-title">
          {line}
        </h1>
      );
      isFirstLine = false;
      return;
    }

    // ALL CAPS subheading or short title
    if (line === line.toUpperCase() && line.length < 50 && /[A-Z]/.test(line)) {
      elements.push(
        <h2 key={index} className="cv-section-heading">
          {line}
        </h2>
      );
      return;
    }

    // Subheading or Body Text
    if (line.includes('|') || line.toLowerCase().includes('email') || line.toLowerCase().includes('phone') || line.toLowerCase().includes('linkedin')) {
      elements.push(
        <div key={index} className="cv-contact-info">
          {parseInlineFormatting(line)}
        </div>
      );
    } else {
      elements.push(
        <p key={index} className="cv-body-text">
          {parseInlineFormatting(line)}
        </p>
      );
    }

    isFirstLine = false;
  });

  flushList('end');

  return (
    <div className="cv-paper-container">
      <div className="cv-paper">
        {elements}
      </div>
    </div>
  );
}

export default CVViewer;
