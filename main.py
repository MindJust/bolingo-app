import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Configuration du Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Logique du Bot (Anciennement bot_logic.py) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text = "Salut ! 👋 Prêt(e) pour Bolingo ? Ici, c'est pour des rencontres sérieuses et dans le respect. On y va ?"
    keyboard = [[InlineKeyboardButton("✅ Oui, on y va !", callback_data="show_charte")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == 'show_charte':
        await show_charte_handler(query)
    elif query.data == 'accept_charte':
        await accept_charte_handler(query)

async def show_charte_handler(query):
    charte_text = (
        "Ok. D'abord, lis nos 3 règles. C'est important pour la sécurité. 🛡️\n\n"
        "✅ <b>Respect</b> obligatoire\n"
        "✅ <b>Vrai profil</b>, vraies photos\n"
        "✅ <b>Pas de harcèlement</b>"
    )
    keyboard = [[InlineKeyboardButton("✅ D'accord, j'accepte les règles", callback_data="accept_charte")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=charte_text, reply_markup=reply_markup, parse_mode='HTML')

async def accept_charte_handler(query):
    base_url = os.getenv("RENDER_EXTERNAL_URL")
    if not base_url:
        await query.edit_message_text(text="Erreur : L'adresse du service n'est pas configurée.")
        return
    
    # --- LA CORRECTION EST ICI ---
    # On ajoute un paramètre de version pour forcer le rechargement
    webapp_url_with_version = f"{base_url}?v=2.0"
    
    text = "Charte acceptée ! 👍\nClique sur le bouton ci-dessous pour commencer à créer ton profil."
    keyboard = [[InlineKeyboardButton("✨ Créer mon profil", web_app=WebAppInfo(url=webapp_url_with_version))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup)

# Le reste du fichier est identique...

# --- Gestion du Cycle de Vie et de l'Application FastAPI (Anciennement main.py) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Démarrage du service...")
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
        app.state.bot_app = bot_app
        yield
    finally:
        if hasattr(app.state, 'bot_app'):
            logger.info("Arrêt du service...")
            await app.state.bot_app.bot.delete_webhook()
            await app.state.bot_app.shutdown()

app = FastAPI(lifespan=lifespan)

# --- Endpoints ---

@app.get("/health")
async def health_check():
    return Response(status_code=200)

@app.post("/webhook")
async def webhook(request: Request):
    bot_app = request.app.state.bot_app
    try:
        update = Update.de_json(await request.json(), bot_app.bot)
        await bot_app.process_update(update)
        return Response(status_code=200)
    except Exception:
        logger.error("Erreur dans le webhook", exc_info=True)
        return Response(status_code=500)

# --- Servir le Frontend ---
app.mount("/app", StaticFiles(directory="frontend", html=True), name="webapp")

@app.get("/")
async def read_root():
    return FileResponse('frontend/index.html')
