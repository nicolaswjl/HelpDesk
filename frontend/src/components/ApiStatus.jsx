import { useEffect, useState } from 'react';
import { API_URL, diagnoseApi } from '../api';

/** Aviso exibido nas telas de login/cadastro quando a API não está acessível. */
export default function ApiStatus() {
  const [state, setState] = useState('checking');

  useEffect(() => {
    let cancelled = false;
    diagnoseApi().then((result) => !cancelled && setState(result));
    return () => {
      cancelled = true;
    };
  }, []);

  if (state === 'checking' || state === 'ok') return null;

  return (
    <div className="api-warning" role="alert">
      {state === 'offline' ? (
        <>
          <b>O backend não está respondendo em {API_URL}.</b>
          <p>Em outro terminal, na pasta <code>backend</code>, inicie a API e deixe-a aberta:</p>
          <code className="block">.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000</code>
          <p>Depois abra <a href={`${API_URL}/health`} target="_blank" rel="noreferrer">{API_URL}/health</a>: deve aparecer <code>{'{"status":"ok"}'}</code>. Se a API usa outra porta, ajuste <code>VITE_API_URL</code> em <code>frontend/.env</code> e reinicie o <code>npm run dev</code>.</p>
        </>
      ) : (
        <>
          <b>A API está no ar, mas o navegador bloqueou a chamada (CORS).</b>
          <p>
            Inclua <code>{window.location.origin}</code> em <code>CORS_ORIGINS</code> no arquivo <code>backend/.env</code> e reinicie o
            backend. Exemplo: <code className="block">CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173</code>
          </p>
        </>
      )}
    </div>
  );
}
