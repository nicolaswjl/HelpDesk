import { Search } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api, { getApiError } from '../api';
import { useAuth } from '../auth';
import TicketTable from '../components/TicketTable';
import { PRIORITY_OPTIONS, STATUS_OPTIONS } from '../labels';

export default function Tickets() {
  const { user } = useAuth();
  const [data, setData] = useState({ items: [], total: 0, page: 1, pages: 0 });
  const [page, setPage] = useState(1);
  const [draftSearch, setDraftSearch] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [priority, setPriority] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams({ page, size: 10 });
    if (search) params.set('search', search);
    if (status) params.set('status', status);
    if (priority) params.set('priority', priority);
    setError('');
    api
      .get(`/tickets/?${params}`)
      .then((response) => !cancelled && setData(response.data))
      .catch((err) => !cancelled && setError(getApiError(err, 'Não foi possível carregar os chamados. Tente novamente.')));
    return () => {
      cancelled = true;
    };
  }, [page, search, status, priority]);

  function submitSearch(event) {
    event.preventDefault();
    setSearch(draftSearch.trim());
    setPage(1);
  }

  const changeFilter = (setter) => (event) => {
    setter(event.target.value);
    setPage(1);
  };

  return (
    <section className="panel">
      {error && <p className="error" role="alert">{error}</p>}
      <div className="section-head">
        <div>
          <h2>{user.role === 'user' ? 'Meus chamados' : 'Todos os chamados'}</h2>
          <p className="muted">{data.total} solicitações</p>
        </div>
        <Link className="primary small" to="/new">
          Novo chamado
        </Link>
      </div>
      <form className="filters" onSubmit={submitSearch} role="search">
        <div className="search">
          <Search aria-hidden="true" />
          <input
            placeholder="Buscar chamado..."
            aria-label="Buscar chamado"
            maxLength="120"
            value={draftSearch}
            onChange={(event) => setDraftSearch(event.target.value)}
          />
        </div>
        <select aria-label="Filtrar por status" value={status} onChange={changeFilter(setStatus)}>
          <option value="">Todos os status</option>
          {STATUS_OPTIONS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select aria-label="Filtrar por prioridade" value={priority} onChange={changeFilter(setPriority)}>
          <option value="">Todas as prioridades</option>
          {PRIORITY_OPTIONS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <button className="secondary">Buscar</button>
      </form>
      <TicketTable tickets={data.items} showPeople={user.role !== 'user'} />
      <div className="pagination">
        <button className="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
          Anterior
        </button>
        <span>
          Página {data.page} de {Math.max(data.pages, 1)}
        </span>
        <button className="secondary" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>
          Próxima
        </button>
      </div>
    </section>
  );
}
