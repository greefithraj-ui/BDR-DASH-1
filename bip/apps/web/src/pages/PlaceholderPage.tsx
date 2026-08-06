type PlaceholderPageProps = {
  title: string;
};

export function PlaceholderPage({ title }: PlaceholderPageProps) {
  return (
    <section className="page-placeholder">
      <div>
        <p className="page-kicker">{title}</p>
        <h1>Coming Soon</h1>
      </div>
    </section>
  );
}
