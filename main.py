import os
import logging
import hmac
import hashlib
from urllib.parse import unquote
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# --- Configuration & Initialisation ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Logique de la Base de Données (La Mémoire) ---
engine = None
if DATABASE_URL:
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    if not engine: return
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                first_name VARCHAR(255),
                onboarding_step VARCHAR(50) DEFAULT 'registered'
            );
        """))

async def get_db():
    if not AsyncSessionLocal: raise HTTPException(status_code=500, detail="Database not configured")
    async with AsyncSessionLocal() as session:
        yield session

async def get_or_create_user(db: AsyncSession, user_id: int, first_name: str) -> dict:
    result = await db.execute(text("SELECT * FROM users WHERE id = :user_id"), {"user_id": user_id})
    user = result.fetchone()
    if not user:
        await db.execute(
            text("INSERT INTO users (id, first_name, onboarding_step) VALUES (:id, :first_name, :step)"),
            {"id": user_id, "first_name": first_name, "step": "registered"}
        )
        await db.commit()
        logger.info(f"Nouvel utilisateur créé en DB : {user_id}")
        return {"id": user_id, "first_name": first_name, "onboarding_step": "registered"}
    return user._asdict()

async def update_user_step(db: AsyncSession, user_id: int, step: str):
    await db.execute(text("UPDATE users SET onboarding_step = :step WHERE id = :user_id"), {"step": step, "user_id": user_id})
    await db.commit()
    logger.info(f"DB : Progression de {user_id} mise à jour à : {step}")

# --- Modèles de Données & Sécurité ---
class ProfileChoices(BaseModel): vibe: str; weekend: str; valeurs: str; plaisir: str
class UserUpdate(BaseModel): step: str
class UserData(BaseModel): id: int; first_name: str
class AuthData(BaseModel): init_data: str; user: UserData

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
async def generate_and_send_description(user_id: int, choices: ProfileChoices, bot_app: Application, db: AsyncSession):
    # ... (inchangé)
    try:
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key: await bot_app.bot.send_message(chat_id=user_id, text="Erreur : la configuration de l'IA est manquante."); return
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = ( "Tu es Bolingo..." ) # Prompt inchangé
        response = await model.generate_content_async(prompt)
        description = response.text.strip()
        message_text = f"✨ <b>Voici la description...</b>" # Message inchangé
        await bot_app.bot.send_message(chat_id=user_id, text=message_text, parse_mode='HTML')
        await update_user_step(db, user_id, "builder_done")
    except Exception as e:
        logger.error(f"Erreur lors de la génération IA : {e}")
        await bot_app.bot.send_message(chat_id=user_id, text="Oups, une erreur est survenue...")

# --- Logique du Bot (Consciente de l'État) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async for db in get_db():
        user = await get_or_create_user(db, update.effective_user.id, update.effective_user.first_name)
        step = user["onboarding_step"]
        base_url = os.getenv("RENDER_EXTERNAL_URL")
        if not base_url: await update.message.reply_text("Erreur : Service non configuré."); return
        
        if step == "registered" or step == "charte_proposee":
            welcome_text = "Salut ! 👋 Prêt(e) pour Bolingo ? Ici, c'est pour des rencontres sérieuses et dans le respect. On y va ?"
            keyboard = [[InlineKeyboardButton("✅ Oui, on y va !", callback_data="show_charte")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
            await update_user_step(db, user["id"], "charte_proposee")
        elif step == "charte_accepted" or step == "onboarding_incomplet" or step == "builder_done":
            text = "Salut ! Il semble que tu n'aies pas terminé ton profil. Clique ici pour reprendre là où tu t'es arrêté(e)."
            webapp_url = f"{base_url}?v=resume_session_v2"
            keyboard = [[InlineKeyboardButton("📝 Continuer mon profil", web_app=WebAppInfo(url=webapp_url))]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup)
        elif step == "completed":
            await update.message.reply_text("Félicitations, ton profil est complet ! Tu vas bientôt recevoir ton premier Match du Jour.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    async for db in get_db():
        user = await get_or_create_user(db, query.from_user.id, query.from_user.first_name)
        if query.data == 'show_charte':
            await show_charte_handler(query)
        elif query.data == 'accept_charte': 
            await update_user_step(db, user["id"], "charte_accepted")
            await accept_charte_handler(query)

async def show_charte_handler(query):
    charte_text = "Ok. D'abord, lis nos 3 règles..."
    keyboard = [[InlineKeyboardButton("✅ D'accord, j'accepte les règles", callback_data="accept_charte")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=charte_text, reply_markup=reply_markup, parse_mode='HTML')

async def accept_charte_handler(query):
    base_url = os.getenv("RENDER_EXTERNAL_URL")
    webapp_url = f"{base_url}?v=start_onboarding"
    text = "Charte acceptée ! 👍\nClique sur le bouton ci-dessous pour commencer à créer ton profil."
    keyboard = [[InlineKeyboardButton("✨ Créer mon profil", web_app=WebAppInfo(url=webapp_url))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup)

# --- Application FastAPI & Cycle de Vie ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(button_handler))
    await bot_app.initialize()
    webhook_url = os.getenv("RENDER_EXTERNAL_URL")
    if webhook_url:
        await bot_app.bot.set_webhook(url=f"{webhook_url}/api/webhook", allowed_updates=Update.ALL_TYPES)
    app.state.bot_app = bot_app
    logger.info("Service démarré et bot initialisé.")
    yield
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
async def generate_description_api(choices: ProfileChoices, background_tasks: BackgroundTasks, auth: AuthData = Depends(validate_webapp_data)):
    async for db in get_db():
        background_tasks.add_task(generate_and_send_description, auth.user.id, choices, app.state.bot_app, db)
    return {"status": "ok", "message": "Ta description est en cours de création..."}

@app.post("/api/update-profile")
async def update_profile_api(update_data: UserUpdate, auth: AuthData = Depends(validate_webapp_data)):
    async for db in get_db():
        await update_user_step(db, auth.user.id, update_data.step)
    return {"status": "ok"}

# --- Servir le Frontend ---
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
