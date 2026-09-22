from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from datetime import timedelta
from jose import JWTError, jwt
import models
import schemas
import auth
from database import get_db
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(
    prefix="/api/users",
    tags=["users"]
)

@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=schemas.Token)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.email})
    refresh_token = auth.create_refresh_token(data={"sub": user.email})
    
    # Set HTTP-Only cookies
    auth.set_auth_cookies(response, access_token, refresh_token)
    return {"message": "Authenticated successfully"}

@router.post("/refresh", response_model=schemas.Token)
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    refresh_token_cookie = request.cookies.get("refresh_token")
    if not refresh_token_cookie:
        raise credentials_exception

    try:
        payload = jwt.decode(refresh_token_cookie, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
            
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise credentials_exception

    new_access_token = auth.create_access_token(data={"sub": user.email})
    new_refresh_token = auth.create_refresh_token(data={"sub": user.email})
    
    auth.set_auth_cookies(response, new_access_token, new_refresh_token)
    return {"message": "Token refreshed successfully"}

@router.post("/logout")
def logout(response: Response):
    auth.clear_auth_cookies(response)
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=schemas.AuthStatusResponse)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return {"authenticated": True, "email": current_user.email}
