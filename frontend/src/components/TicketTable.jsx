import { Link } from 'react-router-dom';
import { formatDate, priorityName, statusName } from '../labels';

export default function TicketTable({ tickets, showPeople = false }) {
  const columns = showPeople ? 6 : 4;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Chamado</th>
            <th>Categoria</th>
            {showPeople && <th>Solicitante</th>}
            {showPeople && <th>Responsável</th>}
            <th>Prioridade</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr key={ticket.id}>
              <td>
                <Link to={`/tickets/${ticket.id}`}>
                  <b>
                    #{ticket.id} · {ticket.title}
                  </b>
                </Link>
                <small>{formatDate(ticket.created_at)}</small>
              </td>
              <td>{ticket.category?.name}</td>
              {showPeople && <td>{ticket.creator?.name}</td>}
              {showPeople && <td>{ticket.assignee?.name || <span className="muted">Não atribuído</span>}</td>}
              <td>
                <span className={`tag ${ticket.priority}`}>{priorityName(ticket.priority)}</span>
              </td>
              <td>
                <span className={`tag ${ticket.status}`}>{statusName(ticket.status)}</span>
              </td>
            </tr>
          ))}
          {!tickets.length && (
            <tr>
              <td colSpan={columns} className="empty">
                Nenhum chamado encontrado.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
