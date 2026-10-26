import io
import re
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors

def fix_spaced_name(text: str) -> str:
    """
    Detects and fixes names or headers where letters are separated by single spaces,
    e.g., 'R E E V E   M A R' -> 'REEVE MAR' or 'J o h n   D o e' -> 'John Doe'.
    """
    if not text:
        return text

    # Handle multi-space separated words with single-letter spacing (e.g., "R E E V E   M A R")
    if "  " in text:
        parts = [p.strip() for p in text.split("  ") if p.strip()]
        new_words = []
        is_spaced_header = False
        for p in parts:
            tokens = p.split()
            if len(tokens) > 1 and all(len(t) == 1 and t.isalpha() for t in tokens):
                new_words.append("".join(tokens))
                is_spaced_header = True
            else:
                new_words.append(p)
        if is_spaced_header:
            return " ".join(new_words)

    # Handle single string of single-letter tokens (e.g., "R E E V E")
    tokens = text.split()
    if len(tokens) >= 3 and all(len(t) == 1 and t.isalpha() for t in tokens):
        return "".join(tokens)

    return text

MAX_PDF_PAGES = 15

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text content from raw PDF bytes with safety limits against page bomb DoS."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if len(reader.pages) > MAX_PDF_PAGES:
        raise ValueError(f"PDF exceeds the maximum allowed page count ({MAX_PDF_PAGES} pages). Please upload a standard 1-3 page CV.")
    extracted_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text = text.replace('\u00ad', '').replace('\u200b', '').replace('\ufeff', '').replace('\u2060', '')
            lines = [fix_spaced_name(line) for line in text.split('\n')]
            extracted_text.append("\n".join(lines))
    return "\n".join(extracted_text)

def sanitize_and_format_text(text: str) -> str:
    """
    Sanitizes Unicode characters unsupported by ReportLab's standard Helvetica font,
    normalizes whitespace and spaced-out names, and converts Markdown bold/italic syntax.
    """
    if not text:
        return ""

    # Fix spaced-out letters in names or titles
    text = fix_spaced_name(text)

    # Remove zero-width spaces / soft hyphens
    text = text.replace('\u00ad', '').replace('\u200b', '').replace('\ufeff', '').replace('\u2060', '')

    # Replace unsupported unicode hyphens, dashes, quotes, non-breaking spaces with standard ASCII
    replacements = {
        '\u2010': '-',  # hyphen
        '\u2011': '-',  # non-breaking hyphen
        '\u2012': '-',  # figure dash
        '\u2013': '-',  # en dash
        '\u2014': '-',  # em dash
        '\u2015': '-',  # horizontal bar
        '\u2018': "'",  # left single quote
        '\u2019': "'",  # right single quote
        '\u201a': "'",  # single low-9 quote
        '\u201b': "'",  # single high-reversed-9 quote
        '\u201c': '"',  # left double quote
        '\u201d': '"',  # right double quote
        '\u201e': '"',  # double low-9 quote
        '\u2026': '...',# ellipsis
        '\u00a0': ' ',  # non-breaking space
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)

    # Ensure literal em-dashes and en-dashes are converted to standard hyphens
    text = text.replace('—', '-').replace('–', '-')

    # Normalize multiple spaces down to a single space
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # HTML escape special chars first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Convert **bold** and *italic* markdown syntax to ReportLab HTML tags
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)

    return text.strip()

def build_pdf_from_text(cv_text: str, output_target):
    """Generate a clean, 1-page professional PDF file or buffer from CV text content."""
    doc = SimpleDocTemplate(
        output_target,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=28,
        bottomMargin=28
    )

    styles = getSampleStyleSheet()
    
    # Custom 1-page optimized styles
    title_style = ParagraphStyle(
        'CVTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=19,
        textColor=colors.HexColor("#0D4733"),
        spaceAfter=6,
        fontName="Helvetica-Bold"
    )
    
    heading_style = ParagraphStyle(
        'CVHeading',
        parent=styles['Heading2'],
        fontSize=11.5,
        leading=14,
        textColor=colors.HexColor("#0D4733"),
        spaceBefore=6,
        spaceAfter=3,
        fontName="Helvetica-Bold"
    )
    
    body_style = ParagraphStyle(
        'CVBody',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor("#1A2B23"),
        spaceAfter=2,
        fontName="Helvetica"
    )

    bullet_style = ParagraphStyle(
        'CVBullet',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )

    story = []
    lines = cv_text.strip().split('\n')
    
    is_first_line = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 3))
            continue
        
        # Format headers vs body vs bullets
        if stripped.startswith("# "):
            clean_text = sanitize_and_format_text(stripped[2:].strip())
            story.append(Paragraph(clean_text, title_style))
            is_first_line = False
        elif stripped.startswith("## ") or stripped.startswith("### "):
            clean_text = sanitize_and_format_text(re.sub(r'^#+\s*', '', stripped))
            story.append(Paragraph(clean_text, heading_style))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            clean_text = "&bull; " + sanitize_and_format_text(stripped[2:].strip())
            story.append(Paragraph(clean_text, bullet_style))
        elif is_first_line and len(stripped) < 60 and not stripped.endswith('.'):
            clean_text = sanitize_and_format_text(stripped)
            story.append(Paragraph(clean_text, title_style))
            is_first_line = False
        elif stripped.isupper() and len(stripped) < 50 and any(c.isalpha() for c in stripped):
            clean_text = sanitize_and_format_text(stripped)
            story.append(Paragraph(clean_text, heading_style))
        else:
            clean_text = sanitize_and_format_text(stripped)
            story.append(Paragraph(clean_text, body_style))
            is_first_line = False

    doc.build(story)
    if hasattr(output_target, "flush"):
        output_target.flush()

def generate_pdf_bytes(cv_text: str) -> bytes:
    """Generate in-memory PDF bytes from CV text content with graceful fallback."""
    buf = io.BytesIO()
    try:
        build_pdf_from_text(cv_text, buf)
    except Exception as e:
        print(f"Warning: styled PDF build failed, falling back to safe plain rendering: {e}")
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        fallback_styles = getSampleStyleSheet()
        story = []
        for line in cv_text.strip().split("\n"):
            clean_l = sanitize_and_format_text(line)
            story.append(Paragraph(clean_l if clean_l else "&nbsp;", fallback_styles["Normal"]))
            story.append(Spacer(1, 3))
        doc.build(story)
    buf.seek(0)
    return buf.getvalue()

