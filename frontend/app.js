// Initialise l'API de la Web App Telegram
const tg = window.Telegram.WebApp;

// Affiche un message dans la console pour confirmer que tout est chargé
console.log("Web App script loaded.");

// Change la couleur de fond de l'en-tête pour correspondre au thème
tg.setHeaderColor('secondary_bg_color');
