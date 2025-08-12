import os
import logging
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application
from bot_logic import setup_bot_application

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Gestion du Cycle de Vie de l'Application (LA SOLUTION) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gère les actions de démarrage et d'arrêt pour être sûr que le bot est
    initialisé une seule fois et proprement.
    """
    logger.info("Phase de démarrage (startup)...")
    try:
        # Initialiser le bot
        bot_app = setup_bot_application()
        await bot_app.initialize()

        # Configurer le webhook
        webhook_url = os.getenv("RENDER_EXTERNAL_URL")
        if webhook_url:
            await bot_app.bot.set_webhook(
                url=f"{webhook_url}/webhook",
                allowed_updates=Update.ALL_TYPES
            )
            logger.info(f"Webhook configuré sur {webhook_url}/webhook")
        else:
            logger.warning("RENDER_EXTERNAL_URL non trouvée. Webhook non configuré.")

        # Stocker l'instance du bot pour qu'elle soit accessible partout
        app.state.bot_app = bot_app
        logger.info("Application bot initialisée et webhook configuré.")
        
        # Le "yield" est le moment où l'application est en cours d'exécution
        yield
        
    finally:
        # Code exécuté à l'arrêt
        if hasattr(app.state, 'bot_app'):
            logger.info("Phase d'arrêt (shutdown)...")
            await app.state.bot_app.bot.delete_webhook()
            await app.state.bot_app.shutdown()
            logger.info("Webhook supprimé et application bot arrêtée.")

# Crée l'application FastAPI avec le cycle de vie géré
app = FastAPI(lifespan=lifespan)

# --- Endpoints de l'API ---

@app.get("/health")
async def health_check():
    """
    Endpoint dédié pour le Health Check de Render.
    Il répond simplement "OK" pour dire que le service est en vie.
    """
    return Response(status_code=200)

@app.post("/webhook")
async def webhook(request: Request):
    """Endpoint qui reçoit les mises à jour de Telegram."""
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
