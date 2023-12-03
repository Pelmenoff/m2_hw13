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

# Load .env file for environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Retrieve secret key and algorithm from environment variables
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

# Initialize rate limiter using remote address as a unique identifier for each user
limiter = Limiter(key_func=get_remote_address)

# Define OAuth2 token URL configuration for token generation and authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Create FastAPI instance
app = FastAPI()

# Define allowed origins for CORS (Cross-Origin Resource Sharing)
origins = [ 
    "http://localhost:8000"
    ]

# Setup middleware for CORS to allow specified origins and HTTP methods
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter to app state and exception handler for rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def get_db():
    """
    Dependency that provides a database session and ensures it is closed after the request is finished.
    
    Yields:
        Session: A database session from SessionLocal.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Configuration for FastAPI-Mail, using environment variables for sensitive data    
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

# Configuration for Cloudinary service, using environment variables for authentication
cloudinary.config(
  cloud_name =os.getenv("CLOUD_NAME"),
  api_key =os.getenv("API_KEY"),
  api_secret =os.getenv("API_SECRET"),
)

def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """
    Retrieve the current user from the database using the provided token.
    
    Args:
        token (str): The OAuth2 token that is used to authenticate the user.
        db (Session): The database session dependency.
        
    Returns:
        User: The user instance that corresponds to the provided token.
        
    Raises:
        HTTPException: If the token is invalid or the user does not exist.
    """
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
    """
    Register a new user in the database and send a verification email.
    
    Args:
        user_in (UserCreate): The user registration information model.
        db (Session): The database session dependency.
        
    Returns:
        dict: A message indicating that the user was created and an email has been sent for verification.
        
    Raises:
        HTTPException: If the email is already registered or verification token generation fails.
    """
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
    """
    Verify a user's email address using the provided token.
    
    Args:
        token (str): The verification token sent to the user's email.
        db (Session): The database session dependency.
        
    Returns:
        dict: A message indicating successful account verification.
        
    Raises:
        HTTPException: If the provided verification token is invalid.
    """
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
    """
    Create a new contact associated with the current user.
    
    Args:
        request (Request): The request instance.
        contact (ContactCreate): The contact model containing the data for the new contact.
        db (Session): The database session dependency.
        current_user (User): The current user creating the contact, obtained via token authentication.
    
    Returns:
        ContactResponse: The newly created contact data.
    
    Raises:
        HTTPException: If the contact cannot be created.
    """
    return create_contact(db, contact, current_user)


@app.get("/contacts/", response_model=ContactListResponse)
def get_all_contacts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Retrieve a list of contacts from the database with pagination.
    
    Args:
        skip (int): The number of items to skip before starting to collect the result set.
        limit (int): The maximum number of items to return.
        db (Session): The database session dependency.
    
    Returns:
        ContactListResponse: The list of contacts with the applied pagination.
    """
    return {"contacts": get_contacts(db, skip=skip, limit=limit)}


@app.get("/contacts/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single contact by its ID.
    
    Args:
        contact_id (int): The unique identifier of the contact.
        db (Session): The database session dependency.
    
    Returns:
        ContactResponse: The requested contact data.
    
    Raises:
        HTTPException: If the contact with the given ID is not found.
    """
    return get_contact_by_id(db, contact_id)


@app.put("/contacts/{contact_id}", response_model=ContactResponse)
def update_existing_contact(
    contact_id: int, contact_data: ContactCreate, db: Session = Depends(get_db)
):
    """
    Update an existing contact's information by its ID.
    
    Args:
        contact_id (int): The unique identifier of the contact to update.
        contact_data (ContactCreate): The updated contact model containing the new data.
        db (Session): The database session dependency.
    
    Returns:
        ContactResponse: The updated contact data.
    
    Raises:
        HTTPException: If the update operation fails.
    """
    return update_contact(db, contact_id, contact_data.dict())


@app.delete("/contacts/{contact_id}", response_model=ContactResponse)
def delete_existing_contact(contact_id: int, db: Session = Depends(get_db)):
    """
    Delete an existing contact by its ID.
    
    Args:
        contact_id (int): The unique identifier of the contact to delete.
        db (Session): The database session dependency.
    
    Returns:
        ContactResponse: The response model indicating successful deletion.
    
    Raises:
        HTTPException: If the deletion operation fails or the contact is not found.
    """
    return delete_contact(db, contact_id)


@app.get("/contacts/search/", response_model=ContactListResponse)
def search_contacts_api(
    query: str, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)
):
    """
    Search for contacts using a query string and apply pagination to the results.
    
    Args:
        query (str): The search query string used to filter contacts.
        skip (int): The number of items to skip before starting to collect the result set.
        limit (int): The maximum number of items to return.
        db (Session): The database session dependency.
    
    Returns:
        ContactListResponse: A list of contacts that match the search query with applied pagination.
    """
    return search_contacts(db, query, skip=skip, limit=limit)


@app.get("/contacts/upcoming_birthdays/", response_model=ContactListResponse)
def get_upcoming_birthdays(db: Session = Depends(get_db)):
    """
    Retrieve a list of contacts with upcoming birthdays.
    
    Args:
        db (Session): The database session dependency.
    
    Returns:
        ContactListResponse: A list of contacts with upcoming birthdays.
    """
    return upcoming_birthdays(db)

@app.post("/users/{user_id}/avatar")
async def upload_avatar(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a user avatar image to the server and update the user's avatar URL in the database.
    
    Args:
        user_id (int): The ID of the user for whom the avatar is being uploaded.
        file (UploadFile): The image file to upload.
        db (Session): The database session dependency.
    
    Raises:
        HTTPException: If the user is not found.
    
    Returns:
        dict: A dictionary containing the filename and URL of the uploaded avatar.
    """
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
    """
    Create a new access token using the provided data and expiry period.
    
    Args:
        data (dict): The data to encode in the JWT.
    
    Returns:
        str: The encoded JWT access token.
    """
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
    """
    Authenticate a user and provide an access token and a refresh token.
    
    Args:
        form_data (OAuth2PasswordRequestForm): The form data containing the username and password.
        db (Session): The database session dependency.
    
    Raises:
        HTTPException: If authentication fails.
    
    Returns:
        dict: A dictionary with access token, refresh token, and token type.
    """
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
    """
    Refresh an access token using a valid refresh token.
    
    Args:
        refresh_token (str): The refresh token used to obtain a new access token.
    
    Raises:
        HTTPException: If the refresh token is invalid.
    
    Returns:
        dict: A dictionary containing the new access token and token type.
    """
    payload = verify_refresh_token(refresh_token)
    access_token = create_access_token(data={"sub": payload["sub"]})
    return {"access_token": access_token, "token_type": "bearer"}


def create_refresh_token(data: dict):
    """
    Create a new refresh token using the provided data and expiry period.
    
    Args:
        data (dict): The data to encode in the JWT.
    
    Returns:
        str: The encoded JWT refresh token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    refresh_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return refresh_token


def verify_refresh_token(token: str):
    """
    Verify the validity of a refresh token and decode its payload.
    
    Args:
        token (str): The refresh token to verify and decode.
    
    Raises:
        HTTPException: If the refresh token is invalid or expired.
    
    Returns:
        dict: The decoded data payload from the refresh token.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
