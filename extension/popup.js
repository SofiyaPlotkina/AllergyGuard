const API = 'http://127.0.0.1:8080';

// ── Tab-Navigation ──────────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
        if (tab.dataset.tab === 'verlauf') loadHistory();
        if (tab.dataset.tab === 'profil') { loadProfile(); }
    });
});

// ── Profil-Badge im Header laden ────────────────────────────────────────────
async function loadProfileBadge() {
    try {
        const r = await fetch(`${API}/profile`);
        const d = await r.json();
        document.getElementById('profileBadge').textContent =
            d.name ? `${d.name} · ${d.allergy}` : 'Kein Profil';
    } catch {
        document.getElementById('profileBadge').textContent = 'Offline';
    }
}
loadProfileBadge();

// ── Ergebnis rendern ────────────────────────────────────────────────────────
function renderResult(data, container) {
    const urteil = (data.urteil || '').toUpperCase();

    const bannerClass = urteil === 'GEFAHR' ? 'gefahr' : urteil === 'WARNUNG' ? 'warnung' : 'sicher';
    const bannerIcon  = urteil === 'GEFAHR' ? '🚫' : urteil === 'WARNUNG' ? '⚠️' : '✅';
    const bannerText  = urteil === 'GEFAHR'
        ? 'NICHT SICHER – Allergen gefunden!'
        : urteil === 'WARNUNG'
        ? 'VORSICHT – Spuren möglich'
        : 'SICHER – Kein Allergen gefunden';

    let bodyHTML = `
        <div class="label">Geprüft für:</div>
        <div style="margin-bottom:8px;">${data.nutzer} &nbsp;·&nbsp; Allergie: <strong>${data.allergie_geprueft}</strong></div>
    `;

    const methodeLabel = {
        openfoodfacts: '🗄️ OpenFoodFacts',
        ollama:        '🤖 KI (Ollama)',
        synonym:       '🔤 Textanalyse',
    }[data.methode] || data.methode;
    bodyHTML += `<div style="font-size:11px;color:#999;margin-bottom:8px;">Analysemethode: ${methodeLabel}</div>`;

    const funde = data.alle_funde || [];
    if (urteil === 'SICHER') {
        bodyHTML += `<div style="color:#555;font-size:13px;margin-top:4px;">${data.grund}</div>`;
    } else {
        const gefahrFunde  = funde.filter(f => !f.ist_spur);
        const spurenFunde  = funde.filter(f => f.ist_spur);

        if (gefahrFunde.length) {
            bodyHTML += `<div class="label" style="margin-bottom:4px;">Direkt gefunden:</div>`;
            bodyHTML += gefahrFunde.map(f => `
                <div style="margin-bottom:6px;">
                    <span class="found-term">${f.synonym}</span>
                    <span style="font-size:11px;color:#777;margin-left:4px;">(${f.allergie})</span>
                    <div class="result-context">${f.fundstelle}</div>
                </div>
            `).join('');
        }
        if (spurenFunde.length) {
            bodyHTML += `<div class="label" style="margin-bottom:4px;margin-top:${gefahrFunde.length ? 6 : 0}px;">Spurenhinweise:</div>`;
            bodyHTML += spurenFunde.map(f => `
                <div style="margin-bottom:6px;">
                    <span class="found-term warn">${f.synonym}</span>
                    <span style="font-size:11px;color:#777;margin-left:4px;">(${f.allergie})</span>
                    <div class="result-context">${f.fundstelle}</div>
                </div>
            `).join('');
        }
    }

    container.innerHTML = `
        <div class="result-card">
            <div class="result-banner ${bannerClass}">${bannerIcon} ${bannerText}</div>
            <div class="result-body">${bodyHTML}</div>
        </div>
    `;
}

// ── Website-Text extrahieren (smart: sucht Zutaten-Bereich) ────────────────
function extractPageText() {
    // Strukturierte Rezeptdaten bevorzugen (schema.org)
    const recipeSchema = document.querySelector('[itemtype*="Recipe"]');
    if (recipeSchema) {
        const ingredients = recipeSchema.querySelectorAll('[itemprop="recipeIngredient"]');
        if (ingredients.length > 0) {
            return Array.from(ingredients).map(el => el.innerText).join('\n');
        }
    }

    // JSON-LD nach Rezeptdaten durchsuchen
    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
        try {
            const json = JSON.parse(script.textContent);
            const entries = Array.isArray(json) ? json : [json];
            for (const entry of entries) {
                if (entry['@type'] === 'Recipe' && entry.recipeIngredient) {
                    return entry.recipeIngredient.join('\n');
                }
            }
        } catch {}
    }

    // Zutaten-Block per typischen CSS-Klassen/IDs suchen
    const candidates = [
        '[class*="ingredient"]', '[id*="ingredient"]',
        '[class*="zutat"]',      '[id*="zutat"]',
        '[class*="recipe"]',     '[id*="recipe"]',
        '[class*="rezept"]',     '[id*="rezept"]',
        'ul.ingredients', 'ol.ingredients',
    ];
    for (const sel of candidates) {
        const el = document.querySelector(sel);
        if (el && el.innerText.trim().length > 30) return el.innerText;
    }

    // Fallback: gesamter Body-Text (max 4000 Zeichen)
    return document.body.innerText.substring(0, 4000);
}

