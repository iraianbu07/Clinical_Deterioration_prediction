import axios from 'axios';

const API_BASE = '';

const api = axios.create({
    baseURL: API_BASE,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('vg_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Auth API
export const authAPI = {
    login: (patient_id, password) =>
        api.post('/auth/login', { patient_id, password }),
    register: (patient_id, password) =>
        api.post('/auth/register', { patient_id, password }),
};

// Vitals API
export const vitalsAPI = {
    add: (vitals) => api.post('/vitals/add', vitals),
    history: () => api.get('/vitals/history'),
};

// Prediction API
export const predictionAPI = {
    current: () => api.get('/prediction/current'),
};

export default api;
