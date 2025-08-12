import os
import logging
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration du logging
logger = logging.getLogger(__name__)

# Récupération du token depuis les variables d'environnement
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("La variable d'environnement TELEGRAM_BOT_TOKEN n'est pas définie !")
    # Gérer l'erreur comme il se doit, par exemple en arrêtant l'application
    # Pour l'instant, on se contente de logger.

# --- Logique des Commandes du Bot ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler pour la commande /start.
    C'est la première interaction de l'utilisateur avec le bot.
    """
    user = update.effective_user
    logger.info(f"L'utilisateur {user.id} ({user.username}) a démarré le bot.")
    
    # Message de bienvenue
    welcome_text = "Salut ! 👋 Prêt(e) pour KeteKete ? Ici, c'est pour des rencontres sérieuses et dans le respect. On y va ?"
    
    # Bouton pour accepter la charte
    keyboard = [[InlineKeyboardButton("✅ Oui, on y va !", callback_data="accept_charte")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# --- Fonction principale pour initialiser et lancer le bot ---

def setup_bot_application():
    """Crée et configure l'instance de l'application Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("Le token Telegram n'est pas défini. L'application ne peut pas démarrer.")
        
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Ajout des handlers de commandes
    application.add_handler(CommandHandler("start", start))

    return application
