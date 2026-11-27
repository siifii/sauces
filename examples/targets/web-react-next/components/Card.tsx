import type { ReactNode } from "react";

export type CardProps = { title: string; children: ReactNode; action?: ReactNode };

export function Card({ title, children, action }: CardProps) {
  return (
    <section className="flex flex-col gap-3 rounded-m bg-surface-variant p-4">
      <h2 className="text-lg text-text">{title}</h2>
      <div className="ml-2 text-text-variant">{children}</div>
      {action}
    </section>
  );
}
