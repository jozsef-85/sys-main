import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from database import init_db, SessionLocal, User
from auth import hash_password

load_dotenv()

app = FastAPI(
    title       = "Sysnergia API",
    description = "Backend de sysnergia.com — José Leal Lizana",
    version     = "1.0.0",
    docs_url    = "/api/docs",
    redoc_url   = "/api/redoc",
)

origins = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8080,https://sysnergia.com,https://admin.sysnergia.com"
).split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins     = origins,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

from routes.auth     import router as auth_router
from routes.blog     import router as blog_router
from routes.projects import router as projects_router
from routes.contact  import router as contact_router

app.include_router(auth_router)
app.include_router(blog_router)
app.include_router(projects_router)
app.include_router(contact_router)

@app.get("/api/status", tags=["sistema"])
def api_status():
    return {"status": "online", "service": "sysnergia-backend", "version": "1.0.0"}

@app.get("/", tags=["sistema"])
def root():
    return JSONResponse({"message": "Sysnergia API — /api/docs para ver endpoints."})

@app.on_event("startup")
def on_startup():
    init_db()
    _create_admin()
    print("✓ Sysnergia Backend listo")
    print(f"✓ Docs en: http://localhost:{os.getenv('PORT','8080')}/api/docs")

def _create_admin():
    username = os.getenv("ADMIN_USERNAME", "jose")
    password = os.getenv("ADMIN_PASSWORD", "")
    email    = os.getenv("CONTACT_EMAIL", "josalejandro@gmail.com")
    if not password:
        print("⚠ ADMIN_PASSWORD no configurado.")
        return
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == username).first():
            db.add(User(
                username        = username,
                email           = email,
                hashed_password = hash_password(password),
                is_active       = True,
            ))
            db.commit()
            print(f"✓ Admin '{username}' creado.")
        else:
            print(f"✓ Admin '{username}' ya existe.")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host   = os.getenv("HOST", "127.0.0.1"),
        port   = int(os.getenv("PORT", "8080")),
        reload = os.getenv("ENVIRONMENT") == "development",
    )
