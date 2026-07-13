import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  KeyboardEvent,
  MouseEvent,
  ReactNode,
} from "react";
import { Link, useNavigate, type LinkProps } from "react-router-dom";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-lg border border-border bg-card text-card-foreground shadow-sm", className)}
      {...props}
    />
  );
}

export function Button({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "inline-flex h-9 items-center justify-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export function ButtonLink({ className, ...props }: LinkProps) {
  return (
    <Link
      className={cn(
        "inline-flex h-9 items-center justify-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90",
        className,
      )}
      {...props}
    />
  );
}

export function Badge({ children, className }: Readonly<{ children: ReactNode; className?: string }>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border border-border bg-accent px-2 py-0.5 text-xs font-medium text-accent-foreground",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="relative w-full overflow-x-auto">
      <table className={cn("w-full caption-bottom text-sm", className)} {...props} />
    </div>
  );
}

export function Th({ className, ...props }: HTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        "h-10 whitespace-nowrap px-3 text-left align-middle text-xs font-medium uppercase tracking-wide text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

export function Td({ className, ...props }: HTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("border-t border-border px-3 py-3 align-middle", className)} {...props} />;
}

type ClickableRowProps = HTMLAttributes<HTMLTableRowElement> & {
  to: string;
};

export function ClickableRow({
  to,
  className,
  onClick,
  onKeyDown,
  ...props
}: ClickableRowProps) {
  const navigate = useNavigate();

  function openRow(event: MouseEvent<HTMLTableRowElement>) {
    onClick?.(event);
    if (event.defaultPrevented || isInteractiveTarget(event.target)) return;
    navigate(to);
  }

  function openRowFromKeyboard(event: KeyboardEvent<HTMLTableRowElement>) {
    onKeyDown?.(event);
    if (event.defaultPrevented) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      navigate(to);
    }
  }

  return (
    <tr
      role="link"
      tabIndex={0}
      onClick={openRow}
      onKeyDown={openRowFromKeyboard}
      className={cn(
        "cursor-pointer transition-colors hover:bg-muted/50 focus:bg-muted/50 focus:outline-none",
        className,
      )}
      {...props}
    />
  );
}

function isInteractiveTarget(target: EventTarget | null) {
  return (
    target instanceof Element &&
    Boolean(target.closest("a,button,input,select,textarea,summary,[data-ignore-row-click]"))
  );
}

export function EmptyState({
  title,
  body,
}: Readonly<{
  title: string;
  body: string;
}>) {
  return (
    <div className="grid place-items-center px-6 py-16 text-center">
      <p className="text-sm font-medium">{title}</p>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{body}</p>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: Readonly<{
  title: string;
  description?: string;
  actions?: ReactNode;
}>) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {actions}
    </div>
  );
}
