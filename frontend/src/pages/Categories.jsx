import { useEffect, useState } from 'react';
import api, { getApiError } from '../api';

export default function CategoriesPage() {
  const [categories, setCategories] = useState([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function load() {
    setError('');
    try {
      const response = await api.get('/categories/');
      setCategories(response.data);
    } catch (err) {
      setError(getApiError(err, 'Não foi possível carregar as categorias.'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setSuccess('');
    setSaving(true);
    try {
      await api.post('/categories/', { name: name.trim(), description: description.trim() || null });
      setName('');
      setDescription('');
      setSuccess('Categoria cadastrada com sucesso.');
      await load();
    } catch (err) {
      setError(getApiError(err, 'Não foi possível cadastrar a categoria.'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <section className="panel form-panel">
        <h2>Gerenciar categorias</h2>
        <p className="muted">Cadastre categorias para organizar os chamados enviados pelos solicitantes.</p>
        <form onSubmit={submit}>
          <label>
            Nome da categoria
            <input required minLength="2" maxLength="80" value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            Descrição (opcional)
            <textarea rows="3" maxLength="255" value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          {error && <p className="error" role="alert">{error}</p>}
          {success && <p className="success" role="status">{success}</p>}
          <button className="primary" disabled={saving}>
            {saving ? 'Salvando...' : 'Cadastrar categoria'}
          </button>
        </form>
      </section>
      <section className="panel">
        <div className="section-head">
          <div>
            <h2>Categorias disponíveis</h2>
            <p className="muted">{categories.length} categoria(s)</p>
          </div>
          <button type="button" className="secondary" onClick={load} disabled={loading || saving}>
            Atualizar
          </button>
        </div>
        {loading ? (
          <p>Carregando categorias...</p>
        ) : categories.length === 0 ? (
          <p className="muted">Nenhuma categoria cadastrada.</p>
        ) : (
          <div className="category-list">
            {categories.map((category) => (
              <article className="category-item" key={category.id}>
                <b>{category.name}</b>
                <span className="muted">{category.description || 'Sem descrição'}</span>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
