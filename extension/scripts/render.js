(function () {
    function renderFund(fund, istSpur) {
        const termClass = istSpur ? 'found-term warn' : 'found-term';
        const ersatz = Array.isArray(fund.ersatz) && fund.ersatz.length
            ? `<div class="ersatz-box">
                   <strong>💡 Mögliche Alternativen:</strong>
                   ${fund.ersatz.map(eintrag => `• ${eintrag}`).join('<br>')}
               </div>`
            : '';

        return `
            <div style="margin-bottom:8px;">
                <span class="${termClass}">${fund.synonym}</span>
                <span style="font-size:11px;color:#777;margin-left:4px;">(${fund.allergie})</span>
                <div class="result-context">${fund.fundstelle}</div>
                ${ersatz}
            </div>
        `;
    }

    function renderResult(data, container) {
        const urteil = (data.urteil || '').toUpperCase();

        const bannerClass = urteil === 'GEFAHR' ? 'gefahr' : urteil === 'WARNUNG' ? 'warnung' : 'sicher';
        const bannerIcon = urteil === 'GEFAHR' ? '🚫' : urteil === 'WARNUNG' ? '⚠️' : '✅';
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
            openfoodfacts: '🗄️ OpenFoodFacts',
            ollama: '🤖 KI (Ollama)',
            synonym: '🔤 Textanalyse',
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

            if (gefahrFunde.length) {
                bodyHTML += `<div class="label" style="margin-bottom:4px;">Direkt gefunden:</div>`;
                bodyHTML += gefahrFunde.map(fund => renderFund(fund, false)).join('');
            }
            if (spurenFunde.length) {
                bodyHTML += `<div class="label" style="margin-bottom:4px;margin-top:${gefahrFunde.length ? 6 : 0}px;">Spurenhinweise:</div>`;
                bodyHTML += spurenFunde.map(fund => renderFund(fund, true)).join('');
            }
        }

        container.innerHTML = `
            <div class="result-card">
                <div class="result-banner ${bannerClass}">${bannerIcon} ${bannerText}</div>
                <div class="result-body">${bodyHTML}</div>
            </div>
        `;
    }

    window.AllergyGuard.render = {
        renderResult,
    };
})();