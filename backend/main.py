import os
import logging
from fastapi import FastAPI, Request, HTTPException
from bot_logic import setup_bot_application
from telegram import Update
from telegram.ext import Application

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialisation
try:
    application = setup_bot_application()
    app = FastAPI()
    # On initialise le bot une seule fois au chargement du module.
    # C'est la responsabilité de Gunicorn de gérer les workers.
    # await application.initialize() n'est pas nécessaire ici avec process_update.
except ValueError as e:
    logger.critical(e)
    application = None
    app = None

# --- Endpoints de l'API ---

@app.get("/")
async def root():
    """Endpoint racine pour vérifier que le serveur est en ligne."""
    return {"status": "Bolingo Backend is running!"}

@app.post("/webhook")
async def webhook(request: Request):
    """
    Endpoint qui reçoit les mises à jour de Telegram.
    """
    if not application:
        logger.error("L'application bot n'est pas initialisée.")
        raise HTTPException(status_code=503, detail="Bot service unavailable")

    try:
        body = await request.json()
        update = Update.de_json(body, application.bot)
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Erreur lors du traitement du webhook : {e}", exc_info=True)
        return {"status": "error"}
