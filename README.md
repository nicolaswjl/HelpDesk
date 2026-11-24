# HelpDesk — Sistema de gerenciamento de chamados

Sistema de suporte de TI com API FastAPI, banco SQLite, interface React/Vite, autenticação JWT, perfis de acesso, chamados, atribuição, comentários, histórico legível, painel, gestão de usuários e testes automatizados.

> Esta versão foi revisada e corrigida a partir do pacote consolidado. Ela é adequada para estudo e execução local. Ainda precisa de validação completa no computador de desenvolvimento antes de ser apresentada como sistema pronto para produção.

## Requisitos
- Python 3.11 ou superior (o projeto também foi verificado sintaticamente com Python 3.13).
- Node.js 20 ou superior e npm.

## 1. Backend (Windows PowerShell)
```powershell
cd backend
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```
Edite `backend/.env` e defina uma `SECRET_KEY` longa e aleatória. Depois:
```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
A API fica em http://localhost:8000 e o Swagger em http://localhost:8000/docs. O banco local é criado automaticamente na primeira inicialização.

## 2. Criar o primeiro administrador
Com o terminal ainda na pasta `backend` e o ambiente virtual ativado:
```powershell
.venv\Scripts\python.exe -m scripts.create_admin
```
O script solicita nome, e-mail e senha duas vezes. Não existe criação pública de administradores. Entre no sistema com essa conta. As categorias iniciais são criadas automaticamente no primeiro início em ambiente de desenvolvimento. Você também pode cadastrar novas categorias pela tela **Categorias** no menu do administrador.
O cadastro público cria apenas usuários com perfil `user`. O administrador pode promover usuários para `technician` e ativar/desativar contas na tela Usuários.

## 3. Frontend
Em outro terminal:
```powershell
cd frontend
npm.cmd install
Copy-Item .env.example .env
npm.cmd run dev
```
Acesse http://localhost:5173. O frontend usa `VITE_API_URL` para localizar a API; o padrão é `http://127.0.0.1:8000`. O servidor Vite fica fixo em `127.0.0.1:5173`; se a porta estiver ocupada, encerre o outro processo que a utiliza em vez de iniciar em outra porta (isso evita erro de CORS).

## 4. Testes
Na pasta `backend`, com o ambiente virtual ativado:
```powershell
.venv\Scripts\python.exe -m pytest -q
```
Os testes cobrem autenticação, limitação de tentativas de login, isolamento dos chamados por usuário, comentários, histórico, atribuição, permissões de técnico, conclusão por administrador, ativação de contas, busca/paginação e não exposição de dados sensíveis.

## Perfis e regras

- **Solicitante:** cria chamados, consulta somente os próprios chamados e pode adicionar comentários enquanto eles não estiverem concluídos.
- **Técnico:** consulta os chamados, assume chamados sem responsável e atualiza o status dos chamados atribuídos a ele. Pode alterar o status para Em andamento, Aguardando e Concluído, finalizando o atendimento após resolver o problema.
- **Administrador (gerente):** possui acesso a todos os chamados, pode atribuir e remover responsáveis, gerenciar perfis e ativar ou desativar contas, cadastrar categorias e concluir chamados. Também possui acesso às funcionalidades administrativas do sistema.

### Fluxo de status dos chamados

1. **Aberto:** chamado recém-criado.
2. **Em andamento:** atendimento iniciado pelo técnico.
3. **Aguardando:** atendimento aguardando informações ou alguma ação.
4. **Concluído:** problema resolvido e atendimento finalizado.

Após a conclusão, o chamado permanece disponível para consulta no histórico.

## Endpoints principais
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `GET /users/`, `PATCH /users/{user_id}/role?role=...`, `PATCH /users/{user_id}/active` (corpo `{"is_active": true|false}`)
- `GET /categories/`, `POST /categories/`
- `GET /tickets/`, `POST /tickets/`, `GET /tickets/{ticket_id}`, `PATCH /tickets/{ticket_id}`
- `PATCH /tickets/{ticket_id}/assign`, `POST /tickets/{ticket_id}/claim`
- `GET /tickets/{ticket_id}/comments`, `POST /tickets/{ticket_id}/comments`
- `GET /tickets/{ticket_id}/history`, `GET /dashboard/summary`
- `GET /health`

## Correções e melhorias da revisão v5
**Segurança**
- `GET /tickets/` não tinha `response_model` e devolvia o objeto `creator` serializado diretamente do banco, **incluindo `password_hash`**. Agora a resposta é validada por `TicketPage`.
- Limitação de tentativas de login (5 falhas por IP + e-mail em 15 min, configurável por `LOGIN_MAX_ATTEMPTS` e `LOGIN_WINDOW_SECONDS`) com resposta `429` e `Retry-After`. É em memória, para um único processo.
- O login de e-mail inexistente agora gasta o mesmo tempo de uma senha errada (evita enumeração de contas por tempo de resposta).
- A busca de chamados escapa `%` e `_` (antes funcionavam como curingas).

