import type { InputHTMLAttributes } from "react";

export type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & { id: string; label: string };

export function TextField({ id, label, ...props }: TextFieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs text-text-variant">
        {label}
      </label>
      <input
        id={id}
        className="min-h-12 rounded-m border border-outline bg-surface px-4 text-text focus-visible:outline-2 focus-visible:outline-brand"
        {...props}
      />
    </div>
  );
}
