const tg = window.Telegram.WebApp;
tg.expand();
tg.setHeaderColor('secondary_bg_color');

const profileBuilder = document.getElementById('profile-builder');
const secretQuestions = document.getElementById('secret-questions');
const allOptionButtons = document.querySelectorAll('.option-btn');
const closeBtn = document.getElementById('close-btn');

let currentStep = 1;
const userChoices = { vibe: null, weekend: null, valeurs: null, plaisir: null };
const secretAnswers = { energie: null, decision: null, conflit: null, ressources: null, focus: null };

// FONCTION POUR SAUVEGARDER LA PROGRESSION
async function saveProgress(step) {
    try {
        await fetch('/api/update-profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `tma ${tg.initData}` },
            body: JSON.stringify({ step: step }),
        });
    } catch (error) {
        console.error("Failed to save progress:", error);
    }
}

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
        isComplete = Object.values(userChoices).every(c => c !== null);
        if (isComplete) { tg.MainButton.setText('Valider et Continuer').show(); }
    } else if (currentStep === 2) {
        isComplete = Object.values(secretAnswers).every(a => a !== null);
        if (isComplete) { tg.MainButton.setText('Terminer mon Profil').show(); }
    }
}

tg.onEvent('mainButtonClicked', async () => {
    if (currentStep === 1) {
        tg.MainButton.showProgress(true).disable();
        // On déclenche la génération de description
        fetch('/api/generate-description', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `tma ${tg.initData}` },
            body: JSON.stringify(userChoices),
        });

        // On passe à l'étape suivante
        currentStep = 2;
        profileBuilder.style.display = 'none';
        secretQuestions.style.display = 'block';
        tg.MainButton.hide().hideProgress().enable();
        tg.showPopup({ title: 'Parfait !', message: 'Ta description arrive par message. Finis ton profil pendant ce temps.', buttons: [{ type: 'ok' }] });
    } else if (currentStep === 2) {
        // L'utilisateur a fini, on sauvegarde et on ferme
        await saveProgress('completed');
        tg.showAlert('Félicitations ! Ton profil est complet.');
        tg.close();
    }
});

closeBtn.addEventListener('click', (e) => { e.preventDefault(); tg.close(); });
