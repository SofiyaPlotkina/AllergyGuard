(function () {
    const apiBase = window.AllergyGuard.config.apiBase;

    async function request(path, options = {}) {
        const response = await fetch(`${apiBase}${path}`, options);
        if (!response.ok) {
            throw new Error('Server-Fehler');
        }
        return response.json();
    }

    async function getUsers() {
        return request('/users');
    }

    async function createUser(name, allergy) {
        return request('/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, allergy }),
        });
    }

    async function updateUser(id, name, allergy) {
        return request(`/users/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, allergy }),
        });
    }

    async function deleteUser(id) {
        return request(`/users/${id}`, { method: 'DELETE' });
    }

    async function setUserSelected(id, selected) {
        return request(`/users/${id}/selection`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ selected }),
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
        getUsers,
        createUser,
        updateUser,
        deleteUser,
        setUserSelected,
        getHistory,
        checkRecipe,
    };
})();