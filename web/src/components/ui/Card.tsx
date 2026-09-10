import { forwardRef } from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
  padding?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ hover = false, padding = true, className = "", ...props }, ref) => (
    <div
      ref={ref}
      className={`bg-surface border border-border rounded-2xl shadow-card ${
        padding ? "p-5" : ""
      } ${hover ? "transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover hover:border-ring" : ""} ${className}`}
      {...props}
    />
  )
);
Card.displayName = "Card";
