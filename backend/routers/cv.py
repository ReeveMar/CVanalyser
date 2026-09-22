from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid
import redis
import models
import schemas
import auth
from database import get_db
from services.ai import analyze_cv, generate_cover_letter, apply_cv_improvements
from services.pdf import extract_text_from_pdf_bytes, build_pdf_from_text

router = APIRouter(
    prefix="/api/cv",
    tags=["cv"]
)

# Connect to Redis
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(redis_url, decode_responses=True)

UPLOAD_DIR = "bucket-name/user-files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=schemas.FileMetadataResponse)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    filename_lower = file.filename.lower()
    if not filename_lower.endswith((".txt", ".md", ".pdf")):
        raise HTTPException(status_code=400, detail="Only .txt, .md, and .pdf files are allowed")

    contents = await file.read()
    
    # Process text content based on file type
    if filename_lower.endswith(".pdf"):
        try:
            decoded_contents = extract_text_from_pdf_bytes(contents)
            if not decoded_contents.strip():
                raise ValueError("No text could be extracted from PDF")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read PDF file: {str(e)}")
    else:
        try:
            decoded_contents = contents.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")

    # Sanitize email for folder name
    sanitized_email = current_user.email.replace("@", "_at_").replace(".", "_dot_")
    user_dir = os.path.join(UPLOAD_DIR, sanitized_email)
    os.makedirs(user_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(user_dir, unique_filename)

    # Replace existing CV in DB and mock S3
    existing_files = db.query(models.UserFile).filter(models.UserFile.user_email == current_user.email).all()
    for existing_file in existing_files:
        if os.path.exists(existing_file.object_key):
            try:
                os.remove(existing_file.object_key)
            except OSError:
                pass
        db.delete(existing_file)
    db.commit()

    with open(file_path, "wb") as f:
        f.write(contents)

    # Store in DB
    db_file = models.UserFile(
        user_email=current_user.email,
        object_key=file_path,
        file_name=file.filename,
        file_size=len(contents),
        file_type=file.content_type or ("application/pdf" if filename_lower.endswith(".pdf") else "text/plain")
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    # Cache CV text in Redis
    redis_client.set(f"cv:{current_user.email}", decoded_contents, ex=3600) # Cache for 1 hour

    return db_file

def get_user_cv(user_email: str, db: Session) -> str:
    # Try Redis first
    cached_cv = redis_client.get(f"cv:{user_email}")
    if cached_cv:
        return cached_cv
    
    # Fallback to DB and File
    db_file = db.query(models.UserFile).filter(models.UserFile.user_email == user_email).order_by(models.UserFile.uploaded_at.desc()).first()
    if not db_file or not os.path.exists(db_file.object_key):
        raise HTTPException(status_code=404, detail="No CV found for user")
    
    if db_file.file_name.lower().endswith(".pdf"):
        with open(db_file.object_key, "rb") as f:
            pdf_bytes = f.read()
        content = extract_text_from_pdf_bytes(pdf_bytes)
    else:
        with open(db_file.object_key, "r", encoding="utf-8") as f:
            content = f.read()
    
    # Update cache
    redis_client.set(f"cv:{user_email}", content, ex=3600)
    return content

@router.get("/content", response_model=schemas.CVContentResponse)
def get_cv_content(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    db_file = db.query(models.UserFile).filter(models.UserFile.user_email == current_user.email).order_by(models.UserFile.uploaded_at.desc()).first()
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

@router.get("/file")
def get_cv_file(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    db_file = db.query(models.UserFile).filter(models.UserFile.user_email == current_user.email).order_by(models.UserFile.uploaded_at.desc()).first()
    if not db_file or not os.path.exists(db_file.object_key):
        raise HTTPException(status_code=404, detail="CV file not found")
    
    media_type = "application/pdf" if db_file.file_name.lower().endswith(".pdf") else "text/plain"
    return FileResponse(
        path=db_file.object_key,
        media_type=media_type,
        filename=db_file.file_name
    )

@router.post("/analyze", response_model=schemas.AnalysisResponse)
def analyze(
    request: schemas.AnalyzeRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cv_content = get_user_cv(current_user.email, db)
    result = analyze_cv(cv_content, request.job_description)
    return result

@router.post("/cover-letter", response_model=schemas.CoverLetterResponse)
def generate_cl(
    request: schemas.CoverLetterRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cv_content = get_user_cv(current_user.email, db)
    cl = generate_cover_letter(cv_content, request.job_description)
    return {"cover_letter": cl}

@router.post("/generate-improved", response_model=schemas.GenerateImprovedResponse)
def generate_improved(
    request: schemas.ApplyChangesRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cv_content = get_user_cv(current_user.email, db)
    improvements = request.improvements or ""
    updated_cv_text = apply_cv_improvements(cv_content, improvements, request.job_description)
    return {"improved_text": updated_cv_text}

@router.post("/download-improved")
def download_improved(
    request: schemas.ApplyChangesRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cv_content = get_user_cv(current_user.email, db)
    improvements = request.improvements or ""
    updated_cv_text = apply_cv_improvements(cv_content, improvements, request.job_description)
    
    sanitized_email = current_user.email.replace("@", "_at_").replace(".", "_dot_")
    user_dir = os.path.join(UPLOAD_DIR, sanitized_email, "generated")
    os.makedirs(user_dir, exist_ok=True)
    
    temp_pdf_path = os.path.join(user_dir, f"improved_cv_{uuid.uuid4()}.pdf")
    try:
        build_pdf_from_text(updated_cv_text, temp_pdf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

    return FileResponse(
        path=temp_pdf_path,
        media_type="application/pdf",
        filename="Improved_CV.pdf"
    )

@router.post("/apply-changes", response_model=schemas.GenerateImprovedResponse)
def apply_changes(
    request: schemas.ApplyChangesRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cv_content = get_user_cv(current_user.email, db)
    improvements = request.improvements or ""
    updated_cv_text = apply_cv_improvements(cv_content, improvements, request.job_description)
    return {"improved_text": updated_cv_text}
