import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { getApiError } from '../api';
import { PRIORITY_OPTIONS } from '../labels';

export default function NewTicket() {
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [categoriesError, setCategoriesError] = useState('');
  const [form, setForm] = useState({ title: '', description: '', priority: 'medium', category_id: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function loadCategories(signal) {
    setCategoriesLoading(true);
    setCategoriesError('');
    try {
      const response = await api.get('/categories/', { signal });
      if (!signal?.aborted) setCategories(response.data);
    } catch (err) {
      if (!signal?.aborted) setCategoriesError(getApiError(err, 'Não foi possível carregar as categorias.'));
    } finally {
      if (!signal?.aborted) setCategoriesLoading(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    loadCategories(controller.signal);
    return () => controller.abort();
  }, []);

  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  async function submit(event) {
    event.preventDefault();
    setError('');
    if (!categories.length) {
      setError('Não há categorias disponíveis. Peça ao administrador para cadastrar uma categoria antes de abrir o chamado.');
      return;
    }
    setSubmitting(true);
    try {
      const response = await api.post('/tickets/', { ...form, category_id: Number(form.category_id) });
      navigate(`/tickets/${response.data.id}`);
    } catch (err) {
      setError(getApiError(err, 'Não foi possível criar o chamado. Confira os dados e tente novamente.'));
      setSubmitting(false);
    }
  }

  return (
    <section className="panel form-panel">
      <h2>Abrir chamado</h2>
      <p className="muted">Descreva o problema para a equipe de suporte.</p>
      {categoriesError && (
        <div className="error-block" role="alert">
          <p className="error">{categoriesError}</p>
          <button type="button" className="secondary" onClick={() => loadCategories()} disabled={categoriesLoading}>
            {categoriesLoading ? 'Atualizando...' : 'Tentar carregar categorias novamente'}
          </button>
        </div>
      )}
      <form onSubmit={submit}>
        <label>
          Título
          <input required minLength="4" maxLength="160" value={form.title} onChange={update('title')} />
        </label>
        <label>
          Descrição
          <textarea required minLength="10" maxLength="10000" rows="6" value={form.description} onChange={update('description')} />
        </label>
        <div className="form-row">
          <label>
            Categoria
            <select required value={form.category_id} onChange={update('category_id')} disabled={categoriesLoading || categories.length === 0}>
              <option value="">{categoriesLoading ? 'Carregando categorias...' : 'Selecione'}</option>
              {categories.map((category) => (
                <option value={category.id} key={category.id}>{category.name}</option>
              ))}
            </select>
            {!categoriesLoading && !categoriesError && categories.length === 0 && (
              <small className="muted">Nenhuma categoria cadastrada. Peça ao administrador para adicionar uma.</small>
            )}
          </label>
          <label>
            Prioridade
            <select value={form.priority} onChange={update('priority')}>
              {PRIORITY_OPTIONS.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={submitting || categoriesLoading || categories.length === 0}>
          {submitting ? 'Enviando...' : 'Enviar chamado'}
        </button>
      </form>
    </section>
  );
}
