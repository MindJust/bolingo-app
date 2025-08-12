import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.main import api_router  # On importe le routeur de notre API

# Crée l'application principale
app = FastAPI()

# Inclut toutes les routes de l'API définies dans backend/main.py
# avec un préfixe /api
app.include_router(api_router, prefix="/api")

# Monte le dossier frontend pour servir les fichiers statiques
app.mount("/app", StaticFiles(directory="frontend", html=True), name="webapp")

@app.get("/")
async def read_root():
    """Redirige la racine du site vers la Web App."""
    return FileResponse('frontend/index.html')
