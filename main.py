import os
import logging
import hmac
import hashlib
from urllib.parse import unquote
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import google.generativeai as genai
import json

# --- Configuration & Initialisation ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# On initialise le bot une seule fois au chargement du module. C'est la méthode la plus simple.
bot_app = Application.builder().token(BOT_TOKEN).build()

# --- Modèles de Données & Sécurité ---
class ProfileChoices(BaseModel): vibe: str; weekend: str; valeurs: str; plaisir: str
class UserData(BaseModel): id: int; first_name: str
class AuthData(BaseModel): init_data: str; user: UserData

async def validate_webapp_data(request: Request) -> AuthData:
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
def generate_ai_description(choices: ProfileChoices) -> str:
    # ... (inchangé)
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key: return "Erreur : la configuration de l'IA est manquante."
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "Tu es Bolingo. Rédige une description de profil courte (2-3 phrases), sincère et positive à partir des choix suivants :\n"
            f"- Vibe : {choices.vibe}\n- Weekend : {choices.weekend}\n- Valeurs : {choices.valeurs}\n- Plaisir : {choices.plaisir}\n\n"
            "Termine par une phrase d'ouverture."
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Erreur lors de la génération IA : {e}")
        return "Je suis une personne intéressante qui cherche à faire de belles rencontres."

# --- Logique du Bot ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (inchangé)
    welcome_text = "Salut ! 👋 Prêt(e) pour Bolingo ? Ici, c'est pour des rencontres sérieuses et dans le respect. On y va ?"
    keyboard = [[InlineKeyboardButton("✅ Oui, on y va !", callback_data="show_charte")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (inchangé)
    query = update.callback_query
    await query.answer()
    if query.data == 'show_charte': await show_charte_handler(query)
    elif query.data == 'accept_charte': await accept_charte_handler(query)
async def show_charte_handler(query):
    # ... (inchangé)
    charte_text = "Ok. D'abord, lis nos 3 règles. C'est important pour la sécurité. 🛡️\n\n✅ <b>Respect</b> obligatoire\n✅ <b>Vrai profil</b>, vraies photos\n✅ <b>Pas de harcèlement</b>"
    keyboard = [[InlineKeyboardButton("✅ D'accord, j'accepte les règles", callback_data="accept_charte")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=charte_text, reply_markup=reply_markup, parse_mode='HTML')
async def accept_charte_handler(query):
    # ... (inchangé)
    base_url = os.getenv("RENDER_EXTERNAL_URL")
    if not base_url: await query.edit_message_text(text="Erreur : L'adresse du service n'est pas configurée."); return
    webapp_url_with_version = f"{base_url}?v=final_stable"
    text = "Charte acceptée ! 👍\nClique sur le bouton ci-dessous pour commencer à créer ton profil."
    keyboard = [[InlineKeyboardButton("✨ Créer mon profil", web_app=WebAppInfo(url=webapp_url_with_version))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup)

# --- Initialisation des Handlers ---
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(button_handler))

# --- Application FastAPI ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Endpoints API ---
@app.post("/api/webhook")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), bot_app.bot)
    await bot_app.process_update(update)
    return Response(status_code=200)

@app.post("/api/generate-description")
async def generate_description_api(choices: ProfileChoices, auth: dict = Depends(validate_webapp_data)):
    description = generate_ai_description(choices)
    return {"description": description}

@app.get("/api/setup")
async def setup_webhook():
    webhook_url = os.getenv("RENDER_EXTERNAL_URL")
    if not webhook_url: return Response(content="RENDER_EXTERNAL_URL non trouvée", status_code=500)
    full_webhook_url = f"{webhook_url}/api/webhook"
    await bot_app.bot.set_webhook(url=full_webhook_url, allowed_updates=Update.ALL_TYPES)
    return Response(content=f"Webhook configuré sur {full_webhook_url}", status_code=200)

# --- Servir le Frontend ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
