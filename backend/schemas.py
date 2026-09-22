from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    message: str = "Authenticated successfully"

class AuthStatusResponse(BaseModel):
    authenticated: bool
    email: Optional[str] = None

class TokenData(BaseModel):
    email: Optional[str] = None
    token_type: Optional[str] = None

class FileMetadataResponse(BaseModel):
    id: int
    file_name: str
    file_size: int
    file_type: str
    uploaded_at: datetime
    class Config:
        from_attributes = True

class AnalyzeRequest(BaseModel):
    job_description: str

class AnalysisResponse(BaseModel):
    score: int
    improvements: str

class CoverLetterRequest(BaseModel):
    job_description: str

class CoverLetterResponse(BaseModel):
    cover_letter: str

class ApplyChangesRequest(BaseModel):
    job_description: str
    improvements: Optional[str] = None

class GenerateImprovedResponse(BaseModel):
    improved_text: str

class CVContentResponse(BaseModel):
    content: str
    file_name: str
    file_type: str
    is_pdf: bool
