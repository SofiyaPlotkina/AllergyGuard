document.getElementById('checkButton').addEventListener('click', async () => {
    const resultText = document.getElementById('resultText');
    resultText.innerText = "Lese Webseite & frage KI... (kann kurz dauern) ⏳";

    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
            let selectedText = window.getSelection().toString();
            return selectedText ? selectedText : document.body.innerText;
        }
    }, async (injectionResults) => {
        let extractedText = injectionResults[0].result;
        let shortText = extractedText.substring(0, 2000); // Kürzen als Schutz

        try {
            const response = await fetch('http://127.0.0.1:8080/check-recipe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ingredients: shortText })
            });
            const data = await response.json();
            
            resultText.innerHTML = `<b>Nutzer:</b> ${data.nutzer}<br><b>Allergie:</b> ${data.allergie_geprueft}<hr><b>KI sagt:</b><br> ${data.ki_warnung}`;
        } catch (error) {
            resultText.innerText = "Fehler: Läuft der FastAPI Server auf Port 8080?";
        }
    });
});