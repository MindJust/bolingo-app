import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application
from bot_logic import setup_bot_application
import pathlib # On importe une librairie pour gérer les chemins de fichiers

# Définir le chemin de base du projet (la racine où se trouvent 'backend' et 'frontend')
BASE_DIR = pathlib.Path(__file__).parent.parent

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Gestion du Cycle de Vie ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # (Le contenu de lifespan ne change pas, il reste identique)
    logger.info("Phase de démarrage (startup)...")
    try:
        bot_app = setup_bot_application()
        await bot_app.initialize()
        webhook_url = os.getenv("RENDER_EXTERNAL_URL")
        if webhook_url:
            await bot_app.bot.set_webhook(
                url=f"{webhook_url}/webhook",
                allowed_updates=Update.ALL_TYPES
            )
            logger.info(f"Webhook configuré sur {webhook_url}/webhook")
        else:
            logger.warning("RENDER_EXTERNAL_URL non trouvée. Webhook non configuré.")
        app.state.bot_app = bot_app
        logger.info("Application bot initialisée et webhook configuré.")
        yield
    finally:
        if hasattr(app.state, 'bot_app'):
            logger.info("Phase d'arrêt (shutdown)...")
            await app.state.bot_app.bot.delete_webhook()
            await app.state.bot_app.shutdown()
            logger.info("Webhook supprimé et application bot arrêtée.")

# --- Création de l'application FastAPI ---

app = FastAPI(lifespan=lifespan)

# --- Endpoints de l'API ---

@app.get("/health")
async def health_check():
    return Response(status_code=200)

@app.post("/webhook")
async def webhook(request: Request):
    # (Le contenu de webhook ne change pas, il reste identique)
    if not hasattr(request.app.state, 'bot_app'):
        logger.error("L'application bot n'est pas disponible.")
        return Response(status_code=500)
    bot_app = request.app.state.bot_app
    try:
        update = Update.de_json(await request.json(), bot_app.bot)
        await bot_app.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Erreur lors du traitement du webhook : {e}", exc_info=True)
        return Response(status_code=500)

# --- Servir la Web App (SECTION CORRIGÉE) ---

# Monter le dossier 'frontend' en utilisant le chemin de base correct
# BASE_DIR / "frontend" construit le chemin absolu vers le dossier frontend
app.mount("/app", StaticFiles(directory=BASE_DIR / "frontend", html=True), name="webapp")

@app.get("/")
async def read_root():
    # Redirige la racine du site vers le fichier index.html correct
    return FileResponse(BASE_DIR / "frontend" / "index.html")
