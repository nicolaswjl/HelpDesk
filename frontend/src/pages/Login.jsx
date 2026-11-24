import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import api, { getApiError, tokenStore } from '../api';
import { useAuth } from '../auth';
import AuthPage from '../components/AuthPage';

export default function Login() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const login = await api.post('/auth/login', { email: email.trim(), password });
      tokenStore.set(login.data.access_token);
      const me = await api.get('/auth/me');
      setUser(me.data);
      navigate('/', { replace: true });
    } catch (err) {
      tokenStore.clear();
      setError(getApiError(err, 'Não foi possível entrar. Confira seu e-mail e senha.'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthPage title="Acesse sua conta" subtitle="Entre para acompanhar seus chamados">
      {location.state?.message && <p className="success" role="status">{location.state.message}</p>}
      <form onSubmit={submit}>
        <label>
          E-mail
          <input
            type="email"
            required
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Senha
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={submitting}>
          {submitting ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
      <p>
        Não tem conta? <Link to="/register">Criar conta</Link>
      </p>
    </AuthPage>
  );
}