**Correções**
- Datas voltavam sem fuso (SQLite) e o navegador as exibia deslocadas (3 h no Brasil). Novo tipo `UTCDateTime` garante UTC (`...Z`) no JSON.
- Telas quebravam (React tentava renderizar objetos) quando a API devolvia erro 422; agora todas usam `getApiError`.
- A mensagem "Conta criada com sucesso" nunca aparecia no login.
- O item ativo do menu nunca era destacado (`Link` → `NavLink`).
- Tag de prioridade "Urgente" aparecia verde (mesma cor de "Concluído"); agora é vermelha.
- `npm run dev` usava `--host 0.0.0.0`, expondo o servidor na rede e contrariando o `vite.config.js`.
- Sessão expirada (401) agora leva ao login em vez de deixar telas com erro.
- Botões "Assumir" e seletor de status não aparecem mais em chamados concluídos para técnicos; formulários têm estado de envio (evita envio duplo).

**Melhorias**
- Administrador pode ativar/desativar contas (`PATCH /users/{id}/active`) com proteção do último administrador.
- Histórico legível ("atribuiu o chamado a Ana") e registrando nomes em vez de IDs na atribuição.
- Filtro por prioridade, colunas Solicitante/Responsável para técnico e admin, cartão "Aguardando" e resumo por prioridade no painel.
- Frontend dividido em arquivos (`pages/`, `components/`) em vez de um único `App.jsx` minificado; dependência `recharts` (não usada) removida.
- `.gitignore` completo, `scripts/__init__.py`, validação de e-mail real em `create_admin`, testes novos e nomes de testes corrigidos.

## Segurança e limitações conhecidas
- O frontend armazena o JWT em `localStorage` por simplicidade didática. Em produção, avalie cookies `HttpOnly`, `Secure`, `SameSite` e proteção CSRF.
- Configure `SECRET_KEY` forte e CORS com os domínios exatos no deploy. O modo `production` rejeita a chave padrão e CORS curinga.
- A limitação de login é em memória (um processo). Atrás de proxy reverso ou com vários processos, use armazenamento compartilhado e o IP real do cliente. Não há recuperação de senha, anexos, notificações, SLA ou trilha de auditoria imutável.
- `Base.metadata.create_all()` serve para iniciar o banco em desenvolvimento, mas não atualiza tabelas existentes. Use Alembic para migrações antes de evoluir o esquema de uma instalação já existente.
- SQLite é adequado para desenvolvimento e demonstração. Para uso concorrente em produção, considere PostgreSQL.
- Execute `pytest` e `npm run build` localmente após instalar as dependências. A revisão v5 foi feita sem acesso à rede para instalá-las (ver `REVISAO_TECNICA.md`). Não declare o projeto validado em produção apenas com os testes automatizados.

## Estrutura
```text
helpdesk_consolidado/
├── backend/
│   ├── app/ (core/config, database, models, schemas, security, main)
│   ├── scripts/create_admin.py
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/ (App.jsx, api.js, auth.js, labels.js, main.jsx, style.css, pages/, components/)
│   ├── package.json
│   └── .env.example
├── documentacao/
└── README.md
```


## Cadastro e categorias iniciais

- O cadastro público em `/register` cria sempre um usuário com perfil `user` (solicitante).
- No primeiro início em ambiente `development`, a API cria automaticamente as categorias Hardware, Software, Rede e internet, Acesso e contas, E-mail e Outros. A criação é idempotente: não duplica categorias já existentes.
- O primeiro administrador continua sendo criado pelo script `.venv\Scripts\python.exe -m scripts.create_admin`.
- O frontend usa `http://127.0.0.1:8000` como endereço padrão da API, alinhado ao comando local do Uvicorn. Se necessário, configure `VITE_API_URL` no arquivo `.env` do frontend.
- A configuração CORS padrão aceita os endereços locais `localhost:5173` e `127.0.0.1:5173`. Se você já possui um arquivo `.env`, confira se `CORS_ORIGINS` contém o endereço usado no navegador.

No Windows PowerShell, execute `npm.cmd install` e `npm.cmd run dev` dentro da pasta `frontend` para evitar o bloqueio de `npm.ps1` pela política de execução.

## Solução de problemas: "Não foi possível conectar à API"
O frontend e o backend são dois programas separados; **os dois terminais precisam ficar abertos**. A tela de login agora diagnostica o motivo e mostra um aviso:
1. **Backend desligado (o mais comum):** na pasta `backend`, rode `.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`. Se o comando falhar, leia o erro no terminal (dependência faltando, `.env` inválido, `SECRET_KEY` curta com `ENVIRONMENT=production`...). Teste abrindo http://127.0.0.1:8000/health, que deve mostrar `{"status":"ok"}`.
2. **CORS:** se `/health` abre no navegador mas o login continua falhando, o `CORS_ORIGINS` do `backend/.env` não contém o endereço usado para abrir o frontend (um `.env` antigo costuma ser o motivo). Compare com o `.env.example`, ajuste e reinicie o backend.
3. **Porta diferente:** se a API roda em outra porta, defina `VITE_API_URL` em `frontend/.env` e reinicie o `npm run dev` (variáveis do Vite só são lidas na inicialização).
