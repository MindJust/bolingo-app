const tg = window.Telegram.WebApp;

// --- CONFIGURATION ---
tg.expand();
tg.setHeaderColor('secondary_bg_color');

// --- ÉLÉMENTS DU DOM ---
const profileBuilder = document.getElementById('profile-builder');
const secretQuestions = document.getElementById('secret-questions');
const allOptionButtons = document.querySelectorAll('.option-btn');

// --- STOCKAGE DES DONNÉES ---
const userChoices = { vibe: null, weekend: null, valeurs: null, plaisir: null };
const secretAnswers = { energie: null, decision: null, conflit: null, ressources: null, focus: null };

// --- LOGIQUE ---

// Gère le clic sur n'importe quel bouton d'option
allOptionButtons.forEach(button => {
    button.addEventListener('click', () => {
        const group = button.dataset.group;
        const value = button.dataset.value;

        // Met à jour le bon objet de stockage
        if (group in userChoices) {
            userChoices[group] = value;
        } else if (group in secretAnswers) {
            secretAnswers[group] = value;
        }

        // Met à jour l'affichage
        document.querySelectorAll(`.option-btn[data-group="${group}"]`).forEach(btn => {
            btn.classList.remove('selected');
        });
        button.classList.add('selected');

        // Vérifie si l'écran actuel est complet
        checkCurrentFormCompletion();
    });
});

function checkCurrentFormCompletion() {
    // Si l'écran 1 est visible
    if (profileBuilder.style.display !== 'none') {
        const isComplete = Object.values(userChoices).every(choice => choice !== null);
        if (isComplete) {
            tg.MainButton.setText('Valider et continuer');
            tg.MainButton.show();
        }
    } 
    // Si l'écran 2 est visible
    else {
        const isComplete = Object.values(secretAnswers).every(answer => answer !== null);
        if (isComplete) {
            tg.MainButton.setText('Terminer mon profil');
            tg.MainButton.show();
        }
    }
}

// Gère le clic sur le bouton principal de Telegram
tg.onEvent('mainButtonClicked', async () => {
    // Si on est sur l'écran 1
    if (profileBuilder.style.display !== 'none') {
        handleProfileBuilderSubmit();
    } 
    // Si on est sur l'écran 2
    else {
        handleSecretQuestionsSubmit();
    }
});

async function handleProfileBuilderSubmit() {
    tg.MainButton.showProgress(true).disable();
    // (Pour l'instant, on ne fait rien avec la réponse, on passe juste à l'écran suivant)
    // Ici, on pourrait appeler l'API /generate-description si on le voulait.

    // On simule une petite attente pour que l'utilisateur comprenne qu'une action a eu lieu
    setTimeout(() => {
        profileBuilder.style.display = 'none';
        secretQuestions.style.display = 'block';
        
        tg.MainButton.hideProgress();
        tg.MainButton.hide(); // On cache le bouton, il réapparaîtra quand le 2ème form sera complet
        
        // On notifie l'utilisateur que sa description arrive
        tg.showPopup({
            title: 'Parfait !',
            message: 'Ta description est en cours de création. Tu la recevras dans un instant. Pendant ce temps, réponds à ces quelques questions secrètes.',
            buttons: [{ type: 'ok' }]
        });
        
    }, 500); // 0.5 seconde
}

function handleSecretQuestionsSubmit() {
    // Étape future : envoyer les `secretAnswers` au backend
    tg.showAlert(`Félicitations ! Ton profil est presque complet. Données secrètes enregistrées (pour le test) : ${secretAnswers.energie}, ${secretAnswers.decision}...`);
    tg.close();
}
