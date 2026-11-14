// Temporary page body until each page is built (Phase 8).
export default function Placeholder({ title, plan }: { title: string; plan: string[] }) {
  return (
    <section>
      <h1>{title}</h1>
      <div className="card">
        <p className="muted">Planned for Phase 8:</p>
        <ul>
          {plan.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
