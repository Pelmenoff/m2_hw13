from fastapi import FastAPI, HTTPException, Depends, status, Request, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
from datetime import datetime, timedelta
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from dotenv import load_dotenv
from .crud import (
    create_contact,
    get_contacts,
    get_contact_by_id,
    update_contact,
    delete_contact,
    search_contacts,
    upcoming_birthdays,
    get_user_by_email,
)
from .database import SessionLocal
from .models import (
    User,
    ContactCreate,
    ContactResponse,
    ContactListResponse,
    UserCreate,
)
from .security import verify_password, get_password_hash
import cloudinary
import os

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

limiter = Limiter(key_func=get_remote_address)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

origins = [ 
    "http://localhost:8000"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=os.getenv("MAIL_PORT"),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
)

cloudinary.config(
  cloud_name =os.getenv("CLOUD_NAME"),
  api_key =os.getenv("API_KEY"),
  api_secret =os.getenv("API_SECRET"),
)

def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    db_user = get_user_by_email(db, email)
    if db_user is None:
        raise credentials_exception
    return db_user



@app.post("/register/")
async def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
    )

    user.generate_verification_token()
    
    db.add(user)
    db.commit()
    db.refresh(user)

    if not user.verification_token:
        raise HTTPException(status_code=500, detail="Failed to generate verification token")
    
    message = MessageSchema(
        subject="Email Verification",
        recipients=[user.email],
        body=f"Your verification token is: {user.verification_token}",
        subtype="html"
    )
    
    fm = FastMail(conf)
    await fm.send_message(message)
    
    return {"msg": "User created. Please check your email to verify your account."}

@app.get("/verify/{token}")
async def verify(token: str, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.verification_token == token).first()
    
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid token")
    
    db_user.is_verified = True
    db_user.is_active = True
    db_user.verification_token = None
    
    db.commit()
    
    return {"msg": "Account verified successfully"}


@app.post("/contacts/", response_model=ContactResponse)
@limiter.limit("5/minute", key_func=lambda request: get_remote_address(request))
def create_new_contact(
    request: Request,
    contact: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_contact(db, contact, current_user)


@app.get("/contacts/", response_model=ContactListResponse)
def get_all_contacts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return {"contacts": get_contacts(db, skip=skip, limit=limit)}


@app.get("/contacts/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    return get_contact_by_id(db, contact_id)


@app.put("/contacts/{contact_id}", response_model=ContactResponse)
def update_existing_contact(
    contact_id: int, contact_data: ContactCreate, db: Session = Depends(get_db)
):
    return update_contact(db, contact_id, contact_data.dict())


@app.delete("/contacts/{contact_id}", response_model=ContactResponse)
def delete_existing_contact(contact_id: int, db: Session = Depends(get_db)):
    return delete_contact(db, contact_id)


@app.get("/contacts/search/", response_model=ContactListResponse)
def search_contacts_api(
    query: str, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)
):
    return search_contacts(db, query, skip=skip, limit=limit)


@app.get("/contacts/upcoming_birthdays/", response_model=ContactListResponse)
def get_upcoming_birthdays(db: Session = Depends(get_db)):
    return upcoming_birthdays(db)

@app.post("/users/{user_id}/avatar")
async def upload_avatar(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = upload(file.file.read(), folder=f"user_avatars/{user_id}")
    url, options = cloudinary_url(result['public_id'], format="jpg", crop="fill", width=100, height=100)

    user.avatar_url = url
    db.add(user)
    db.commit()

    return {"filename": file.filename, "url": url}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return access_token

@app.post("/token/")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    db_user = get_user_by_email(db, form_data.username)
    if db_user is None or not verify_password(
        form_data.password, db_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    refresh_token = create_refresh_token(data={"sub": form_data.username})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post("/token/refresh/")
def refresh_access_token(refresh_token: str = Depends(oauth2_scheme)):
    payload = verify_refresh_token(refresh_token)
    access_token = create_access_token(data={"sub": payload["sub"]})
    return {"access_token": access_token, "token_type": "bearer"}


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    refresh_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return refresh_token


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
