const API_URL = 'http://localhost:8000';

export const api = {
    async request(endpoint, options = {}) {
        const token = localStorage.getItem('token');
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers,
        });

        if (response.status === 401) {
            localStorage.removeItem('token');
            window.dispatchEvent(new Event('auth-expired'));
        }

        if (!response.ok) {
            let error = 'An error occurred';
            try {
                const data = await response.json();
                error = data.detail || error;
            } catch (e) {}
            throw new Error(error);
        }

        return response.json();
    },

    get(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'GET' });
    },

    post(endpoint, body, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'POST',
            body: JSON.stringify(body),
        });
    },

    patch(endpoint, body, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'PATCH',
            body: JSON.stringify(body),
        });
    },

    postForm(endpoint, formData, options = {}) {
        // Specifically for OAuth2 application/x-www-form-urlencoded
        const token = localStorage.getItem('token');
        const headers = {
            ...options.headers,
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        return fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            body: formData,
            headers,
        }).then(async (response) => {
            if (!response.ok) {
                let error = 'An error occurred';
                try {
                    const data = await response.json();
                    error = data.detail || error;
                } catch (e) {}
                throw new Error(error);
            }
            return response.json();
        });
    }
};
