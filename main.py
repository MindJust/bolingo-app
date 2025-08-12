import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pydantic import BaseModel # Importé pour définir la structure des données
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Modèles de Données (pour l'API) ---
class ProfileChoices(BaseModel):
    vibe: str
    weekend: str
    valeurs: str
    plaisir: str

# --- Logique du Bot ---
# (Toute la logique du bot reste identique, de 'async def start' à 'def setup_bot_application')
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
    
    webapp_url_with_version = f"{base_url}?v=final" # Version finale pour vider le cache
    
    text = "Charte acceptée ! 👍\nClique sur le bouton ci-dessous pour commencer à créer ton profil."
    keyboard = [[InlineKeyboardButton("✨ Créer mon profil", web_app=WebAppInfo(url=webapp_url_with_version))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup)

def setup_bot_application():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Le token Telegram n'est pas défini.")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    return application

# --- Gestion du Cycle de Vie et de l'Application FastAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # (Le contenu de lifespan reste identique)
    logger.info("Démarrage du service...")
    bot_app = setup_bot_application()
    await bot_app.initialize()
    webhook_url = os.getenv("RENDER_EXTERNAL_URL")
    if webhook_url:
        full_webhook_url = f"{webhook_url}/api/webhook"
        await bot_app.bot.set_webhook(url=full_webhook_url, allowed_updates=Update.ALL_TYPES)
        logger.info(f"Webhook configuré sur {full_webhook_url}")
    app.state.bot_app = bot_app
    yield
    logger.info("Arrêt du service...")
    await app.state.bot_app.bot.delete_webhook()
    await app.state.bot_app.shutdown()

app = FastAPI(lifespan=lifespan)

# --- Endpoints API ---

@app.post("/api/webhook")
async def webhook(request: Request):
    bot_app = request.app.state.bot_app
    update = Update.de_json(await request.json(), bot_app.bot)
    await bot_app.process_update(update)
    return Response(status_code=200)

# --- NOUVELLE SECTION : API POUR LA WEB APP ---
@app.post("/api/generate-description")
async def generate_description(choices: ProfileChoices):
    # Pour l'instant, on ne fait que recevoir les choix et les afficher dans les logs
    # pour prouver que la connexion fonctionne.
    logger.info(f"Reçu les choix du Profile Builder : {choices.dict()}")
    
    # Plus tard, nous appellerons l'API Gemini ici.
    
    # On renvoie une fausse description pour le test.
    return {"description": f"Ceci est une description générée pour quelqu'un de {choices.vibe} qui aime les week-ends {choices.weekend}."}

# --- Servir le Frontend ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
