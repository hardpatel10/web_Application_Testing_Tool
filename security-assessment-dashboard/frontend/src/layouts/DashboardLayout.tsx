import { NavLink, Outlet } from "react-router-dom";

import { navItems } from "@/routes/nav-items";
import { cn } from "@/utils/cn";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function DashboardLayout() {
  return (
    <div className="relative flex h-screen overflow-hidden bg-background text-foreground">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(59,130,246,0.08),transparent_30%),linear-gradient(180deg,rgba(255,255,255,0.035),transparent_26%)]" />
      <Sidebar />
      <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto px-5 pb-8 pt-4 md:px-8 lg:px-10">
          <div className="mx-auto w-full max-w-7xl">
            <Outlet />
          </div>
        </main>
        <nav className="fixed bottom-4 left-1/2 z-30 flex -translate-x-1/2 gap-1 rounded-2xl border border-border/70 bg-card/90 p-1.5 shadow-[0_24px_80px_-40px_rgba(0,0,0,0.95)] backdrop-blur-xl md:hidden">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              aria-label={item.label}
              className={({ isActive }) =>
                cn(
                  "flex h-11 w-11 items-center justify-center rounded-xl transition-all",
                  isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                )
              }
            >
              <item.icon className="h-5 w-5" />
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
