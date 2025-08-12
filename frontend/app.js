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

// FONCTION DE SAUVEGARDE
async function saveProgress(step) {
    if (!tg.initData) return;
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

// Logique des boutons et de l'affichage...
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
        fetch('/api/generate-description', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `tma ${tg.initData}` },
            body: JSON.stringify(userChoices),
        });
        await saveProgress('builder_done');

        currentStep = 2;
        profileBuilder.style.display = 'none';
        secretQuestions.style.display = 'block';
        tg.MainButton.setText('Terminer plus tard').hideProgress().enable();
        tg.MainButton.show(); // On le remontre tout de suite
    } else if (currentStep === 2) {
        await saveProgress('completed');
        tg.showAlert('Félicitations ! Ton profil est complet.');
        tg.close();
    }
});

// Le bouton "Terminer plus tard" sauvegarde la progression
closeBtn.addEventListener('click', async (e) => { 
    e.preventDefault(); 
    await saveProgress('onboarding_incomplet');
    tg.close(); 
});

// Quand la webapp se ferme, on sauvegarde aussi
tg.onEvent('viewportChanged', async (event) => {
    if (!event.isStateStable) {
        if(currentStep === 2 && !Object.values(secretAnswers).every(a => a !== null)) {
            await saveProgress('onboarding_incomplet');
        }
    }
});
