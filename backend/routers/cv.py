from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import os
import io
import uuid
import redis
import models
import schemas
import auth
from database import get_db
from services.ai import analyze_cv, generate_cover_letter, apply_cv_improvements
from services.pdf import extract_text_from_pdf_bytes, generate_pdf_bytes
from services.storage import storage_service
from services.limiter import rate_limit
import re

router = APIRouter(
    prefix="/api/cv",
    tags=["cv"]
)

def sanitize_filename_header(filename: str) -> str:
    """Sanitize filename to prevent HTTP Header Injection / Response Splitting in Content-Disposition."""
    if not filename:
        return "document.pdf"
    clean = re.sub(r'[\r\n"\\;]', '', filename).strip()
    return clean or "document.pdf"

# Connect to Redis
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(redis_url, decode_responses=True)

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
}

@router.post(
    "/upload",
    response_model=schemas.FileMetadataResponse,
    dependencies=[Depends(rate_limit("upload", limit=10, period=60))]
)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    filename_lower = file.filename.lower()
    if not filename_lower.endswith((".txt", ".md", ".pdf")):
        raise HTTPException(status_code=400, detail="Only .txt, .md, and .pdf files are allowed")

    # Read uploaded bytes with size validation
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE // (1024 * 1024)}MB."
        )

    # Validate content and extract text based on file type
    if filename_lower.endswith(".pdf"):
        # Validate PDF magic header
        if not contents.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Invalid PDF file: Missing standard PDF header")
        try:
            decoded_contents = extract_text_from_pdf_bytes(contents)
            if not decoded_contents.strip():
                raise ValueError("No readable text found in PDF")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not parse PDF file: {str(e)}")
        content_type = "application/pdf"
    else:
        try:
            decoded_contents = contents.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")
        content_type = "text/markdown" if filename_lower.endswith(".md") else "text/plain"

    # Sanitize user email for S3 key structure
    sanitized_email = current_user.email.replace("@", "_at_").replace(".", "_dot_")
    file_ext = os.path.splitext(file.filename)[1].lower()
    s3_key = f"user-files/{sanitized_email}/{uuid.uuid4()}{file_ext}"

    # Invalidate Redis cache for this user
    try:
        redis_client.delete(f"cv:{current_user.email}")
    except Exception as e:
        print(f"Redis cache invalidate warning: {e}")

    # Remove previous files from S3 and database
    existing_files = db.query(models.UserFile).filter(models.UserFile.user_email == current_user.email).all()
    for existing_file in existing_files:
        try:
            storage_service.delete_file(existing_file.object_key)
        except Exception as e:
            print(f"Warning deleting old S3 object ({existing_file.object_key}): {e}")
        db.delete(existing_file)
    db.commit()

    # Upload to AWS S3
    try:
        storage_service.upload_file(contents, s3_key, content_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store file in object storage: {str(e)}")

    # Store file metadata in database
    db_file = models.UserFile(
        user_email=current_user.email,
        object_key=s3_key,
        file_name=file.filename,
        file_size=len(contents),
        file_type=content_type,
        uploaded_at=func.now()
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    # Cache extracted text in Redis for 1 hour
    try:
        redis_client.set(f"cv:{current_user.email}", decoded_contents, ex=3600)
    except Exception as e:
        print(f"Redis cache set warning: {e}")

    return db_file


def get_user_cv(user_email: str, db: Session) -> str:
    """Retrieve CV text from Redis or fetch from S3 and extract text."""
    # 1. Check Redis cache
    try:
        cached_cv = redis_client.get(f"cv:{user_email}")
        if cached_cv:
            return cached_cv
    except Exception as e:
        print(f"Redis cache get warning: {e}")

    # 2. Fetch from DB
    db_file = db.query(models.UserFile).filter(
        models.UserFile.user_email == user_email
    ).order_by(models.UserFile.uploaded_at.desc(), models.UserFile.id.desc()).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="No CV found for user")

    # 3. Download from S3
    try:
        file_bytes = storage_service.get_file_bytes(db_file.object_key)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"CV object not found in storage: {str(e)}")

    if db_file.file_name.lower().endswith(".pdf"):
        content = extract_text_from_pdf_bytes(file_bytes)
    else:
        content = file_bytes.decode("utf-8", errors="replace")

    # 4. Refresh Redis cache
    try:
        redis_client.set(f"cv:{user_email}", content, ex=3600)
    except Exception as e:
        print(f"Redis cache update warning: {e}")

    return content


@router.get("/content", response_model=schemas.CVContentResponse)
def get_cv_content(
    response: Response,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    for key, value in NO_CACHE_HEADERS.items():
        response.headers[key] = value

    db_file = db.query(models.UserFile).filter(
        models.UserFile.user_email == current_user.email
    ).order_by(models.UserFile.uploaded_at.desc(), models.UserFile.id.desc()).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="No CV found for user")

    cv_content = get_user_cv(current_user.email, db)
    is_pdf = db_file.file_name.lower().endswith(".pdf")
    return {
        "content": cv_content,
        "file_name": db_file.file_name,
        "file_type": db_file.file_type or ("application/pdf" if is_pdf else "text/plain"),
        "is_pdf": is_pdf
    }


