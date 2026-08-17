(function () {
    function extractPageText() {
        // ═══════════════════════════════════════════════════════════════════
        // PRE-PROCESSING: Öffne ALLE Dropdowns/Details für vollständigen Zugriff!
        // ═══════════════════════════════════════════════════════════════════
        try {
            // <details> Tags (HTML5 Dropdowns) öffnen
            document.querySelectorAll('details').forEach(detail => {
                detail.setAttribute('open', '');
            });
            
            // Aria-Dropdowns
            document.querySelectorAll('[aria-expanded="false"]').forEach(el => {
                el.setAttribute('aria-expanded', 'true');
            });
        } catch (e) {
            console.warn('[AllergyGuard] Dropdown opening failed:', e);
        }
        
        // DEBUG-MARKER (wird im Backend sichtbar sein)
        console.log('[AllergyGuard] NEUE extract.js VERSION v2.0 läuft!');
        
        function normalizeText(value) {
            return (value || '')
                .replace(/\r/g, '\n')
                .replace(/\u00a0/g, ' ')
                .replace(/[ \t]+/g, ' ')
                .replace(/\n{3,}/g, '\n\n')
                .trim();
        }

        function textFromNode(node) {
            return normalizeText(node?.innerText || node?.textContent || '');
        }

        function dedupeLines(text) {
            const seen = new Set();
            const lines = [];

            for (const rawLine of normalizeText(text).split('\n')) {
                const line = rawLine.trim();
                if (!line) {
                    continue;
                }

                const key = line.toLowerCase();
                if (seen.has(key)) {
                    continue;
                }

                seen.add(key);
                lines.push(line);
            }

            return lines.join('\n');
        }

        function finalize(text) {
            const cleaned = dedupeLines(text);
            return cleaned.substring(0, 6000).trim();
        }

        function recipeTypeMatches(typeValue) {
            if (!typeValue) {
                return false;
            }
            if (Array.isArray(typeValue)) {
                return typeValue.some(recipeTypeMatches);
            }
            return String(typeValue).toLowerCase().includes('recipe');
        }

        function gatherRecipeIngredients(entry) {
            if (!entry || typeof entry !== 'object') {
                return [];
            }

            let hits = [];
            if (recipeTypeMatches(entry['@type']) && Array.isArray(entry.recipeIngredient)) {
                hits = hits.concat(entry.recipeIngredient.filter(Boolean).map(value => String(value)));
            }

            if (Array.isArray(entry['@graph'])) {
                for (const graphEntry of entry['@graph']) {
                    hits = hits.concat(gatherRecipeIngredients(graphEntry));
                }
            }

            return hits;
        }

        function fromJsonLd() {
            for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
                try {
                    const json = JSON.parse(script.textContent || 'null');
                    const entries = Array.isArray(json) ? json : [json];
                    const ingredients = [];

                    for (const entry of entries) {
                        ingredients.push(...gatherRecipeIngredients(entry));
                    }

                    const text = finalize(ingredients.join('\n'));
                    if (text.length > 30) {
                        return text;
                    }
                } catch {}
            }

            return '';
        }

        function fromMicrodata() {
            const scopes = document.querySelectorAll('[itemtype*="Recipe"], [itemtype*="recipe"]');
            for (const scope of scopes) {
                const ingredients = scope.querySelectorAll('[itemprop="recipeIngredient"]');
                if (!ingredients.length) {
                    continue;
                }

                const text = finalize(Array.from(ingredients).map(textFromNode).join('\n'));
                if (text.length > 30) {
                    return text;
                }
            }

            return '';
        }

        function fromKnownSelectors() {
            // Für Produktseiten: Sammle MEHRERE Sektionen!
            const produktSelectors = [
                '[class*="allergen"]', '[id*="allergen"]',
                '[class*="allergene"]', '[id*="allergene"]',
                '[class*="inhaltsstoff"]', '[id*="inhaltsstoff"]',
                '[class*="zutat"]', '[id*="zutat"]',
                '[class*="zutaten"]', '[id*="zutaten"]',
                '[class*="warnhinweis"]', '[id*="warnhinweis"]',
                '[class*="produktbeschreibung"]', '[id*="produktbeschreibung"]',
                '[class*="product-description"]', '[id*="product-description"]',
                '[class*="product-details"]', '[id*="product-details"]',
            ];
            
            const chunks = [];
            for (const selector of produktSelectors) {
                const elements = document.querySelectorAll(selector);
                for (const el of elements) {
                    const text = textFromNode(el);
                    if (text.length > 20) {
                        chunks.push(text);
                    }
                }
            }
            
            if (chunks.length > 0) {
                const combined = finalize(chunks.join('\n\n'));
                // GENERISCH: Nur returnen wenn genug Text gefunden wurde
                // Wenig Text (z.B. 219 Zeichen) → überspringen → Fallback extrahiert alles!
                if (combined.length > 800) {
                    return combined;
                }
            }
            
            // Fallback: Rezept-Selektoren (wie vorher)
            const rezeptSelectors = [
                '[class*="ingredient"]', '[id*="ingredient"]',
                '[class*="ingredients"]', '[id*="ingredients"]',
                '[class*="recipe-ingredients"]', '[id*="recipe-ingredients"]',
                '[class*="recipeIngredients"]', '[id*="recipeIngredients"]',
                '[class*="ingredient-list"]', '[id*="ingredient-list"]',
                '[class*="ingredients-list"]', '[id*="ingredients-list"]',
                '[class*="recipe-content"]', '[id*="recipe-content"]',
                '[class*="recipe-body"]', '[id*="recipe-body"]',
                '[class*="recipe-card"]', '[id*="recipe-card"]',
                '[class*="recipe-detail"]', '[id*="recipe-detail"]',
                '[class*="rezept-zutaten"]', '[id*="rezept-zutaten"]',
                '[class*="zutatenliste"]', '[id*="zutatenliste"]',
                '[class*="zutaten-list"]', '[id*="zutaten-list"]',
                '[class*="ingredientSection"]', '[id*="ingredientSection"]',
                '[class*="recipe__ingredients"]', '[id*="recipe__ingredients"]',
                '[class*="ingredients__list"]', '[id*="ingredients__list"]',
                '[class*="recipe__content"]', '[id*="recipe__content"]',
                '[class*="wprm-recipe-ingredient"]', '[class*="tasty-recipes-ingredients"]',
                '[class*="mv-create-ingredients"]', '[class*="easyrecipe-ingredients"]',
                '.ingredients', '.ingredient-list', '.ingredients-list', '.recipe-ingredients',
                '.recipe__ingredients', '.wprm-recipe-ingredients-container',
                '.tasty-recipes-ingredients', '.entry-content ul', '.entry-content ol',
                'section.ingredients', 'div.ingredients', 'ul.ingredients', 'ol.ingredients',
            ];

            for (const selector of rezeptSelectors) {
                const element = document.querySelector(selector);
                const text = finalize(textFromNode(element));
                if (text.length > 30) {
                    return text;
                }
            }

            return '';
        }

        function fromHeadings() {
            const headingSelectors = 'h1, h2, h3, h4, h5, h6, strong, b, summary';
            const headingPattern = /(zutaten|ingredients|ingredient list|rezeptzutaten|allergene|allergen|inhaltsstoffe|warnhinweise|produktbeschreibung)/i;

            for (const heading of document.querySelectorAll(headingSelectors)) {
                const headingText = textFromNode(heading);
                if (!headingPattern.test(headingText)) {
                    continue;
                }

                const chunks = [headingText];
                let sibling = heading.nextElementSibling;
                let guard = 0;

                while (sibling && guard < 6) {
                    const tag = sibling.tagName?.toLowerCase() || '';
                    if (/^h[1-6]$/.test(tag)) {
                        break;
                    }

                    const text = textFromNode(sibling);
                    if (text) {
                        chunks.push(text);
                    }

                    if (tag === 'ul' || tag === 'ol') {
                        break;
                    }

                    sibling = sibling.nextElementSibling;
                    guard += 1;
                }

                const merged = finalize(chunks.join('\n'));
                // Nur returnen wenn genug Text (> 800 Zeichen) gefunden wurde
                if (merged.length > 800) {
                    return merged;
                }
            }

            return '';
        }

        function fromFallbackContent() {
            // Aggressive Strategie: Extrahiere ALLES vom Body für Produktseiten
            // (Die vorherigen Stages haben nichts gefunden)
            const bodyText = textFromNode(document.body);
            
            // Für Produktseiten: Nimm mehr als die normalen 6000 Zeichen
            const maxChars = 10000;
            return finalize(bodyText.substring(0, maxChars));
        }

        const extractionStages = [
            fromJsonLd,
            fromMicrodata,
            fromKnownSelectors,
            fromHeadings,
            fromFallbackContent,
        ];

        for (const stage of extractionStages) {
            const text = stage();
            if (text.length > 30) {
                console.log(`[AllergyGuard] Stage ${stage.name} → ${text.length} Zeichen`);
                return text;
            }
        }

        return '';
    }

    window.AllergyGuard.extract = {
        extractPageText,
    };
})();
