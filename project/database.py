from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Retrieve the database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

# Create an SQLAlchemy engine that will interface with the database
engine = create_engine(DATABASE_URL)

# Store metadata for the database which is used when generating the schema
metadata = MetaData()

# Configure the session class to create new database session instances
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative class definitions
Base = declarative_base(metadata=metadata)