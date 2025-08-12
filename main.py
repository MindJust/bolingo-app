import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware # NOUVEL IMPORT
from contextlib import asynccontextmanager
from pydantic import BaseModel
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import google.generativeai as genai

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Modèles de Données ---
class ProfileChoices(BaseModel):
    vibe: str
    weekend: str
    valeurs: str
    plaisir: str

# --- Logique de l'IA ---
def generate_ai_description(choices: ProfileChoices) -> str:
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("Clé API Google non trouvée.")
            return "Erreur : la configuration de l'IA est manquante."
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "Tu es Bolingo, un assistant de rencontre bienveillant et doué avec les mots. "
            "Ta mission est de rédiger une description de profil courte (2-3 phrases), sincère et positive à partir des choix d'un utilisateur. "
            "Le ton doit être simple, accessible et encourageant. Adresse-toi à la personne qui lira le profil.\n\n"
            "Voici les choix de l'utilisateur :\n"
            f"- Vibe générale : {choices.vibe}\n"
            f"- Temps libre : {choices.weekend}\n"
            f"- Valeurs : {choices.valeurs}\n"
            f"- Petit plaisir : {choices.plaisir}\n\n"
            "Rédige la description. Termine par une petite phrase d'ouverture invitant à la discussion."
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la description par l'IA : {e}")
        return "Je suis une personne intéressante qui cherche à faire de belles rencontres. N'hésitez pas à me contacter."

# --- Logique du Bot ---
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
    
    webapp_url_with_version = f"{base_url}?v=final"
    
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

# --- Gestion du Cycle de Vie ---
@asynccontextmanager
async def lifespan(app: FastAPI):
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

# --- CONFIGURATION DU CORS (LA VERSION QUI DOIT MARCHER) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints API ---
@app.post("/api/webhook")
async def webhook(request: Request):
    bot_app = request.app.state.bot_app
    update = Update.de_json(await request.json(), bot_app.bot)
    await bot_app.process_update(update)
    return Response(status_code=200)

@app.post("/api/generate-description")
async def generate_description_api(choices: ProfileChoices):
    description = generate_ai_description(choices)
    return {"description": description}

# --- Servir le Frontend ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