@router.get("/pdf")
def get_cv_pdf(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    db_file = db.query(models.UserFile).filter(
        models.UserFile.user_email == current_user.email
    ).order_by(models.UserFile.uploaded_at.desc(), models.UserFile.id.desc()).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="No CV found for user")

    clean_filename = sanitize_filename_header(db_file.file_name)
    headers = {
        **NO_CACHE_HEADERS,
        "Content-Disposition": f'inline; filename="{clean_filename}"'
    }

    if db_file.file_name.lower().endswith(".pdf"):
        # Retrieve PDF bytes from S3 and stream directly
        try:
            pdf_bytes = storage_service.get_file_bytes(db_file.object_key)
            return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"File could not be retrieved from storage: {str(e)}")
    else:
        # Build PDF dynamically from markdown / text content in memory
        cv_content = get_user_cv(current_user.email, db)
        pdf_bytes = generate_pdf_bytes(cv_content)
        clean_base = sanitize_filename_header(os.path.splitext(db_file.file_name)[0])
        pdf_filename = f"{clean_base}.pdf"
        headers["Content-Disposition"] = f'inline; filename="{pdf_filename}"'
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@router.get("/file")
def get_cv_file(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    db_file = db.query(models.UserFile).filter(
        models.UserFile.user_email == current_user.email
    ).order_by(models.UserFile.uploaded_at.desc(), models.UserFile.id.desc()).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="CV file not found")

    try:
        file_bytes = storage_service.get_file_bytes(db_file.object_key)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Object not found in storage: {str(e)}")

    clean_filename = sanitize_filename_header(db_file.file_name)
    media_type = "application/pdf" if db_file.file_name.lower().endswith(".pdf") else "text/plain"
    headers = {
        **NO_CACHE_HEADERS,
        "Content-Disposition": f'attachment; filename="{clean_filename}"'
    }
    return StreamingResponse(io.BytesIO(file_bytes), media_type=media_type, headers=headers)


@router.post(
    "/analyze",
    response_model=schemas.AnalysisResponse,
    dependencies=[Depends(rate_limit("ai", limit=10, period=60))]
)
def analyze(
    request: schemas.AnalyzeRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cv_content = get_user_cv(current_user.email, db)
    result = analyze_cv(cv_content, request.job_description)
    return result


@router.post(
    "/cover-letter",
    response_model=schemas.CoverLetterResponse,
    dependencies=[Depends(rate_limit("ai", limit=10, period=60))]
)
def generate_cl(
    request: schemas.CoverLetterRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cv_content = get_user_cv(current_user.email, db)
    cl = generate_cover_letter(cv_content, request.job_description)
    return {"cover_letter": cl}


@router.post(
    "/download-cover-letter",
    dependencies=[Depends(rate_limit("ai", limit=10, period=60))]
)
def download_cover_letter(
    request: schemas.CoverLetterRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cv_content = get_user_cv(current_user.email, db)
    cl_text = generate_cover_letter(cv_content, request.job_description)

    # Generate PDF directly in memory
    try:
        pdf_bytes = generate_pdf_bytes(cl_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate cover letter PDF: {str(e)}")

    headers = {
        **NO_CACHE_HEADERS,
        "Content-Disposition": 'attachment; filename="Cover_Letter.pdf"'
    }
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@router.post(
    "/generate-improved",
    response_model=schemas.GenerateImprovedResponse,
    dependencies=[Depends(rate_limit("ai", limit=10, period=60))]
)
def generate_improved(
    request: schemas.ApplyChangesRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cv_content = get_user_cv(current_user.email, db)
    improvements = request.improvements or ""
    updated_cv_text = apply_cv_improvements(cv_content, improvements, request.job_description)
    return {"improved_text": updated_cv_text}


@router.post(
    "/download-improved",
    dependencies=[Depends(rate_limit("ai", limit=10, period=60))]
)
def download_improved(
    request: schemas.ApplyChangesRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cv_content = get_user_cv(current_user.email, db)
    improvements = request.improvements or ""
    updated_cv_text = apply_cv_improvements(cv_content, improvements, request.job_description)

    # Generate PDF directly in memory
    try:
        pdf_bytes = generate_pdf_bytes(updated_cv_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

    headers = {
        **NO_CACHE_HEADERS,
        "Content-Disposition": 'attachment; filename="Improved_CV.pdf"'
    }
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@router.post(
    "/apply-changes",
    response_model=schemas.GenerateImprovedResponse,
    dependencies=[Depends(rate_limit("ai", limit=10, period=60))]
)
def apply_changes(
    request: schemas.ApplyChangesRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cv_content = get_user_cv(current_user.email, db)
    improvements = request.improvements or ""
    updated_cv_text = apply_cv_improvements(cv_content, improvements, request.job_description)
    return {"improved_text": updated_cv_text}
