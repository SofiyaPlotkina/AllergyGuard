(function () {
    const apiBase = window.AllergyGuard.config.apiBase;

    async function request(path, options = {}) {
        const response = await fetch(`${apiBase}${path}`, options);
        if (!response.ok) {
            throw new Error('Server-Fehler');
        }
        return response.json();
    }

    async function getProfile() {
        return request('/profile');
    }

    async function saveProfile(name, allergy) {
        return request('/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, allergy }),
        });
    }

    async function getHistory() {
        return request('/history');
    }

    async function checkRecipe(ingredients, source) {
        return request('/check-recipe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ingredients, source }),
        });
    }

    window.AllergyGuard.api = {
        getProfile,
        saveProfile,
        getHistory,
        checkRecipe,
    };
})();