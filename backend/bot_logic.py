import os
import logging
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration du logging
logger = logging.getLogger(__name__)

# --- Logique des Commandes du Bot ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler pour la commande /start.
    C'est la première interaction de l'utilisateur avec le bot.
    """
    user = update.effective_user
    logger.info(f"L'utilisateur {user.id} ({user.username}) a démarré le bot.")
    
    # Message de bienvenue
    welcome_text = "Salut ! 👋 Prêt(e) pour Bolingo ? Ici, c'est pour des rencontres sérieuses et dans le respect. On y va ?"
    
    # Bouton pour accepter la charte
    keyboard = [[InlineKeyboardButton("✅ Oui, on y va !", callback_data="accept_charte")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# --- Fonction principale pour initialiser le bot ---

def setup_bot_application():
    """Crée et configure l'instance de l'application Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.critical("ERREUR CRITIQUE: Le token Telegram (TELEGRAM_BOT_TOKEN) n'est pas défini.")
        raise ValueError("Le token Telegram n'est pas défini. L'application ne peut pas démarrer.")
        
    application = Application.builder().token(token).build()

    # Ajout des handlers de commandes
    application.add_handler(CommandHandler("start", start))

    return application
