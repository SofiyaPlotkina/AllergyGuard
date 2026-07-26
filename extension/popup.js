async function analyzeText(text, source, resultBox) {
    try {
        const data = await window.AllergyGuard.api.checkRecipe(text, source);
        window.AllergyGuard.render.renderResult(data, resultBox);
    } catch {
        resultBox.innerHTML = `
            <p style="color:#c0392b;font-size:13px;">
                ❌ Verbindung fehlgeschlagen.<br>
                <span style="color:#888;">Läuft der AllergyGuard-Server auf Port 8080?</span>
            </p>`;
    }
}

function setupTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(button => button.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(panel => panel.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('tab-' + tab.dataset.tab).classList.add('active');

            if (tab.dataset.tab === 'verlauf') {
                window.AllergyGuard.history.loadHistory();
            }
            if (tab.dataset.tab === 'profil') {
                window.AllergyGuard.profile.loadProfileForm();
            }
        });
    });
}

function setupScanButton() {
    document.getElementById('checkButton').addEventListener('click', async () => {
        const resultBox = document.getElementById('resultBox');
        resultBox.innerHTML = '<p class="loading">🔍 Lese Seite & analysiere...</p>';
        document.getElementById('checkButton').disabled = true;

        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        const pageUrl = tab.url || '';

        chrome.scripting.executeScript(
            {
                target: { tabId: tab.id },
                func: window.AllergyGuard.extract.extractPageText,
            },
            async injectionResults => {
                document.getElementById('checkButton').disabled = false;
                if (!injectionResults || injectionResults[0].result === undefined) {
                    resultBox.innerHTML = '<p style="color:red;font-size:13px;">Seite konnte nicht gelesen werden.</p>';
                    return;
                }

                const text = injectionResults[0].result;
                await analyzeText(text, pageUrl, resultBox);
            }
        );
    });
}

function setupManualButton() {
    document.getElementById('checkManualButton').addEventListener('click', async () => {
        const text = document.getElementById('manualText').value.trim();
        const resultBox = document.getElementById('resultBoxManual');
        if (!text) {
            resultBox.innerHTML = '<p style="color:#c0392b;font-size:13px;">Bitte erst Text einfügen.</p>';
            return;
        }

        resultBox.innerHTML = '<p class="loading">🔍 Analysiere...</p>';
        await analyzeText(text, 'Manuell eingegeben', resultBox);
    });
}

function setupProfileButton() {
    document.getElementById('saveProfileButton').addEventListener('click', () => {
        window.AllergyGuard.profile.saveProfileForm();
    });
}

function bootstrap() {
    setupTabs();
    setupScanButton();
    setupManualButton();
    setupProfileButton();
    window.AllergyGuard.profile.initProfile();
}

bootstrap();
