/** Dekorativni barvni siji v ozadju strani (zgolj vizualni, brez interakcije). */
export function AmbientGlow() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div className="absolute -top-40 -left-40 size-[600px] rounded-full bg-secondary/10 blur-[130px]" />
      <div className="absolute top-1/4 -right-40 size-[700px] rounded-full bg-tertiary/10 blur-[150px]" />
      <div className="absolute bottom-10 left-1/3 size-[800px] rounded-full bg-primary/5 blur-[160px]" />
    </div>
  );
}
