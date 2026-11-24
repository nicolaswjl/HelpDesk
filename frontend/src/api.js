import axios from 'axios';

const TOKEN_KEY = 'helpdesk_token';
export const UNAUTHORIZED_EVENT = 'helpdesk:unauthorized';

// localStorage pode lançar exceções (modo privado, armazenamento bloqueado).
export const tokenStore = {
  get() {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(value) {
    try {
      localStorage.setItem(TOKEN_KEY, value);
    } catch {
      /* sem persistência: a sessão vale apenas até recarregar a página */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* nada a fazer */
    }
  },
};

const configuredUrl = import.meta.env.VITE_API_URL?.trim();
const baseURL = (configuredUrl || 'http://127.0.0.1:8000').replace(/\/+$/, '');

const api = axios.create({
  baseURL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Token expirado ou revogado: limpa a sessão e avisa a aplicação para voltar ao login.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginCall = error?.config?.url?.startsWith('/auth/login');
    if (error?.response?.status === 401 && !isLoginCall && tokenStore.get()) {
      tokenStore.clear();
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    return Promise.reject(error);
  },
);

export function getApiError(error, fallback = 'Ocorreu um erro inesperado.') {
  if (error?.code === 'ECONNABORTED') return 'A API demorou para responder. Tente novamente.';
  const detail = error?.response?.data?.detail;
  if (detail) {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      // Erros de validação do FastAPI (422): lista de objetos com "msg".
      return detail.map((item) => String(item?.msg ?? item).replace(/^Value error, /, '')).join(' ');
    }
  }
  if (error?.response) return fallback;
  if (error?.request) {
    return `Não foi possível conectar à API em ${baseURL}. Verifique se o backend está ativo (veja o aviso na tela de login) e se o endereço está correto.`;
  }
  return error?.message || fallback;
}

export const API_URL = baseURL;

/**
 * Diagnostica por que a API não responde.
 * Retorna 'ok', 'offline' (nada escutando no endereço) ou 'cors' (a API respondeu,
 * mas o navegador bloqueou por CORS_ORIGINS não incluir a origem do frontend).
 */
export async function diagnoseApi() {
  try {
    await api.get('/health', { timeout: 4000 });
    return 'ok';
  } catch (err) {
    if (err?.response) return 'ok'; // respondeu com algum status HTTP: a API está no ar
  }
  try {
    // Requisição "opaca": só falha se não houver servidor; ignora CORS.
    await fetch(`${baseURL}/health`, { mode: 'no-cors', signal: AbortSignal.timeout(4000) });
    return 'cors';
  } catch {
    return 'offline';
  }
}

export default api;
