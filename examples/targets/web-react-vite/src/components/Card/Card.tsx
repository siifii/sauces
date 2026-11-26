import type { ReactNode } from 'react'
import styles from './Card.module.css'

export type CardProps = { title: string; children: ReactNode; action?: ReactNode }

export function Card({ title, children, action }: CardProps) {
  return (
    <section className={styles.card}>
      <h2 className={styles.title}>{title}</h2>
      <div className={styles.body}>{children}</div>
      {action}
    </section>
  )
}
