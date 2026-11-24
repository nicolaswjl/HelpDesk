import ApiStatus from './ApiStatus';

export default function AuthPage({ title, subtitle, children }) {
  return (
    <main className="auth">
      <div className="auth-card">
        <div className="brand-mark">HD</div>
        <h1>{title}</h1>
        <p className="muted">{subtitle}</p>
        <ApiStatus />
        {children}
      </div>
    </main>
  );
}
