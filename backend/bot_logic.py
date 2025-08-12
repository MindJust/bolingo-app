import os
import logging
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger(__name__)

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gère la commande /start."""
    welcome_text = "Salut ! 👋 Prêt(e) pour Bolingo ? Ici, c'est pour des rencontres sérieuses et dans le respect. On y va ?"
    keyboard = [[InlineKeyboardButton("✅ Oui, on y va !", callback_data="show_charte")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# --- Callback Query Handler (gestion des clics sur les boutons) ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gère tous les clics sur les boutons inline."""
    query = update.callback_query
    await query.answer()

    if query.data == 'show_charte':
        await show_charte_handler(query)
    elif query.data == 'accept_charte':
        await accept_charte_handler(query)

async def show_charte_handler(query):
    """Affiche la charte et le bouton d'acceptation en utilisant le format HTML."""
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
    """
    Confirme l'acceptation et envoie le bouton pour ouvrir la Web App.
    """
    # On récupère l'URL de notre service depuis les variables d'environnement
    # C'est l'URL de base où notre Web App est servie.
    webapp_url = os.getenv("RENDER_EXTERNAL_URL")
    
    if not webapp_url:
        await query.edit_message_text(text="Erreur : L'adresse du service n'est pas configurée.")
        return

    text = "Charte acceptée ! 👍\nClique sur le bouton ci-dessous pour commencer à créer ton profil."
    
    # On crée un bouton spécial qui ouvre une Web App
    # L'URL doit être celle de notre page index.html
    keyboard = [[InlineKeyboardButton(
        "✨ Créer mon profil", 
        web_app=WebAppInfo(url=webapp_url)
    )]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=text, reply_markup=reply_markup)

# --- Configuration de l'application ---

def setup_bot_application():
    """Crée et configure l'application Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.critical("ERREUR CRITIQUE: TELEGRAM_BOT_TOKEN n'est pas défini.")
        raise ValueError("Le token Telegram n'est pas défini.")
    
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    return application
