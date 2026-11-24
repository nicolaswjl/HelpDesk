import { Clock, MessageSquare, Hourglass, ShieldCheck, Ticket } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api, { getApiError } from '../api';
import { useAuth } from '../auth';
import Stat from '../components/Stat';
import TicketTable from '../components/TicketTable';
import { PRIORITY_OPTIONS } from '../labels';

export default function Dashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [recent, setRecent] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.get('/dashboard/summary'), api.get('/tickets/?size=5')])
      .then(([summaryResponse, ticketsResponse]) => {
        if (cancelled) return;
        setSummary(summaryResponse.data);
        setRecent(ticketsResponse.data.items);
      })
      .catch((err) => !cancelled && setError(getApiError(err, 'Não foi possível carregar o painel.')));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!summary) return <p>Carregando painel...</p>;

  return (
    <>
      <div className="stats">
        <Stat title="Total de chamados" value={summary.total} icon={<Ticket />} />
        <Stat title="Abertos" value={summary.by_status.open} icon={<Clock />} />
        <Stat title="Em andamento" value={summary.by_status.in_progress} icon={<MessageSquare />} />
        <Stat title="Aguardando" value={summary.by_status.waiting} icon={<Hourglass />} />
        <Stat title="Concluídos" value={summary.by_status.completed} icon={<ShieldCheck />} />
      </div>
      <section className="panel">
        <h2>Por prioridade</h2>
        <div className="priority-summary">
          {PRIORITY_OPTIONS.map(([value, label]) => (
            <span className={`tag ${value}`} key={value}>
              {label}: {summary.by_priority[value] ?? 0}
            </span>
          ))}
        </div>
      </section>
      <section className="panel">
        <div className="section-head">
          <div>
            <h2>Chamados recentes</h2>
            <p className="muted">Acompanhe as últimas solicitações</p>
          </div>
          <Link className="text-link" to="/tickets">
            Ver todos
          </Link>
        </div>
        <TicketTable tickets={recent} showPeople={user.role !== 'user'} />
      </section>
    </>
  );
}
