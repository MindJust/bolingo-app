const tg = window.Telegram.WebApp;

// --- CONFIGURATION ---
tg.expand();
tg.setHeaderColor('secondary_bg_color');

// --- ÉLÉMENTS DU DOM ---
const profileBuilder = document.getElementById('profile-builder');
const secretQuestions = document.getElementById('secret-questions');
const allOptionButtons = document.querySelectorAll('.option-btn');
const closeBtn = document.getElementById('close-btn');

// --- GESTION DE L'ÉTAT ---
let currentStep = 1;

// --- STOCKAGE DES DONNÉES ---
const userChoices = { vibe: null, weekend: null, valeurs: null, plaisir: null };
const secretAnswers = { energie: null, decision: null, conflit: null, ressources: null, focus: null };

// --- LOGIQUE D'INITIALISATION ---
// Configure le bouton principal dès le début. Il sera notre bouton "Sauvegarder et Fermer".
tg.MainButton.setText('Terminer plus tard');
tg.MainButton.show();

// --- LOGIQUE ---

allOptionButtons.forEach(button => {
    button.addEventListener('click', () => {
        const group = button.dataset.group;
        const value = button.dataset.value;

        if (group in userChoices) userChoices[group] = value;
        else if (group in secretAnswers) secretAnswers[group] = value;

        document.querySelectorAll(`.option-btn[data-group="${group}"]`).forEach(btn => btn.classList.remove('selected'));
        button.classList.add('selected');

        checkCurrentFormCompletion();
    });
});

function checkCurrentFormCompletion() {
    let isComplete = false;
    if (currentStep === 1) {
        isComplete = Object.values(userChoices).every(choice => choice !== null);
        if (isComplete) {
            tg.MainButton.setText('Valider et Continuer');
        }
    } else if (currentStep === 2) {
        isComplete = Object.values(secretAnswers).every(answer => answer !== null);
        if (isComplete) {
            tg.MainButton.setText('Terminer mon Profil');
        }
    }
}

// Gère le clic sur le bouton principal de Telegram
tg.onEvent('mainButtonClicked', async () => {
    // Si le formulaire de l'étape 1 n'est pas complet, le bouton sert juste à fermer.
    if (currentStep === 1 && !Object.values(userChoices).every(c => c !== null)) {
        tg.close();
        return;
    }
    
    // Si le formulaire de l'étape 1 est complet, on passe à l'étape 2.
    if (currentStep === 1) {
        handleProfileBuilderSubmit();
    } 
    // Si on est à l'étape 2, le bouton sauvegarde et ferme.
    else if (currentStep === 2) {
        handleSecretQuestionsSubmit();
    }
});

// Gère le clic sur le lien "Terminer plus tard" en bas de page.
closeBtn.addEventListener('click', (e) => {
    e.preventDefault();
    tg.close();
});


async function handleProfileBuilderSubmit() {
    tg.MainButton.showProgress(true).disable();
    try {
        if (!tg.initData) throw new Error('Identité non vérifiée.');
        
        await fetch('/api/generate-description', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `tma ${tg.initData}` },
            body: JSON.stringify(userChoices),
        });

        currentStep = 2;
        profileBuilder.style.display = 'none';
        secretQuestions.style.display = 'block';

        tg.MainButton.setText('Terminer plus tard'); // Le bouton retrouve sa fonction par défaut
        tg.MainButton.hideProgress().enable();

        tg.showPopup({
            title: 'Parfait !',
            message: 'Ta description arrive par message. Finis ton profil en répondant à ces questions, ou reviens plus tard.',
            buttons: [{ type: 'ok' }]
        });
    } catch (error) {
        tg.showAlert('Une erreur de connexion est survenue.');
        tg.MainButton.hideProgress().enable();
    }
}

function handleSecretQuestionsSubmit() {
    // Étape future : envoyer les `secretAnswers` au backend
    const answersCount = Object.values(secretAnswers).filter(a => a !== null).length;
    tg.showAlert(`Progrès sauvegardé ! Vous avez répondu à ${answersCount} sur 5 questions secrètes.`);
    tg.close();
}
