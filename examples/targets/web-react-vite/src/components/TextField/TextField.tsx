import { useId, type InputHTMLAttributes } from 'react'
import styles from './TextField.module.css'

export type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string }

export function TextField({ label, id, ...props }: TextFieldProps) {
  const generated = useId()
  const inputId = id ?? generated
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={inputId}>{label}</label>
      <input id={inputId} className={styles.input} {...props} />
    </div>
  )
}
