const tg = window.Telegram.WebApp;

tg.expand();
tg.setHeaderColor('secondary_bg_color');

const userChoices = { vibe: null, weekend: null, valeurs: null, plaisir: null };
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
    if (Object.values(userChoices).every(choice => choice !== null)) {
        tg.MainButton.setText('Valider mes choix');
        tg.MainButton.show();
    }
}

tg.onEvent('mainButtonClicked', async () => {
    tg.MainButton.showProgress(true).disable();
    try {
        if (!tg.initData) {
            tg.showAlert('Erreur: Impossible de vérifier votre identité.');
            return;
        }

        const response = await fetch('/api/generate-description', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `tma ${tg.initData}`
            },
            body: JSON.stringify(userChoices),
        });

        if (response.ok) {
            const result = await response.json();
            // On affiche le message de confirmation et on ferme
            tg.showAlert(result.message);
            tg.close();
        } else {
            const errorResult = await response.json();
            tg.showAlert(`Une erreur est survenue : ${errorResult.detail || 'Erreur inconnue'}`);
        }
    } catch (error) {
        tg.showAlert(`Erreur de connexion. Veuillez réessayer.`);
    } finally {
        tg.MainButton.hideProgress().enable();
    }
});
