import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application
from bot_logic import setup_bot_application

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Gestion du Cycle de Vie ---

@asynccontextmanager
async def lifespan(app: FastAPI):
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

# --- Servir la Web App (NOUVELLE SECTION) ---

# Monter le dossier 'frontend' comme un répertoire de fichiers statiques
# La route est vide pour que le serveur cherche à la racine du domaine
app.mount("/app", StaticFiles(directory="frontend", html=True), name="webapp")

@app.get("/")
async def read_root():
    # Redirige la racine du site vers la Web App
    return FileResponse('frontend/index.html')
