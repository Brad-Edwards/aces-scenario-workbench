import { useEffect, useRef, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { BookOpen, FolderKanban, LogOut, ShieldCheck, UserRound } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { getPrincipal } from "@/api/client";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";

function ShellLink({
  to,
  children,
}: Readonly<{
  to: string;
  children: ReactNode;
}>) {
  return (
    <NavLink
      to={to}
      end={to === "/app/"}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
          isActive
            ? "bg-accent text-accent-foreground"
            : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
        )
      }
    >
      {children}
    </NavLink>
  );
}

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  const location = useLocation();
  const mainRef = useRef<HTMLElement>(null);
  const firstRender = useRef(true);
  const principal = useQuery({ queryKey: ["principal"], queryFn: getPrincipal });

  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    mainRef.current?.focus();
  }, [location.pathname]);

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-foreground"
      >
        Skip to content
      </a>
      <div className="flex min-h-dvh">
        <aside className="hidden w-64 shrink-0 flex-col border-r border-white/10 bg-white/[0.02] px-3 py-5 backdrop-blur-xl md:flex">
          <Link to="/app/" className="flex items-center gap-2 px-2 pb-8 text-sm font-semibold tracking-tight">
            <div className="flex size-7 items-center justify-center rounded-md border border-white/10 bg-white/[0.05]">
              <ShieldCheck className="size-4 text-primary" />
            </div>
            ACES Workbench
          </Link>
          <nav className="flex flex-col gap-6" aria-label="Primary">
            <div className="flex flex-col gap-1">
              <span className="px-2 pb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Workspace
              </span>
              <ShellLink to="/app/">
                <FolderKanban className="size-4" />
                Scenarios
              </ShellLink>
            </div>
            <div className="flex flex-col gap-1">
              <span className="px-2 pb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Account
              </span>
              <a
                href="/accounts/me/"
                className="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground"
              >
                <UserRound className="size-4" />
                Profile
              </a>
              <a
                href="/privacy/"
                className="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground"
              >
                <BookOpen className="size-4" />
                Privacy
              </a>
            </div>
          </nav>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-white/10 bg-background/70 px-4 backdrop-blur-xl md:px-8">
            <Link to="/app/" className="text-sm font-semibold md:hidden">
              ACES Workbench
            </Link>
            <div className="flex-1" />
            <span className="hidden text-sm text-muted-foreground sm:inline">
              {principal.data?.displayName || principal.data?.email || "Signed in"}
            </span>
            <form method="post" action="/accounts/logout/">
              <input type="hidden" name="csrfmiddlewaretoken" value={getCookie("csrftoken")} />
              <Button type="submit" className="gap-1.5 bg-transparent text-foreground hover:bg-accent">
                <LogOut className="size-4" />
                <span className="hidden sm:inline">Sign out</span>
              </Button>
            </form>
          </header>
          <main
            id="main"
            ref={mainRef}
            tabIndex={-1}
            className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 outline-none md:px-8"
          >
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}

function getCookie(name: string) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}
