import json
import re
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from database import get_db, Post
from auth import get_current_user, User

router = APIRouter(prefix="/api/posts", tags=["blog"])

class PostCreate(BaseModel):
    title:       str = Field(min_length=3, max_length=200)
    excerpt:     Optional[str] = Field(default=None, max_length=400)
    content:     str = Field(min_length=1, max_length=50000)
    cover_image: Optional[str] = Field(default=None, max_length=500)
    tags:        List[str] = Field(default_factory=list, max_length=20)
    published:   bool = False

class PostUpdate(BaseModel):
    title:       Optional[str] = Field(default=None, min_length=3, max_length=200)
    excerpt:     Optional[str] = Field(default=None, max_length=400)
    content:     Optional[str] = Field(default=None, min_length=1, max_length=50000)
    cover_image: Optional[str] = Field(default=None, max_length=500)
    tags:        Optional[List[str]] = None
    published:   Optional[bool] = None

class PostResponse(BaseModel):
    id:          int
    title:       str
    slug:        str
    excerpt:     Optional[str]
    content:     str
    cover_image: Optional[str]
    tags:        List[str]
    published:   bool
    created_at:  datetime
    updated_at:  datetime
    class Config:
        from_attributes = True

class PostSummary(BaseModel):
    id:          int
    title:       str
    slug:        str
    excerpt:     Optional[str]
    cover_image: Optional[str]
    tags:        List[str]
    published:   bool
    created_at:  datetime
    class Config:
        from_attributes = True

def slugify(text: str) -> str:
    text = text.lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")

def unique_slug(db: Session, base: str, exclude_id: int = None) -> str:
    slug, i = base, 1
    while True:
        q = db.query(Post).filter(Post.slug == slug)
        if exclude_id:
            q = q.filter(Post.id != exclude_id)
        if not q.first():
            return slug
        slug = f"{base}-{i}"; i += 1

def parse_tags(post: Post) -> List[str]:
    try:
        return json.loads(post.tags) if post.tags else []
    except Exception:
        return []

def to_dict(post: Post) -> dict:
    d = {c.name: getattr(post, c.name) for c in post.__table__.columns}
    d["tags"] = parse_tags(post)
    return d

@router.get("", response_model=List[PostSummary])
def list_posts(tag: Optional[str]=Query(None), limit: int=Query(20,ge=1,le=100),
               skip: int=Query(0,ge=0), db: Session=Depends(get_db)):
    q = db.query(Post).filter(Post.published == True)
    if tag:
        q = q.filter(Post.tags.contains(tag))
    return [to_dict(p) for p in q.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()]

@router.get("/admin/all", response_model=List[PostSummary])
def list_all(db: Session=Depends(get_db), _: User=Depends(get_current_user)):
    return [to_dict(p) for p in db.query(Post).order_by(Post.created_at.desc()).all()]

@router.get("/{slug}", response_model=PostResponse)
def get_post(slug: str, db: Session=Depends(get_db)):
    post = db.query(Post).filter(Post.slug==slug, Post.published==True).first()
    if not post:
        raise HTTPException(status_code=404, detail="Artículo no encontrado.")
    return to_dict(post)

@router.post("", response_model=PostResponse, status_code=201)
def create_post(data: PostCreate, db: Session=Depends(get_db), user: User=Depends(get_current_user)):
    post = Post(title=data.title, slug=unique_slug(db, slugify(data.title)),
                excerpt=data.excerpt, content=data.content, cover_image=data.cover_image,
                tags=json.dumps(data.tags or []), published=data.published, author_id=user.id)
    db.add(post); db.commit(); db.refresh(post)
    return to_dict(post)

@router.put("/{post_id}", response_model=PostResponse)
def update_post(post_id: int, data: PostUpdate, db: Session=Depends(get_db), _: User=Depends(get_current_user)):
    post = db.query(Post).filter(Post.id==post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Artículo no encontrado.")
    if data.title       is not None: post.title=data.title; post.slug=unique_slug(db,slugify(data.title),exclude_id=post_id)
    if data.excerpt     is not None: post.excerpt=data.excerpt
    if data.content     is not None: post.content=data.content
    if data.cover_image is not None: post.cover_image=data.cover_image
    if data.tags        is not None: post.tags=json.dumps(data.tags)
    if data.published   is not None: post.published=data.published
    post.updated_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(post)
    return to_dict(post)

@router.delete("/{post_id}", status_code=204)
def delete_post(post_id: int, db: Session=Depends(get_db), _: User=Depends(get_current_user)):
    post = db.query(Post).filter(Post.id==post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Artículo no encontrado.")
    db.delete(post); db.commit()
