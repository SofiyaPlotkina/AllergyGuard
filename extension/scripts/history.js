(function () {
    function renderHistoryDetails(snapshot) {
        if (!snapshot || !snapshot.alle_funde) return '';
        
        const funde = snapshot.alle_funde;
        if (!funde.length) return '<div style="padding:8px;color:#666;font-size:12px;">Keine Allergene gefunden</div>';
        
        const gefahrFunde = funde.filter(f => !f.ist_spur);
        const spurenFunde = funde.filter(f => f.ist_spur);
        
        let html = '<div style="padding:8px;font-size:12px;">';
        
        if (gefahrFunde.length) {
            html += '<div style="margin-bottom:6px;"><strong style="color:#c0392b;">⚠️ Direkt gefunden:</strong></div>';
            gefahrFunde.forEach(fund => {
                html += `<div style="margin-left:12px;margin-bottom:4px;">
                    <span style="background:#ffe5e5;padding:2px 4px;border-radius:3px;font-weight:500;">${fund.synonym}</span>
                    <span style="color:#999;font-size:11px;margin-left:4px;">(${fund.allergie})</span>
                </div>`;
                if (fund.fundstelle) {
                    html += `<div style="margin-left:12px;color:#666;font-size:11px;margin-bottom:6px;">"${fund.fundstelle.substring(0, 80)}${fund.fundstelle.length > 80 ? '...' : ''}"</div>`;
                }
            });
        }
        
        if (spurenFunde.length) {
            html += '<div style="margin-bottom:6px;margin-top:8px;"><strong style="color:#e67e22;">ℹ️ Spurenhinweise:</strong></div>';
            spurenFunde.forEach(fund => {
                html += `<div style="margin-left:12px;margin-bottom:4px;">
                    <span style="background:#fff3cd;padding:2px 4px;border-radius:3px;">${fund.synonym}</span>
                    <span style="color:#999;font-size:11px;margin-left:4px;">(${fund.allergie})</span>
                </div>`;
            });
        }
        
        html += '</div>';
        return html;
    }

    async function loadHistory() {
        const list = document.getElementById('historyList');
        list.innerHTML = '<p class="loading">Lade Verlauf...</p>';

        try {
            const items = await window.AllergyGuard.api.getHistory();
            if (!items.length) {
                list.innerHTML = '<p class="history-empty">Noch keine Prüfungen gespeichert.</p>';
                return;
            }

            list.innerHTML = '<div class="history-list">' +
                items.map((item, idx) => {
                    const cls = (item.urteil || '').toLowerCase();
                    const icon = cls === 'gefahr' ? '🚫' : cls === 'warnung' ? '⚠️' : '✅';
                    const site = item.source || 'Unbekannt';
                    const date = new Date(item.timestamp).toLocaleString('de-DE', {
                        dateStyle: 'short',
                        timeStyle: 'short',
                    });

                    const methodeLabel = {
                        openfoodfacts: '🗄️ OpenFoodFacts',
                        ollama: '🤖 KI',
                        synonym: '🔤 Textanalyse',
                    }[item.methode] || item.methode || '';

                    // Parse result_snapshot wenn vorhanden
                    let snapshot = null;
                    if (item.result_snapshot) {
                        try {
                            snapshot = JSON.parse(item.result_snapshot);
                        } catch (e) {
                            console.warn('Could not parse result_snapshot:', e);
                        }
                    }

                    const detailsHTML = snapshot ? renderHistoryDetails(snapshot) : '';
                    const hasDetails = detailsHTML && snapshot.alle_funde && snapshot.alle_funde.length > 0;

                    return `<div class="history-item ${hasDetails ? 'history-item-expandable' : ''}" data-idx="${idx}">
                        <div>
                            <span class="history-dot ${cls}"></span>
                            <div class="history-info">
                                <div class="history-site">${icon} ${site}</div>
                                <div class="history-date">${date} · ${item.allergie_geprueft}${methodeLabel ? ' · ' + methodeLabel : ''}</div>
                                ${hasDetails ? '<div class="history-expand-hint" style="font-size:10px;color:#999;margin-top:2px;">▸ Details anzeigen</div>' : ''}
                            </div>
                        </div>
                        ${hasDetails ? `<div class="history-details" style="display:none;border-top:1px solid #eee;margin-top:6px;">${detailsHTML}</div>` : ''}
                    </div>`;
                }).join('') +
            '</div>';

            // Event-Listener für expandierbare Items
            document.querySelectorAll('.history-item-expandable').forEach(item => {
                item.addEventListener('click', function() {
                    const details = this.querySelector('.history-details');
                    const hint = this.querySelector('.history-expand-hint');
                    if (details) {
                        const isExpanded = details.style.display !== 'none';
                        details.style.display = isExpanded ? 'none' : 'block';
                        if (hint) {
                            hint.textContent = isExpanded ? '▸ Details anzeigen' : '▾ Details verbergen';
                        }
                    }
                });
            });
        } catch {
            list.innerHTML = '<p class="history-empty" style="color:#c0392b;">Server nicht erreichbar.</p>';
        }
    }

    window.AllergyGuard.history = {
        loadHistory,
    };
})();