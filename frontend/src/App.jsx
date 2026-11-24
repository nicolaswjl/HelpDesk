import { useCallback, useEffect, useMemo, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import api, { tokenStore, UNAUTHORIZED_EVENT } from './api';
import { AuthContext } from './auth';
import Shell from './components/Shell';
import Login from './pages/Login';
import Register from './pages/Register';

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    if (!tokenStore.get()) {
      setLoading(false);
      return;
    }
    api
      .get('/auth/me')
      .then((response) => setUser(response.data))
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  // Disparado pelo cliente HTTP quando a API responde 401 com uma sessão ativa.
  useEffect(() => {
    window.addEventListener(UNAUTHORIZED_EVENT, logout);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, logout);
  }, [logout]);

  const value = useMemo(() => ({ user, setUser, logout }), [user, logout]);

  if (loading) return <div className="center">Carregando...</div>;

  return (
    <AuthContext.Provider value={value}>
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
        <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />
        <Route path="/*" element={user ? <Shell /> : <Navigate to="/login" replace />} />
      </Routes>
    </AuthContext.Provider>
  );
}
