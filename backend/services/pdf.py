import io
import re
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text content from raw PDF bytes."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            extracted_text.append(text)
    return "\n".join(extracted_text)

def build_pdf_from_text(cv_text: str, output_path: str):
    """Generate a clean, 1-page professional PDF file from CV text content."""
    doc = SimpleDocTemplate(
        output_path,
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
            clean_text = stripped[2:].strip()
            story.append(Paragraph(clean_text, title_style))
            is_first_line = False
        elif stripped.startswith("## ") or stripped.startswith("### "):
            clean_text = re.sub(r'^#+\s*', '', stripped)
            story.append(Paragraph(clean_text, heading_style))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            clean_text = "&bull; " + stripped[2:].strip()
            story.append(Paragraph(clean_text, bullet_style))
        elif is_first_line and len(stripped) < 60 and not stripped.endswith('.'):
            story.append(Paragraph(stripped, title_style))
            is_first_line = False
        elif stripped.isupper() and len(stripped) < 50:
            story.append(Paragraph(stripped, heading_style))
        else:
            safe_text = stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe_text, body_style))
            is_first_line = False

    doc.build(story)
