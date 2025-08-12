import os
import logging
import hmac
import hashlib
import asyncio
from urllib.parse import unquote
from fastapi import FastAPI, Request, Response, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Json
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import google.genergenerativeai as genai
import json

# --- Configuration & Initialisation ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- Modèles de Données ---
class ProfileChoices(BaseModel): vibe: str; weekend: str; valeurs: str; plaisir: str
class UserData(BaseModel): id: int; first_name: str
class AuthData(BaseModel): init_data: str; user: UserData

# --- MODÈLE DE SÉCURITÉ ---
async def validate_webapp_data(request: Request) -> AuthData:
    # ... (inchangé)
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('tma '): raise HTTPException(status_code=401, detail="Non autorisé")
    init_data_str = auth_header.split(' ', 1)[1]
    try:
        secret_key = hmac.new("WebAppData".encode(), BOT_TOKEN.encode(), hashlib.sha256).digest()
        data_check_string = "\n".join(sorted([f"{k}={v}" for k, v in [item.split('=', 1) for item in unquote(init_data_str).split('&') if item.split('=', 1)[0] != 'hash']]))
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        sent_hash = next((item.split('=', 1)[1] for item in init_data_str.split('&') if item.startswith('hash=')), None)
        if not sent_hash or not hmac.compare_digest(expected_hash, sent_hash): raise HTTPException(status_code=401, detail="Validation échouée")
        user_json_str = unquote(next((item.split('=', 1)[1] for item in init_data_str.split('&') if item.startswith('user=')), '{}'))
        user_data = json.loads(user_json_str)
        return AuthData(init_data=init_data_str, user=UserData(**user_data))
    except Exception as e:
        logger.error(f"Erreur de validation: {e}")
        raise HTTPException(status_code=401, detail="Validation invalide")

# --- Logique de l'IA ---
async def generate_and_send_description(user_id: int, choices: ProfileChoices, bot_app: Application):
    logger.info(f"Début de la génération de la description en arrière-plan pour l'utilisateur {user_id}")
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            await bot_app.bot.send_message(chat_id=user_id, text="Erreur : la configuration de l'IA est manquante.")
            return
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "Tu es Bolingo, un assistant de rencontre bienveillant. Rédige une description de profil courte (2-3 phrases), sincère et positive à partir des choix suivants :\n"
            f"- Vibe : {choices.vibe}\n- Weekend : {choices.weekend}\n- Valeurs : {choices.valeurs}\n- Plaisir : {choices.plaisir}\n\n"
            "Termine par une phrase d'ouverture. N'utilise aucun formatage markdown ou html."
        )
        response = await model.generate_content_async(prompt)
        description = response.text.strip()
        
        message_text = f"✨ <b>Voici la description de profil que j'ai préparée pour toi :</b>\n\n{description}\n\nTu pourras la modifier plus tard. La prochaine étape sera d'ajouter tes photos."
        # --- LA CORRECTION EST ICI ---
        await bot_app.bot.send_message(chat_id=user_id, text=message_text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Erreur lors de la génération IA en arrière-plan : {e}")
        await bot_app.bot.send_message(chat_id=user_id, text="Oups, une erreur est survenue lors de la création de ta description. Nous allons y remédier.")

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
    webapp_url_with_version = f"{base_url}?v=final_secure_v3"
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
    # ... (inchangé)
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
    # ... (inchangé)
    update = Update.de_json(await request.json(), request.app.state.bot_app.bot)
    await request.app.state.bot_app.process_update(update)
    return Response(status_code=200)

@app.post("/api/generate-description")
async def generate_description_api(choices: ProfileChoices, background_tasks: BackgroundTasks, auth: AuthData = Depends(validate_webapp_data)):
    user_id = auth.user.id
    logger.info(f"Requête reçue pour l'utilisateur {user_id}. Lancement en arrière-plan.")
    background_tasks.add_task(generate_and_send_description, user_id, choices, app.state.bot_app)
    return {"status": "ok", "message": "Ta description est en cours de création. Tu vas la recevoir par message dans un instant !"}

# --- Servir le Frontend ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
