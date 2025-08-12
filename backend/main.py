from fastapi import FastAPI, Request
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Création de l'application FastAPI
app = FastAPI()

@app.get("/")
async def root():
    """
    Endpoint racine pour vérifier que le serveur est en ligne.
    """
    logger.info("Health check endpoint was called.")
    return {"status": "KeteKete Backend is running!"}

@app.post("/webhook")
async def webhook(request: Request):
    """
    Endpoint qui recevra les mises à jour de Telegram.
    Pour l'instant, il ne fait qu'accuser réception.
    """
    body = await request.json()
    logger.info(f"Received update from Telegram: {body}")
    return {"status": "ok"}
