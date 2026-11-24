export default function Stat({ title, value, icon }) {
  return (
    <div className="stat">
      <span className="stat-icon">{icon}</span>
      <span className="muted">{title}</span>
      <strong>{value}</strong>
    </div>
  );
}
