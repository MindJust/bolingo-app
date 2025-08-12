const tg = window.Telegram.WebApp;

// --- CONFIGURATION ---
tg.expand();
tg.setHeaderColor('secondary_bg_color');

// --- ÉLÉMENTS DU DOM ---
const profileBuilder = document.getElementById('profile-builder');
const secretQuestions = document.getElementById('secret-questions');
const allOptionButtons = document.querySelectorAll('.option-btn');

// --- GESTION DE L'ÉTAT ---
let currentStep = 1;

// --- STOCKAGE DES DONNÉES ---
const userChoices = { vibe: null, weekend: null, valeurs: null, plaisir: null };
const secretAnswers = { energie: null, decision: null, conflit: null, ressources: null, focus: null };

// --- LOGIQUE ---

allOptionButtons.forEach(button => {
    button.addEventListener('click', () => {
        const group = button.dataset.group;
        const value = button.dataset.value;

        if (group in userChoices) {
            userChoices[group] = value;
        } else if (group in secretAnswers) {
            secretAnswers[group] = value;
        }

        document.querySelectorAll(`.option-btn[data-group="${group}"]`).forEach(btn => {
            btn.classList.remove('selected');
        });
        button.classList.add('selected');

        checkCurrentFormCompletion();
    });
});

function checkCurrentFormCompletion() {
    let isComplete = false;
    if (currentStep === 1) {
        isComplete = Object.values(userChoices).every(choice => choice !== null);
        if (isComplete) {
            tg.MainButton.setText('Valider et continuer');
            tg.MainButton.show();
        }
    } else if (currentStep === 2) {
        isComplete = Object.values(secretAnswers).every(answer => answer !== null);
        if (isComplete) {
            tg.MainButton.setText('Terminer mon profil');
            tg.MainButton.show();
        }
    }
}

// Gère le clic sur le bouton principal de Telegram
tg.onEvent('mainButtonClicked', async () => {
    if (currentStep === 1) {
        // Affiche l'indicateur de chargement
        tg.MainButton.showProgress(true).disable();

        // **On appelle l'API pour générer la description en arrière-plan**
        try {
            if (!tg.initData) {
                tg.showAlert('Erreur: Impossible de vérifier votre identité.');
                tg.MainButton.hideProgress().enable();
                return;
            }
            // On ne fait rien avec la 'response' ici, on veut juste déclencher l'action
            await fetch('/api/generate-description', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `tma ${tg.initData}`
                },
                body: JSON.stringify(userChoices),
            });
        } catch (error) {
            // En cas d'échec de l'appel, on prévient l'utilisateur
            tg.showAlert('Erreur de connexion. Impossible de générer la description.');
            tg.MainButton.hideProgress().enable();
            return; // On ne continue pas
        }

        // On passe à l'étape 2
        currentStep = 2;
        profileBuilder.style.display = 'none';
        secretQuestions.style.display = 'block';

        // On réinitialise le bouton principal
        tg.MainButton.hide().hideProgress().enable();
        
        tg.showPopup({
            title: 'Parfait !',
            message: 'Ta description est en cours de création et arrivera dans un message. Pendant ce temps, réponds à ces quelques questions secrètes.',
            buttons: [{ type: 'ok' }]
        });

    } else if (currentStep === 2) {
        // Étape future : envoyer les `secretAnswers` au backend
        tg.showAlert(`Félicitations ! Ton profil est presque complet. Données secrètes : ${Object.values(secretAnswers).join(', ')}`);
        tg.close();
    }
});
