import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api, { getApiError } from '../api';
import AuthPage from '../components/AuthPage';

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await api.post('/auth/register', { ...form, name: form.name.trim(), email: form.email.trim() });
      navigate('/login', {
        state: { message: 'Conta criada com sucesso. Entre com seu e-mail e senha.' },
      });
    } catch (err) {
      setError(getApiError(err, 'Não foi possível concluir o cadastro. Tente novamente.'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthPage title="Criar conta" subtitle="Abra uma solicitação de suporte">
      <form onSubmit={submit}>
        <label>
          Nome
          <input required minLength="2" maxLength="120" autoComplete="name" value={form.name} onChange={update('name')} />
        </label>
        <label>
          E-mail
          <input type="email" required autoComplete="email" value={form.email} onChange={update('email')} />
        </label>
        <label>
          Senha
          <input
            type="password"
            required
            minLength="10"
            maxLength="128"
            autoComplete="new-password"
            value={form.password}
            onChange={update('password')}
          />
          <small className="muted">Mínimo de 10 caracteres.</small>
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={submitting}>
          {submitting ? 'Criando conta...' : 'Criar conta'}
        </button>
      </form>
      <p>
        Já tem conta? <Link to="/login">Entrar</Link>
      </p>
    </AuthPage>
  );
}
