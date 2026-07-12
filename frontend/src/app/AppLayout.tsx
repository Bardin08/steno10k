import { NavLink, Outlet } from "react-router";
import { Sidebar } from "./Sidebar";
import { ThemeToggle } from "../theme/ThemeToggle";

const topLink = ({ isActive }: { isActive: boolean }) =>
  `font-mono text-[11px] uppercase tracking-[0.14em] ${isActive ? "text-ink" : "text-ink-faint hover:text-ink"}`;

export function AppLayout() {
  return (
    <div className="grid min-h-screen grid-cols-[248px_1fr]">
      <aside className="border-r border-hairline bg-surface">
        <Sidebar />
      </aside>
      <div className="flex flex-col">
        <header className="flex items-center gap-6 border-b border-hairline px-8 py-4">
          <NavLink to="/" className="text-sm font-medium text-ink">
            steno10k
          </NavLink>
          <nav className="flex gap-5">
            <NavLink to="/queue" className={topLink}>
              Queue
            </NavLink>
            <NavLink to="/config" className={topLink}>
              Config
            </NavLink>
          </nav>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </header>
        <main className="mx-auto w-full max-w-[var(--maxw)] px-8 py-12">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
