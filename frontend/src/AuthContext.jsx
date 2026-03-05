import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [token, setToken] = useState(localStorage.getItem('vg_token'));
    const [patientId, setPatientId] = useState(localStorage.getItem('vg_patient_id'));
    const [isAuthenticated, setIsAuthenticated] = useState(!!token);

    useEffect(() => {
        setIsAuthenticated(!!token);
    }, [token]);

    const login = (accessToken, pid) => {
        localStorage.setItem('vg_token', accessToken);
        localStorage.setItem('vg_patient_id', pid);
        setToken(accessToken);
        setPatientId(pid);
    };

    const logout = () => {
        localStorage.removeItem('vg_token');
        localStorage.removeItem('vg_patient_id');
        setToken(null);
        setPatientId(null);
    };

    return (
        <AuthContext.Provider value={{ token, patientId, isAuthenticated, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) throw new Error('useAuth must be used within AuthProvider');
    return context;
}
