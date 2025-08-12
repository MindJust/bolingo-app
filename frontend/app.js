const tg = window.Telegram.WebApp;

// --- CONFIGURATION ---
tg.expand();
tg.setHeaderColor('secondary_bg_color');

// --- ÉLÉMENTS DU DOM ---
const profileBuilder = document.getElementById('profile-builder');
const secretQuestions = document.getElementById('secret-questions');
const allOptionButtons = document.querySelectorAll('.option-btn');

// --- GESTION DE L'ÉTAT ---
let currentStep = 1; // 1 = Profile Builder, 2 = Secret Questions

// --- STOCKAGE DES DONNÉES ---
const userChoices = { vibe: null, weekend: null, valeurs: null, plaisir: null };
const secretAnswers = { energie: null, decision: null, conflit: null, ressources: null, focus: null };

// --- LOGIQUE ---

// Gère le clic sur n'importe quel bouton d'option
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
tg.onEvent('mainButtonClicked', () => {
    if (currentStep === 1) {
        // On passe à l'étape 2
        currentStep = 2;
        
        // On effectue la transition visuelle
        profileBuilder.style.display = 'none';
        secretQuestions.style.display = 'block';

        // On réinitialise le bouton principal
        tg.MainButton.hide();

        // On peut toujours appeler l'API de description en arrière-plan ici si on veut.
        // fetch('/api/generate-description', ...);

        tg.showPopup({
            title: 'Parfait !',
            message: 'Réponds maintenant à ces quelques questions secrètes pour affiner ton profil.',
            buttons: [{ type: 'ok' }]
        });
        
    } else if (currentStep === 2) {
        // On termine le processus
        tg.showAlert(`Félicitations ! Ton profil est presque complet. Données secrètes : ${Object.values(secretAnswers).join(', ')}`);
        tg.close();
    }
});
