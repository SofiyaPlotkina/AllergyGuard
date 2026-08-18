(function () {
    // Vorerst auf die vier häufigsten/schwersten Allergene begrenzt.
    const ALLE_ALLERGENE = [
        { key: 'Gluten', sub: 'Weizen, Dinkel, Roggen', top: true },
        { key: 'Milch', sub: 'Laktose, Kasein, Butter', top: true },
        { key: 'Erdnuss', sub: 'Peanut, Arachis', top: true },
        { key: 'Ei', sub: 'Eiklar, Eigelb', top: true },
    ];

    // null = Formular legt ein neues Profil an; sonst id des bearbeiteten Profils
    let editingUserId = null;

    function getSelectedAllergens() {
        return document.getElementById('profileAllergy').value
            .split(',').map(value => value.trim()).filter(Boolean);
    }

    function setSelectedAllergens(list) {
        document.getElementById('profileAllergy').value = list.join(', ');
        syncPickerUI();
    }

    function toggleAllergen(key) {
        const current = getSelectedAllergens();
        const index = current.findIndex(value => value.toLowerCase() === key.toLowerCase());
        if (index >= 0) {
            current.splice(index, 1);
        } else {
            current.push(key);
        }
        setSelectedAllergens(current);
    }

    function syncPickerUI() {
        const selected = getSelectedAllergens().map(value => value.toLowerCase());
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
            button.textContent = allergen.key;
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

    function showForm(user) {
        editingUserId = user ? user.id : null;
        document.getElementById('profileFormTitle').textContent = user ? 'Profil bearbeiten' : 'Neues Profil';
        document.getElementById('profileName').value = user ? user.name : '';
        setSelectedAllergens(user ? user.allergy.split(',').map(value => value.trim()).filter(Boolean) : []);
        document.getElementById('saveMsg').textContent = '';
        document.getElementById('profileForm').style.display = 'block';
        document.getElementById('profileName').focus();
    }

    function hideForm() {
        document.getElementById('profileForm').style.display = 'none';
        editingUserId = null;
    }

    function renderUserList(users) {
        const wrap = document.getElementById('userList');
        if (!users.length) {
            wrap.innerHTML = '<p class="history-empty">Noch keine Profile angelegt.</p>';
            return;
        }

        wrap.innerHTML = '';
        users.forEach(user => {
            const row = document.createElement('div');
            row.className = 'user-row';
            row.innerHTML = `
                <input type="checkbox" class="user-select" ${user.selected ? 'checked' : ''} title="Für Prüfung berücksichtigen">
                <div class="user-info">
                    <div class="user-name">${user.name}</div>
                    <div class="user-allergy">${user.allergy}</div>
                </div>
                <button class="user-icon-btn user-edit">Bearbeiten</button>
                <button class="user-icon-btn user-delete">Löschen</button>
            `;
            row.querySelector('.user-select').addEventListener('change', async event => {
                await window.AllergyGuard.api.setUserSelected(user.id, event.target.checked);
                loadProfileBadge();
            });
            row.querySelector('.user-edit').addEventListener('click', () => showForm(user));
            row.querySelector('.user-delete').addEventListener('click', async () => {
                if (!confirm(`Profil "${user.name}" wirklich löschen?`)) return;
                await window.AllergyGuard.api.deleteUser(user.id);
                if (editingUserId === user.id) hideForm();
                await loadUserList();
                loadProfileBadge();
            });
            wrap.appendChild(row);
        });
    }

    async function loadUserList() {
        try {
            const users = await window.AllergyGuard.api.getUsers();
            renderUserList(users);
        } catch {
            document.getElementById('userList').innerHTML =
                '<p class="history-empty" style="color:#c0392b;">Profile konnten nicht geladen werden.</p>';
        }
    }

    async function loadProfileBadge() {
        const badge = document.getElementById('profileBadge');
        try {
            const users = await window.AllergyGuard.api.getUsers();
            const selected = users.filter(user => user.selected);
            if (!selected.length) {
                badge.textContent = 'Kein Profil';
            } else if (selected.length === 1) {
                badge.textContent = `${selected[0].name} · ${selected[0].allergy}`;
            } else {
                badge.textContent = selected.map(user => user.name).join(' + ');
            }
        } catch {
            badge.textContent = 'Offline';
        }
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
            if (editingUserId) {
                await window.AllergyGuard.api.updateUser(editingUserId, name, allergy);
            } else {
                await window.AllergyGuard.api.createUser(name, allergy);
            }
            hideForm();
            await loadUserList();
            loadProfileBadge();
        } catch {
            msg.style.color = '#c0392b';
            msg.textContent = 'Fehler beim Speichern.';
        }
    }

    function initProfile() {
        buildPicker();
        loadProfileBadge();
        document.getElementById('addUserButton').addEventListener('click', () => showForm(null));
        document.getElementById('cancelProfileButton').addEventListener('click', hideForm);
    }

    window.AllergyGuard.profile = {
        initProfile,
        loadProfileForm: loadUserList,
        saveProfileForm,
    };
})();
