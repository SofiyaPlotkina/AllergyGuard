(function () {
    const ALLE_ALLERGENE = [
        { key: 'Erdnuss', emoji: '🥜', sub: 'Peanut, Arachis', top: true },
        { key: 'Milch', emoji: '🥛', sub: 'Laktose, Kasein, Butter', top: true },
        { key: 'Ei', emoji: '🥚', sub: 'Eiklar, Eigelb', top: true },
        { key: 'Gluten', emoji: '🌾', sub: 'Weizen, Dinkel, Roggen', top: true },
        { key: 'Soja', emoji: '🫘', sub: 'Tofu, Sojalecithin', top: true },
        { key: 'Nüsse', emoji: '🌰', sub: 'Mandel, Haselnuss, Cashew', top: true },
        { key: 'Fisch', emoji: '🐟', sub: 'Lachs, Thunfisch, Anchovis', top: true },
        { key: 'Sesam', emoji: '🌿', sub: 'Tahini, Sesamöl', top: true },
        { key: 'Sellerie', emoji: '🥬', sub: 'Selleriesalz, -öl', top: false },
        { key: 'Senf', emoji: '🟡', sub: 'Senfkörner, Senfmehl', top: false },
        { key: 'Lupine', emoji: '🌱', sub: 'Lupinenmehl, -protein', top: false },
        { key: 'Krebstiere', emoji: '🦐', sub: 'Garnele, Hummer, Krabbe', top: false },
        { key: 'Weichtiere', emoji: '🦑', sub: 'Muschel, Tintenfisch', top: false },
        { key: 'Sulfite', emoji: '🍷', sub: 'E220–E228, Schwefeldioxid', top: false },
    ];

    function getSelected() {
        return document.getElementById('profileAllergy').value
            .split(',').map(value => value.trim()).filter(Boolean);
    }

    function setSelected(list) {
        document.getElementById('profileAllergy').value = list.join(', ');
        syncPickerUI();
    }

    function toggleAllergen(key) {
        const current = getSelected();
        const index = current.findIndex(value => value.toLowerCase() === key.toLowerCase());
        if (index >= 0) {
            current.splice(index, 1);
        } else {
            current.push(key);
        }
        setSelected(current);
    }

    function syncPickerUI() {
        const selected = getSelected().map(value => value.toLowerCase());
        document.querySelectorAll('.top-btn').forEach(button => {
            button.classList.toggle('selected', selected.includes(button.dataset.key.toLowerCase()));
        });
        document.querySelectorAll('#allergenList .allergen-row input[type=checkbox]').forEach(checkbox => {
            checkbox.checked = selected.includes(checkbox.dataset.key.toLowerCase());
        });
    }

    function filterAllergenList(query) {
        document.querySelectorAll('#allergenList .allergen-row').forEach(row => {
            const match = !query || row.dataset.name.includes(query) ||
                row.querySelector('.a-sub').textContent.toLowerCase().includes(query);
            row.classList.toggle('hidden', !match);
        });
    }

    function buildPicker() {
        const topWrap = document.getElementById('topAllergens');
        topWrap.innerHTML = '';
        ALLE_ALLERGENE.filter(allergen => allergen.top).forEach(allergen => {
            const button = document.createElement('button');
            button.className = 'top-btn';
            button.dataset.key = allergen.key;
            button.textContent = `${allergen.emoji} ${allergen.key}`;
            button.addEventListener('click', () => {
                toggleAllergen(allergen.key);
            });
            topWrap.appendChild(button);
        });

        const list = document.getElementById('allergenList');
        list.innerHTML = '';
        ALLE_ALLERGENE.forEach(allergen => {
            const row = document.createElement('div');
            row.className = 'allergen-row';
            row.dataset.name = allergen.key.toLowerCase();
            row.innerHTML = `
                <input type="checkbox" data-key="${allergen.key}">
                <span class="a-emoji">${allergen.emoji}</span>
                <span class="a-name">${allergen.key}</span>
                <span class="a-sub">${allergen.sub}</span>
            `;
            row.querySelector('input').addEventListener('change', () => toggleAllergen(allergen.key));
            row.addEventListener('click', event => {
                if (event.target.tagName !== 'INPUT') {
                    toggleAllergen(allergen.key);
                }
            });
            list.appendChild(row);
        });

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

        document.getElementById('allergenSearchInput').addEventListener('input', event => {
            filterAllergenList(event.target.value.trim().toLowerCase());
        });

        document.getElementById('profileAllergy').addEventListener('input', syncPickerUI);
        syncPickerUI();
    }

    async function loadProfileBadge() {
        try {
            const profile = await window.AllergyGuard.api.getProfile();
            document.getElementById('profileBadge').textContent =
                profile.name ? `${profile.name} · ${profile.allergy}` : 'Kein Profil';
        } catch {
            document.getElementById('profileBadge').textContent = 'Offline';
        }
    }

    async function loadProfileForm() {
        try {
            const profile = await window.AllergyGuard.api.getProfile();
            document.getElementById('profileName').value = profile.name || '';
            document.getElementById('profileAllergy').value = profile.allergy || '';
            syncPickerUI();
        } catch {}
    }

    async function saveProfileForm() {
        const name = document.getElementById('profileName').value.trim();
        const allergy = document.getElementById('profileAllergy').value.trim();
        const msg = document.getElementById('saveMsg');

        if (!name || !allergy) {
            msg.style.color = '#c0392b';
            msg.textContent = 'Bitte Name und Allergie eingeben.';
            return;
        }

        try {
            await window.AllergyGuard.api.saveProfile(name, allergy);
            msg.style.color = '#2c7a2c';
            msg.textContent = '✅ Gespeichert!';
            loadProfileBadge();
            setTimeout(() => {
                msg.textContent = '';
            }, 2500);
        } catch {
            msg.style.color = '#c0392b';
            msg.textContent = 'Fehler beim Speichern.';
        }
    }

    function initProfile() {
        buildPicker();
        loadProfileBadge();
    }

    window.AllergyGuard.profile = {
        initProfile,
        loadProfileForm,
        saveProfileForm,
    };
})();