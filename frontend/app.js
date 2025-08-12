// Initialise l'API de la Web App Telegram
const tg = window.Telegram.WebApp;

// --- CONFIGURATION INITIALE DE LA WEB APP ---
tg.expand(); // Étend la Web App à la hauteur maximale
tg.setHeaderColor('secondary_bg_color'); // Change la couleur de l'en-tête

// --- GESTION DU FORMULAIRE ---

// On stocke les choix de l'utilisateur
const userChoices = {
    vibe: null,
    weekend: null,
    valeurs: null,
    plaisir: null
};

// On sélectionne tous les boutons d'option
const optionButtons = document.querySelectorAll('.option-btn');

optionButtons.forEach(button => {
    button.addEventListener('click', () => {
        const group = button.dataset.group;
        const value = button.dataset.value;

        // Stocke le choix
        userChoices[group] = value;

        // Met à jour l'affichage des boutons pour ce groupe
        document.querySelectorAll(`.option-btn[data-group="${group}"]`).forEach(btn => {
            btn.classList.remove('selected');
        });
        button.classList.add('selected');

        // Vérifie si le formulaire est complet pour afficher le bouton principal
        checkFormCompletion();
    });
});

function checkFormCompletion() {
    // Vérifie si toutes les clés dans userChoices ont une valeur
    const isComplete = Object.values(userChoices).every(choice => choice !== null);

    if (isComplete) {
        // Affiche le bouton principal de Telegram
        tg.MainButton.setText('Générer ma description');
        tg.MainButton.show();
    }
}

// --- GESTION DU BOUTON PRINCIPAL TELEGRAM ---

// Définit ce qui se passe quand l'utilisateur clique sur le bouton principal
tg.onEvent('mainButtonClicked', () => {
    // Affiche une alerte pour l'instant.
    // Plus tard, on enverra les données au backend ici.
    const message = `Tes choix :
        - Vibe: ${userChoices.vibe}
        - Weekend: ${userChoices.weekend}
        - Valeurs: ${userChoices.valeurs}
        - Plaisir: ${userChoices.plaisir}`;
    
    tg.showAlert(message);

    // À la fin, on fermera la Web App
    // tg.close(); 
});
