(function () {
    function extractPageText() {
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
            const selectors = [
                '[class*="ingredient"]', '[id*="ingredient"]',
                '[class*="ingredients"]', '[id*="ingredients"]',
                '[class*="zutat"]', '[id*="zutat"]',
                '[class*="zutaten"]', '[id*="zutaten"]',
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

            for (const selector of selectors) {
                const element = document.querySelector(selector);
                const text = finalize(textFromNode(element));
                if (text.length > 30) {
                    return text;
                }
            }

            return '';
        }

        function fromHeadings() {
            const headingSelectors = 'h1, h2, h3, h4, h5, h6, strong, b';
            const headingPattern = /(zutaten|ingredients|ingredient list|rezeptzutaten)/i;

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
                if (merged.length > 30) {
                    return merged;
                }
            }

            return '';
        }

        function fromFallbackContent() {
            const pieces = [];
            const title = normalizeText(document.title || '');
            if (title) {
                pieces.push(title);
            }

            const listTexts = [];
            for (const list of document.querySelectorAll('ul, ol')) {
                const text = textFromNode(list);
                if (text.length >= 20) {
                    listTexts.push(text);
                }
                if (listTexts.length >= 8) {
                    break;
                }
            }
            pieces.push(listTexts.join('\n\n'));

            const bodyText = textFromNode(document.body).substring(0, 5000);
            if (bodyText) {
                pieces.push(bodyText);
            }

            return finalize(pieces.filter(Boolean).join('\n\n'));
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
                return text;
            }
        }

        return '';
    }

    window.AllergyGuard.extract = {
        extractPageText,
    };
})();