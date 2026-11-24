const ROLES = { admin: 'Administrador', technician: 'Técnico', user: 'Solicitante' };
const STATUSES = { open: 'Aberto', in_progress: 'Em andamento', waiting: 'Aguardando', completed: 'Concluído' };
const PRIORITIES = { low: 'Baixa', medium: 'Média', high: 'Alta', urgent: 'Urgente' };

export const roleName = (role) => ROLES[role] || role;
export const statusName = (status) => STATUSES[status] || status;
export const priorityName = (priority) => PRIORITIES[priority] || priority;

export const STATUS_OPTIONS = Object.entries(STATUSES);
export const PRIORITY_OPTIONS = Object.entries(PRIORITIES);

export const formatDate = (value) => new Date(value).toLocaleDateString('pt-BR');
export const formatDateTime = (value) => new Date(value).toLocaleString('pt-BR');

/** Texto legível para uma linha do histórico do chamado. */
export function describeChange(entry) {
  const { field, old_value: oldValue, new_value: newValue } = entry;
  switch (field) {
    case 'created':
      return 'abriu o chamado';
    case 'comment_added':
      return 'adicionou um comentário';
    case 'status':
      return `alterou o status de ${statusName(oldValue)} para ${statusName(newValue)}`;
    case 'priority':
      return `alterou a prioridade de ${priorityName(oldValue)} para ${priorityName(newValue)}`;
    case 'title':
      return 'editou o título';
    case 'description':
      return 'editou a descrição';
    case 'assignee':
      if (oldValue && newValue) return `reatribuiu o chamado de ${oldValue} para ${newValue}`;
      if (newValue) return `atribuiu o chamado a ${newValue}`;
      return `removeu o responsável (${oldValue})`;
    case 'assignee_id': // registros antigos, anteriores ao histórico com nomes
      return 'alterou o responsável';
    default:
      return `alterou ${field}: ${oldValue ?? '—'} → ${newValue ?? '—'}`;
  }
}
