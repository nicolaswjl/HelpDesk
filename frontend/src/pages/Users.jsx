import { useEffect, useState } from 'react';
import api, { getApiError } from '../api';
import { useAuth } from '../auth';

export default function UsersPage() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);

  async function load() {
    const response = await api.get('/users/');
    setUsers(response.data);
  }

  useEffect(() => {
    load().catch((err) => setError(getApiError(err, 'Não foi possível carregar usuários.')));
  }, []);

  async function mutate(userId, request, fallback) {
    setError('');
    setBusyId(userId);
    try {
      await request();
      await load();
    } catch (err) {
      setError(getApiError(err, fallback));
    } finally {
      setBusyId(null);
    }
  }

  const changeRole = (target, role) =>
    mutate(target.id, () => api.patch(`/users/${target.id}/role`, null, { params: { role } }), 'Não foi possível alterar o perfil.');
  const toggleActive = (target) =>
    mutate(
      target.id,
      () => api.patch(`/users/${target.id}/active`, { is_active: !target.is_active }),
      'Não foi possível alterar o status do usuário.',
    );

  return (
    <section className="panel">
      <h2>Usuários</h2>
      <p className="muted">Gerencie permissões e o acesso das contas.</p>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>E-mail</th>
              <th>Perfil</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {users.map((target) => {
              const isSelf = target.id === me.id;
              return (
                <tr key={target.id}>
                  <td>{target.name}</td>
                  <td>{target.email}</td>
                  <td>
                    <select
                      aria-label={`Perfil de ${target.name}`}
                      value={target.role}
                      disabled={isSelf || busyId === target.id}
                      title={isSelf ? 'Você não pode alterar o próprio perfil' : undefined}
                      onChange={(event) => changeRole(target, event.target.value)}
                    >
                      <option value="user">Solicitante</option>
                      <option value="technician">Técnico</option>
                      <option value="admin">Administrador</option>
                    </select>
                  </td>
                  <td>
                    <button
                      className="secondary small-btn"
                      disabled={isSelf || busyId === target.id}
                      title={isSelf ? 'Você não pode desativar a própria conta' : undefined}
                      onClick={() => toggleActive(target)}
                    >
                      {target.is_active ? 'Ativo · Desativar' : 'Inativo · Ativar'}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
