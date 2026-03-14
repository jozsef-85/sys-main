from sqlalchemy import (
    create_engine, Column, Integer, String,
    Text, Boolean, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sysnergia:password@localhost:5432/sysnergia_db"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(50), unique=True, nullable=False, index=True)
    email           = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    posts    = relationship("Post", back_populates="author")
    projects = relationship("Project", back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    slug        = Column(String(220), unique=True, nullable=False, index=True)
    excerpt     = Column(String(400))
    content     = Column(Text, nullable=False)
    cover_image = Column(String(500))
    tags        = Column(String(300))
    published   = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))
    author_id   = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")

class Project(Base):
    __tablename__ = "projects"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text)
    tech_stack  = Column(String(400))
    repo_url    = Column(String(500))
    demo_url    = Column(String(500))
    status      = Column(String(50), default="en progreso")
    private     = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    author_id   = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="projects")

class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    email      = Column(String(120), nullable=False)
    subject    = Column(String(200))
    message    = Column(Text, nullable=False)
    read       = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
