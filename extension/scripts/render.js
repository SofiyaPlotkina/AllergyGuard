(function () {
    // Prüfe ob Alternativen angezeigt werden sollen
    function shouldShowAlternatives() {
        const toggle = document.getElementById('showAlternativesToggle');
        return toggle ? toggle.checked : true; // Default: anzeigen
    }

    function renderFundItem(fund, istSpur) {
        const termClass = istSpur ? 'found-term warn' : 'found-term';
        
        // Alternativen nur anzeigen wenn Toggle aktiviert
        const showAlternatives = shouldShowAlternatives();
        const ersatz = showAlternatives && Array.isArray(fund.ersatz) && fund.ersatz.length
            ? `<div class="ersatz-box">
                   <strong>Alternativen:</strong>
                   ${fund.ersatz.map(eintrag => `• ${eintrag}`).join('<br>')}
               </div>`
            : '';

        return `
            <div class="fund-item">
                <div class="fund-header">
                    <span class="${termClass}">• ${fund.synonym}</span>
                </div>
                <div class="fund-context">${fund.fundstelle}</div>
                ${ersatz}
            </div>
        `;
    }

    function groupByAllergen(funde) {
        const grouped = {};
        for (const fund of funde) {
            const allergen = fund.allergie;
            if (!grouped[allergen]) {
                grouped[allergen] = [];
            }
            grouped[allergen].push(fund);
        }
        return grouped;
    }

    function renderResult(data, container) {
        const urteil = (data.urteil || '').toUpperCase();

        const bannerClass = urteil === 'GEFAHR' ? 'gefahr' : urteil === 'WARNUNG' ? 'warnung' : 'sicher';
        const bannerText = urteil === 'GEFAHR'
            ? 'NICHT SICHER – Allergen gefunden!'
            : urteil === 'WARNUNG'
                ? 'VORSICHT – Spuren möglich'
                : 'SICHER – Kein Allergen gefunden';

        let bodyHTML = `
            <div class="label">Geprüft für:</div>
            <div style="margin-bottom:10px;">${data.nutzer} &nbsp;·&nbsp; Allergie: <strong>${data.allergie_geprueft}</strong></div>
        `;

        const methodeLabel = {
            openfoodfacts: 'OpenFoodFacts',
            ollama: 'KI (Ollama)',
            synonym: 'Textanalyse',
            'openfoodfacts+synonym': 'OpenFoodFacts + Textanalyse',
            'synonym+ki': 'Textanalyse + KI',
            ki: 'KI (Ollama)',
        }[data.methode] || data.methode;
        bodyHTML += `<div style="margin-bottom:10px;">
            <span style="display:inline-block;background:#f0f0f0;color:#555;font-size:11px;padding:3px 8px;border-radius:10px;font-weight:500;">
                ${methodeLabel}
            </span>
        </div>`;

        const funde = data.alle_funde || [];
        if (urteil === 'SICHER') {
            bodyHTML += `<div style="color:#555;font-size:13px;margin-top:4px;">${data.grund}</div>`;
        } else {
            const gefahrFunde = funde.filter(fund => !fund.ist_spur);
            const spurenFunde = funde.filter(fund => fund.ist_spur);

            // Gruppierte Anzeige nach Allergen
            if (gefahrFunde.length) {
                bodyHTML += `<div class="label" style="margin-bottom:8px;">Direkt gefunden:</div>`;
                
                const grouped = groupByAllergen(gefahrFunde);
                for (const [allergen, fundsInGroup] of Object.entries(grouped)) {
                    // Allergen-Header
                    bodyHTML += `<div class="allergen-group">`;
                    bodyHTML += `<div class="allergen-header">[${allergen}]</div>`;
                    
                    // Alle Funde für dieses Allergen
                    for (const fund of fundsInGroup) {
                        bodyHTML += renderFundItem(fund, false);
                    }
                    bodyHTML += `</div>`;
                }
            }
            
            if (spurenFunde.length) {
                bodyHTML += `<div class="label" style="margin-bottom:8px;margin-top:${gefahrFunde.length ? 10 : 0}px;">Spurenhinweise:</div>`;
                
                const grouped = groupByAllergen(spurenFunde);
                for (const [allergen, fundsInGroup] of Object.entries(grouped)) {
                    bodyHTML += `<div class="allergen-group">`;
                    bodyHTML += `<div class="allergen-header warn">[${allergen}]</div>`;
                    
                    for (const fund of fundsInGroup) {
                        bodyHTML += renderFundItem(fund, true);
                    }
                    bodyHTML += `</div>`;
                }
            }
        }

        container.innerHTML = `
            <div class="result-card">
                <div class="result-banner ${bannerClass}">${bannerText}</div>
                <div class="result-body">${bodyHTML}</div>
            </div>
        `;
    }

    window.AllergyGuard.render = {
        renderResult,
    };
})();