import type { ButtonHTMLAttributes } from "react";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement>;

export function Button({ className = "", type = "button", ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex min-h-12 items-center justify-center rounded-m bg-brand px-6 font-semibold text-on-brand disabled:opacity-60 ${className}`}
      {...props}
    />
  );
}
