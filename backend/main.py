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

# Initialisation des applications
# Cela est maintenant sûr car chaque worker aura sa propre instance en mémoire
try:
    application = setup_bot_application()
    app = FastAPI()
except ValueError as e:
    logger.critical(e)
    # Si le token manque, on empêche le démarrage
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
    Il les transmet à la librairie python-telegram-bot pour traitement.
    """
    if not application:
        logger.error("L'application bot n'est pas initialisée. Le token est-il manquant ?")
        raise HTTPException(status_code=503, detail="Bot service unavailable")

    try:
        body = await request.json()
        
        # Créer un objet Update à partir du corps de la requête
        update = Update.de_json(body, application.bot)
        
        # Traiter l'update directement au lieu de le mettre en file d'attente
        await application.process_update(update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Erreur lors du traitement du webhook : {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")
