import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, Project
from auth import get_current_user, User

router = APIRouter(prefix="/api/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    title:       str
    description: Optional[str] = None
    tech_stack:  Optional[List[str]] = []
    repo_url:    Optional[str] = None
    demo_url:    Optional[str] = None
    status:      str = "en progreso"
    private:     bool = True

class ProjectUpdate(BaseModel):
    title:       Optional[str] = None
    description: Optional[str] = None
    tech_stack:  Optional[List[str]] = None
    repo_url:    Optional[str] = None
    demo_url:    Optional[str] = None
    status:      Optional[str] = None
    private:     Optional[bool] = None

class ProjectResponse(BaseModel):
    id:          int
    title:       str
    description: Optional[str]
    tech_stack:  List[str]
    repo_url:    Optional[str]
    demo_url:    Optional[str]
    status:      str
    private:     bool
    class Config:
        from_attributes = True

def to_dict(p: Project) -> dict:
    d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    try:
        d["tech_stack"] = json.loads(p.tech_stack) if p.tech_stack else []
    except Exception:
        d["tech_stack"] = []
    return d

@router.get("/public", response_model=List[ProjectResponse])
def list_public(db: Session=Depends(get_db)):
    return [to_dict(p) for p in db.query(Project).filter(Project.private==False).all()]

@router.get("", response_model=List[ProjectResponse])
def list_all(db: Session=Depends(get_db), _: User=Depends(get_current_user)):
    return [to_dict(p) for p in db.query(Project).order_by(Project.created_at.desc()).all()]

@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(data: ProjectCreate, db: Session=Depends(get_db), user: User=Depends(get_current_user)):
    p = Project(title=data.title, description=data.description,
                tech_stack=json.dumps(data.tech_stack or []), repo_url=data.repo_url,
                demo_url=data.demo_url, status=data.status, private=data.private, author_id=user.id)
    db.add(p); db.commit(); db.refresh(p)
    return to_dict(p)

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, data: ProjectUpdate, db: Session=Depends(get_db), _: User=Depends(get_current_user)):
    p = db.query(Project).filter(Project.id==project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")
    if data.title       is not None: p.title=data.title
    if data.description is not None: p.description=data.description
    if data.tech_stack  is not None: p.tech_stack=json.dumps(data.tech_stack)
    if data.repo_url    is not None: p.repo_url=data.repo_url
    if data.demo_url    is not None: p.demo_url=data.demo_url
    if data.status      is not None: p.status=data.status
    if data.private     is not None: p.private=data.private
    db.commit(); db.refresh(p)
    return to_dict(p)

@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session=Depends(get_db), _: User=Depends(get_current_user)):
    p = db.query(Project).filter(Project.id==project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")
    db.delete(p); db.commit()
