import { LayoutDashboard, LogOut, Plus, Tags, Ticket, UserCircle, Users } from 'lucide-react';
import { Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { useAuth } from '../auth';
import { roleName } from '../labels';
import CategoriesPage from '../pages/Categories';
import Dashboard from '../pages/Dashboard';
import NewTicket from '../pages/NewTicket';
import TicketDetail from '../pages/TicketDetail';
import Tickets from '../pages/Tickets';
import UsersPage from '../pages/Users';

function Nav({ to, icon, end = false, children }) {
  return (
    <NavLink className="nav-link" to={to} end={end} title={children}>
      {icon}
      {children}
    </NavLink>
  );
}

export default function Shell() {
  const { user, logout } = useAuth();
  const isAdmin = user.role === 'admin';

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">HD</span>
          <b>HelpDesk</b>
        </div>
        <nav aria-label="Navegação principal">
          <Nav to="/" end icon={<LayoutDashboard />}>
            Painel
          </Nav>
          <Nav to="/tickets" icon={<Ticket />}>
            Chamados
          </Nav>
          <Nav to="/new" icon={<Plus />}>
            Novo chamado
          </Nav>
          {isAdmin && (
            <>
              <Nav to="/users" icon={<Users />}>
                Usuários
              </Nav>
              <Nav to="/categories" icon={<Tags />}>
                Categorias
              </Nav>
            </>
          )}
        </nav>
        <div className="side-bottom">
          <div className="user-mini">
            <UserCircle />
            <span>
              <b>{user.name}</b>
              <small>{roleName(user.role)}</small>
            </span>
          </div>
          <button className="logout" onClick={logout}>
            <LogOut size={17} /> Sair
          </button>
        </div>
      </aside>
      <main className="content">
        <header>
          <div>
            <span className="eyebrow">CENTRAL DE SUPORTE</span>
            <h1>Olá, {user.name.split(' ')[0]}</h1>
          </div>
          <span className="role-pill">{roleName(user.role)}</span>
        </header>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tickets" element={<Tickets />} />
          <Route path="/new" element={<NewTicket />} />
          <Route path="/tickets/:id" element={<TicketDetail />} />
          <Route path="/users" element={isAdmin ? <UsersPage /> : <Navigate to="/" replace />} />
          <Route path="/categories" element={isAdmin ? <CategoriesPage /> : <Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
