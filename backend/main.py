import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application
from bot_logic import setup_bot_application

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Initialisation ---
# Le bot est initialisé une seule fois au chargement du module.
try:
    application = setup_bot_application()
    app = FastAPI()
except ValueError as e:
    logger.critical(e)
    # Empêche le démarrage si le token est manquant.
    application = None
    app = None

# --- Endpoints de l'API ---

@app.get("/")
async def root():
    """Endpoint racine pour la vérification de santé de Render."""
    return {"status": "Bolingo Backend is running!"}

@app.post("/webhook")
async def webhook(request: Request):
    """Endpoint qui reçoit les mises à jour de Telegram."""
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

@app.get("/setup_webhook")
async def setup_webhook():
    """Endpoint manuel et secret pour configurer le webhook."""
    webhook_url = os.getenv("RENDER_EXTERNAL_URL")
    if not webhook_url:
        logger.error("RENDER_EXTERNAL_URL n'est pas définie.")
        return {"status": "error", "message": "URL de Render non trouvée"}
    
    try:
        await application.bot.set_webhook(
            url=f"{webhook_url}/webhook",
            allowed_updates=Update.ALL_TYPES
        )
        logger.info(f"Webhook configuré avec succès sur {webhook_url}/webhook")
        return {"status": "ok", "message": f"Webhook configuré sur {webhook_url}/webhook"}
    except Exception as e:
        logger.error(f"Erreur lors de la configuration du webhook : {e}")
        return {"status": "error", "message": str(e)}
