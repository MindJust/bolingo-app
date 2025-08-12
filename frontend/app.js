// Initialise l'API de la Web App Telegram
const tg = window.Telegram.WebApp;

// --- CONFIGURATION INITIALE DE LA WEB APP ---
tg.expand();
tg.setHeaderColor('secondary_bg_color');

// --- GESTION DU FORMULAIRE ---
const userChoices = {
    vibe: null,
    weekend: null,
    valeurs: null,
    plaisir: null
};

const optionButtons = document.querySelectorAll('.option-btn');

optionButtons.forEach(button => {
    button.addEventListener('click', () => {
        const group = button.dataset.group;
        const value = button.dataset.value;

        userChoices[group] = value;

        document.querySelectorAll(`.option-btn[data-group="${group}"]`).forEach(btn => {
            btn.classList.remove('selected');
        });
        button.classList.add('selected');

        checkFormCompletion();
    });
});

function checkFormCompletion() {
    const isComplete = Object.values(userChoices).every(choice => choice !== null);
    if (isComplete) {
        tg.MainButton.setText('Générer ma description');
        tg.MainButton.show();
    }
}

// --- GESTION DU BOUTON PRINCIPAL TELEGRAM (LA PARTIE MODIFIÉE) ---

// Définit ce qui se passe quand l'utilisateur clique sur le bouton principal
tg.onEvent('mainButtonClicked', async () => {
    // 1. Affiche un indicateur de chargement
    tg.MainButton.showProgress(true);
    tg.MainButton.disable();

    try {
        // 2. Prépare l'envoi des données au backend
        const response = await fetch('/api/generate-description', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userChoices),
        });

        // 3. Gère la réponse du backend
        if (response.ok) {
            const result = await response.json();
            
            // Affiche la description générée
            tg.showAlert(`Voici ta description générée :\n\n${result.description}`);
            
            // Une fois que l'utilisateur a vu la description, on ferme la Web App
            tg.close();
        } else {
            // En cas d'erreur du serveur
            const errorResult = await response.json();
            tg.showAlert(`Une erreur est survenue : ${errorResult.detail || 'Erreur inconnue'}`);
        }

    } catch (error) {
        // En cas d'erreur réseau
        tg.showAlert(`Erreur de connexion. Veuillez réessayer.`);
    } finally {
        // 4. Cache l'indicateur de chargement, quoi qu'il arrive
        tg.MainButton.hideProgress();
        tg.MainButton.enable();
    }
});
