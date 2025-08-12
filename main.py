import os
import logging
import hmac
import hashlib
from urllib.parse import unquote
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import google.generativeai as genai

# --- Configuration & Initialisation ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- MODÈLE DE SÉCURITÉ ---
async def validate_webapp_data(request: Request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('tma '):
        raise HTTPException(status_code=401, detail="Non autorisé")
    
    init_data_str = auth_header.split(' ', 1)[1]
    
    try:
        secret_key = hmac.new("WebAppData".encode(), BOT_TOKEN.encode(), hashlib.sha256).digest()
        data_check_string = "\n".join(sorted([
            f"{key}={value}" for key, value in 
            [item.split('=', 1) for item in unquote(init_data_str).split('&') if item.split('=', 1)[0] != 'hash']
        ]))
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        sent_hash = next((item.split('=', 1)[1] for item in init_data_str.split('&') if item.startswith('hash=')), None)

        if not sent_hash or not hmac.compare_digest(expected_hash, sent_hash):
            raise HTTPException(status_code=401, detail="Validation échouée")
            
        user_data = next((item.split('=', 1)[1] for item in init_data_str.split('&') if item.startswith('user=')), None)
        return {"init_data": init_data_str, "user": unquote(user_data)}

    except Exception as e:
        logger.error(f"Erreur de validation: {e}")
        raise HTTPException(status_code=401, detail="Validation invalide")

# --- Modèles de Données ---
class ProfileChoices(BaseModel):
    vibe: str
    weekend: str
    valeurs: str
    plaisir: str

# --- Logique de l'IA (désactivée pour le test) ---
def generate_ai_description(choices: ProfileChoices) -> str:
    # ... le code de l'IA reste ici, mais ne sera pas appelé par l'endpoint de test
    pass

# --- Logique du Bot ---
# ... (inchangée)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text = "Salut ! 👋 Prêt(e) pour Bolingo ? Ici, c'est pour des rencontres sérieuses et dans le respect. On y va ?"
    keyboard = [[InlineKeyboardButton("✅ Oui, on y va !", callback_data="show_charte")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == 'show_charte': await show_charte_handler(query)
    elif query.data == 'accept_charte': await accept_charte_handler(query)
async def show_charte_handler(query):
    charte_text = "Ok. D'abord, lis nos 3 règles. C'est important pour la sécurité. 🛡️\n\n✅ <b>Respect</b> obligatoire\n✅ <b>Vrai profil</b>, vraies photos\n✅ <b>Pas de harcèlement</b>"
    keyboard = [[InlineKeyboardButton("✅ D'accord, j'accepte les règles", callback_data="accept_charte")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=charte_text, reply_markup=reply_markup, parse_mode='HTML')
async def accept_charte_handler(query):
    base_url = os.getenv("RENDER_EXTERNAL_URL")
    if not base_url:
        await query.edit_message_text(text="Erreur : L'adresse du service n'est pas configurée.")
        return
    webapp_url_with_version = f"{base_url}?v=final_secure_v2"
    text = "Charte acceptée ! 👍\nClique sur le bouton ci-dessous pour commencer à créer ton profil."
    keyboard = [[InlineKeyboardButton("✨ Créer mon profil", web_app=WebAppInfo(url=webapp_url_with_version))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup)
def setup_bot_application():
    if not BOT_TOKEN: raise ValueError("Le token Telegram n'est pas défini.")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    return application

# --- Cycle de Vie & App FastAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Démarrage du service...")
    bot_app = setup_bot_application()
    await bot_app.initialize()
    webhook_url = os.getenv("RENDER_EXTERNAL_URL")
    if webhook_url:
        await bot_app.bot.set_webhook(url=f"{webhook_url}/api/webhook", allowed_updates=Update.ALL_TYPES)
    app.state.bot_app = bot_app
    yield
    logger.info("Arrêt du service...")
    await app.state.bot_app.bot.delete_webhook()
    await app.state.bot_app.shutdown()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Endpoints API ---
@app.post("/api/webhook")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), request.app.state.bot_app.bot)
    await request.app.state.bot_app.process_update(update)
    return Response(status_code=200)

@app.post("/api/generate-description")
async def generate_description_api(choices: ProfileChoices, auth: dict = Depends(validate_webapp_data)):
    logger.info(f"Requête de description validée pour l'utilisateur : {auth.get('user')}")
    
    # --- LA MODIFICATION EST ICI ---
    # On met l'appel à l'IA en commentaire pour le test.
    # description = generate_ai_description(choices) 
    
    # On renvoie une description de test INSTANTANÉE.
    description = f"TEST DE VITESSE : La plomberie fonctionne ! Vibe choisie : {choices.vibe}."
    
    return {"description": description}

# --- Servir le Frontend ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