// ── Website scannen ─────────────────────────────────────────────────────────
document.getElementById('checkButton').addEventListener('click', async () => {
    const resultBox = document.getElementById('resultBox');
    resultBox.innerHTML = '<p class="loading">🔍 Lese Seite & analysiere...</p>';
    document.getElementById('checkButton').disabled = true;

    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const pageUrl = tab.url || '';

    chrome.scripting.executeScript(
        { target: { tabId: tab.id }, func: extractPageText },
        async (injectionResults) => {
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

// ── Manuellen Text prüfen ───────────────────────────────────────────────────
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

// ── API-Aufruf ──────────────────────────────────────────────────────────────
async function analyzeText(text, source, resultBox) {
    try {
        const response = await fetch(`${API}/check-recipe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ingredients: text, source })
        });
        if (!response.ok) throw new Error('Server-Fehler');
        const data = await response.json();
        renderResult(data, resultBox);
    } catch {
        resultBox.innerHTML = `
            <p style="color:#c0392b;font-size:13px;">
                ❌ Verbindung fehlgeschlagen.<br>
                <span style="color:#888;">Läuft der AllergyGuard-Server auf Port 8080?</span>
            </p>`;
    }
}

// ── Verlauf laden ────────────────────────────────────────────────────────────
async function loadHistory() {
    const list = document.getElementById('historyList');
    list.innerHTML = '<p class="loading">Lade Verlauf...</p>';
    try {
        const r = await fetch(`${API}/history`);
        const items = await r.json();
        if (!items.length) {
            list.innerHTML = '<p class="history-empty">Noch keine Prüfungen gespeichert.</p>';
            return;
        }
        list.innerHTML = '<div class="history-list">' +
            items.map(item => {
                const cls = (item.urteil || '').toLowerCase();
                const icon = cls === 'gefahr' ? '🚫' : cls === 'warnung' ? '⚠️' : '✅';
                const site = item.source || 'Unbekannt';
                const date = new Date(item.timestamp).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
                return `<div class="history-item">
                    <span class="history-dot ${cls}"></span>
                    <div class="history-info">
                        <div class="history-site">${icon} ${site}</div>
                        <div class="history-date">${date} · ${item.allergie_geprueft}</div>
                    </div>
                </div>`;
            }).join('') +
        '</div>';
    } catch {
        list.innerHTML = '<p class="history-empty" style="color:#c0392b;">Server nicht erreichbar.</p>';
    }
}

// ── Allergen-Picker ──────────────────────────────────────────────────────────
const ALLE_ALLERGENE = [
    { key: 'Erdnuss',      emoji: '🥜', sub: 'Peanut, Arachis',          top: true  },
    { key: 'Milch',        emoji: '🥛', sub: 'Laktose, Kasein, Butter',   top: true  },
    { key: 'Ei',           emoji: '🥚', sub: 'Eiklar, Eigelb',            top: true  },
    { key: 'Gluten',       emoji: '🌾', sub: 'Weizen, Dinkel, Roggen',    top: true  },
    { key: 'Soja',         emoji: '🫘', sub: 'Tofu, Sojalecithin',        top: true  },
    { key: 'Nüsse',        emoji: '🌰', sub: 'Mandel, Haselnuss, Cashew', top: true  },
    { key: 'Fisch',        emoji: '🐟', sub: 'Lachs, Thunfisch, Anchovis',top: true  },
    { key: 'Sesam',        emoji: '🌿', sub: 'Tahini, Sesamöl',           top: true  },
    { key: 'Sellerie',     emoji: '🥬', sub: 'Selleriesalz, -öl',         top: false },
    { key: 'Senf',         emoji: '🟡', sub: 'Senfkörner, Senfmehl',      top: false },
    { key: 'Lupine',       emoji: '🌱', sub: 'Lupinenmehl, -protein',     top: false },
    { key: 'Krebstiere',   emoji: '🦐', sub: 'Garnele, Hummer, Krabbe',   top: false },
    { key: 'Weichtiere',   emoji: '🦑', sub: 'Muschel, Tintenfisch',      top: false },
    { key: 'Sulfite',      emoji: '🍷', sub: 'E220–E228, Schwefeldioxid', top: false },
];

function getSelected() {
    return document.getElementById('profileAllergy').value
        .split(',').map(s => s.trim()).filter(Boolean);
}

function setSelected(list) {
    document.getElementById('profileAllergy').value = list.join(', ');
    syncPickerUI();
}

function toggleAllergen(key) {
    const current = getSelected();
    const idx = current.findIndex(s => s.toLowerCase() === key.toLowerCase());
    if (idx >= 0) current.splice(idx, 1);
    else current.push(key);
    setSelected(current);
}

function syncPickerUI() {
    const selected = getSelected().map(s => s.toLowerCase());
    document.querySelectorAll('.top-btn').forEach(btn => {
        btn.classList.toggle('selected', selected.includes(btn.dataset.key.toLowerCase()));
    });
    document.querySelectorAll('#allergenList .allergen-row input[type=checkbox]').forEach(cb => {
        cb.checked = selected.includes(cb.dataset.key.toLowerCase());
    });
}

function buildPicker() {
    // Top-Buttons
    const topWrap = document.getElementById('topAllergens');
    topWrap.innerHTML = '';
    ALLE_ALLERGENE.filter(a => a.top).forEach(a => {
        const btn = document.createElement('button');
        btn.className = 'top-btn';
        btn.dataset.key = a.key;
        btn.textContent = `${a.emoji} ${a.key}`;
        btn.addEventListener('click', () => { toggleAllergen(a.key); });
        topWrap.appendChild(btn);
    });

    // Volle Liste
    const list = document.getElementById('allergenList');
    list.innerHTML = '';
    ALLE_ALLERGENE.forEach(a => {
        const row = document.createElement('div');
        row.className = 'allergen-row';
        row.dataset.name = a.key.toLowerCase();
        row.innerHTML = `
            <input type="checkbox" data-key="${a.key}">
            <span class="a-emoji">${a.emoji}</span>
            <span class="a-name">${a.key}</span>
            <span class="a-sub">${a.sub}</span>
        `;
        row.querySelector('input').addEventListener('change', () => toggleAllergen(a.key));
        row.addEventListener('click', e => {
            if (e.target.tagName !== 'INPUT') toggleAllergen(a.key);
        });
        list.appendChild(row);
    });

    // Suchfeld
    document.getElementById('allergenSearchToggle').addEventListener('click', () => {
        const wrap = document.getElementById('allergenSearchWrap');
        wrap.classList.toggle('open');
        if (wrap.classList.contains('open')) {
            document.getElementById('allergenSearchInput').focus();
        } else {
            document.getElementById('allergenSearchInput').value = '';
            filterAllergenList('');
        }
    });

    document.getElementById('allergenSearchInput').addEventListener('input', e => {
        filterAllergenList(e.target.value.trim().toLowerCase());
    });

    // Freitext-Feld → Picker synchron halten
    document.getElementById('profileAllergy').addEventListener('input', syncPickerUI);

    syncPickerUI();
}

function filterAllergenList(query) {
    document.querySelectorAll('#allergenList .allergen-row').forEach(row => {
        const match = !query || row.dataset.name.includes(query) ||
            row.querySelector('.a-sub').textContent.toLowerCase().includes(query);
        row.classList.toggle('hidden', !match);
    });
}

// ── Profil laden / speichern ─────────────────────────────────────────────────
async function loadProfile() {
    try {
        const r = await fetch(`${API}/profile`);
        const d = await r.json();
        document.getElementById('profileName').value = d.name || '';
        document.getElementById('profileAllergy').value = d.allergy || '';
        syncPickerUI();
    } catch {}
}

// Picker einmalig beim Start aufbauen
buildPicker();

document.getElementById('saveProfileButton').addEventListener('click', async () => {
    const name    = document.getElementById('profileName').value.trim();
    const allergy = document.getElementById('profileAllergy').value.trim();
    const msg     = document.getElementById('saveMsg');
    if (!name || !allergy) {
        msg.style.color = '#c0392b';
        msg.textContent = 'Bitte Name und Allergie eingeben.';
        return;
    }
    try {
        await fetch(`${API}/profile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, allergy })
        });
        msg.style.color = '#2c7a2c';
        msg.textContent = '✅ Gespeichert!';
        loadProfileBadge();
        setTimeout(() => { msg.textContent = ''; }, 2500);
    } catch {
        msg.style.color = '#c0392b';
        msg.textContent = 'Fehler beim Speichern.';
    }
});
