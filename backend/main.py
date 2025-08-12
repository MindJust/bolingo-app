import os
import logging
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application
from bot_logic import setup_bot_application

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Gestion du Cycle de Vie de l'Application ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gère les actions de démarrage et d'arrêt.
    C'est la méthode moderne pour les événements startup/shutdown dans FastAPI.
    """
    logger.info("Démarrage du service...")
    # Initialisation du bot
    try:
        bot_app = setup_bot_application()
        await bot_app.initialize()
        
        # Stocker l'instance du bot dans l'état de l'application FastAPI
        app.state.bot_app = bot_app
        logger.info("Application bot initialisée avec succès.")
        
        # Le "yield" est le moment où l'application est en cours d'exécution
        yield
        
    finally:
        # Code exécuté à l'arrêt
        if hasattr(app.state, 'bot_app'):
            logger.info("Arrêt du service...")
            await app.state.bot_app.shutdown()
            logger.info("Application bot arrêtée proprement.")


# Crée l'application FastAPI avec le cycle de vie géré
app = FastAPI(lifespan=lifespan)


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
    bot_app = request.app.state.bot_app
    if not bot_app:
        logger.error("L'application bot n'est pas disponible dans l'état de l'application.")
        raise HTTPException(status_code=503, detail="Bot service unavailable")

    try:
        body = await request.json()
        update = Update.de_json(body, bot_app.bot)
        await bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Erreur lors du traitement du webhook : {e}", exc_info=True)
        return {"status": "error"}
