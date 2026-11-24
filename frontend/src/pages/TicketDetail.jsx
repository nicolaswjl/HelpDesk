import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api, { getApiError } from '../api';
import { useAuth } from '../auth';
import { describeChange, formatDateTime, priorityName, STATUS_OPTIONS, statusName } from '../labels';

export default function TicketDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [ticket, setTicket] = useState(null);
  const [comments, setComments] = useState([]);
  const [history, setHistory] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (signal) => {
    const requestConfig = signal ? { signal } : undefined;
    const ticketResponse = await api.get(`/tickets/${id}`, requestConfig);
    if (signal?.aborted) return;
    setTicket(ticketResponse.data);
    const [commentsResult, historyResult] = await Promise.allSettled([
      api.get(`/tickets/${id}/comments`, requestConfig),
      api.get(`/tickets/${id}/history`, requestConfig),
    ]);
    if (signal?.aborted) return;
    if (commentsResult.status === 'fulfilled') setComments(commentsResult.value.data);
    if (historyResult.status === 'fulfilled') setHistory(historyResult.value.data);
    if (commentsResult.status === 'rejected' || historyResult.status === 'rejected') {
      setError('Chamado carregado, mas não foi possível carregar os comentários ou o histórico.');
    }
  }, [id]);

  useEffect(() => {
    const controller = new AbortController();
    setTicket(null);
    setComments([]);
    setHistory([]);
    setTechnicians([]);
    setError('');
    load(controller.signal).catch((err) => {
      if (!controller.signal.aborted) setError(getApiError(err, 'Não foi possível carregar o chamado.'));
    });
    if (user.role === 'admin') {
      api
        .get('/users/', { signal: controller.signal })
        .then((response) => {
          if (!controller.signal.aborted) {
            setTechnicians(response.data.filter((u) => u.role === 'technician' && u.is_active));
          }
        })
        .catch(() => {});
    }
    return () => controller.abort();
  }, [load, user.role]);

  // Executa uma ação, recarrega o chamado e mostra a mensagem de erro da API se falhar.
  async function perform(action, fallback) {
    setError('');
    setBusy(true);
    try {
      await action();
      await load();
      return true;
    } catch (err) {
      setError(getApiError(err, fallback));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function submitComment(event) {
    event.preventDefault();
    const ok = await perform(() => api.post(`/tickets/${id}/comments`, { content: text }), 'Não foi possível enviar o comentário.');
    if (ok) setText('');
  }

  const changeStatus = (event) =>
    perform(() => api.patch(`/tickets/${id}`, { status: event.target.value }), 'Não foi possível atualizar o status.');
  const claim = () => perform(() => api.post(`/tickets/${id}/claim`), 'Não foi possível assumir o chamado.');
  const assign = (event) =>
    perform(
      () => api.patch(`/tickets/${id}/assign`, { assignee_id: event.target.value ? Number(event.target.value) : null }),
      'Não foi possível atribuir o chamado.',
    );

  if (!ticket) return error ? <p className="error" role="alert">{error}</p> : <p>Carregando chamado...</p>;

  const isAdmin = user.role === 'admin';
  const isCompleted = ticket.status === 'completed';
  const isAssignedTechnician = user.role === 'technician' && ticket.assignee_id === user.id;
  const canClaim = user.role === 'technician' && !ticket.assignee_id && !isCompleted;
  const canChangeStatus = isAdmin || (isAssignedTechnician && !isCompleted);
  const canComment = !isCompleted || isAdmin;
  const statusOptions = STATUS_OPTIONS.filter(([value]) => isAdmin || (user.role === 'technician' && value === 'completed') || value !== 'completed');

  return (
    <>
      {error && <p className="error" role="alert">{error}</p>}
      <section className="panel">
        <div className="section-head">
          <div>
            <span className="muted">CHAMADO #{ticket.id}</span>
            <h2>{ticket.title}</h2>
          </div>
          <span className={`tag ${ticket.status}`}>{statusName(ticket.status)}</span>
        </div>
        <p className="ticket-description">{ticket.description}</p>
        <div className="meta-grid">
          <div>
            <small>Categoria</small>
            <b>{ticket.category.name}</b>
          </div>
          <div>
            <small>Prioridade</small>
            <b>{priorityName(ticket.priority)}</b>
          </div>
          <div>
            <small>Solicitante</small>
            <b>{ticket.creator.name}</b>
          </div>
          <div>
            <small>Responsável</small>
            <b>{ticket.assignee?.name || 'Não atribuído'}</b>
          </div>
          <div>
            <small>Aberto em</small>
            <b>{formatDateTime(ticket.created_at)}</b>
          </div>
          <div>
            <small>Última atualização</small>
            <b>{formatDateTime(ticket.updated_at)}</b>
          </div>
        </div>
        {canClaim && (
          <button className="primary" onClick={claim} disabled={busy}>
            Assumir chamado
          </button>
        )}
        {isAdmin && !isCompleted && (
          <div className="actions">
            <label>
              Responsável
              <select value={ticket.assignee_id || ''} onChange={assign} disabled={busy}>
                <option value="">Não atribuído</option>
                {technicians.map((technician) => (
                  <option key={technician.id} value={technician.id}>
                    {technician.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
        {canChangeStatus && (
          <div className="actions">
            <label>
              Atualizar status
              <select value={ticket.status} onChange={changeStatus} disabled={busy}>
                {statusOptions.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Comentários</h2>
        <div className="comments">
          {comments.map((comment) => (
            <article key={comment.id}>
              <b>{comment.author.name}</b>
              <small>{formatDateTime(comment.created_at)}</small>
              <p>{comment.content}</p>
            </article>
          ))}
          {!comments.length && <p className="muted">Nenhum comentário ainda.</p>}
        </div>
        {canComment ? (
          <form onSubmit={submitComment}>
            <label>
              Adicionar comentário
              <textarea rows="3" required maxLength="3000" value={text} onChange={(event) => setText(event.target.value)} />
            </label>
            <button className="primary" disabled={busy}>
              Comentar
            </button>
          </form>
        ) : (
          <p className="muted">Este chamado foi concluído e não aceita novos comentários.</p>
        )}
      </section>

      <section className="panel">
        <h2>Histórico</h2>
        {history.map((entry) => (
          <p className="history" key={entry.id}>
            <b>{entry.actor.name}</b> {describeChange(entry)}
            <small>{formatDateTime(entry.changed_at)}</small>
          </p>
        ))}
        {!history.length && <p className="muted">Sem registros.</p>}
      </section>
    </>
  );
}
