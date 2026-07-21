import { ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";

import { navItems } from "@/routes/nav-items";
import { cn } from "@/utils/cn";

export function Sidebar() {
  return (
    <aside className="relative hidden w-[92px] shrink-0 px-4 py-5 md:flex md:flex-col">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-border/70 bg-card/80 shadow-[0_16px_60px_-34px_rgba(0,0,0,0.9)] backdrop-blur-xl">
        <ShieldCheck className="h-6 w-6 text-primary" />
        <span className="sr-only">Security Dashboard</span>
      </div>

      <nav className="mt-6 flex flex-1 flex-col items-center gap-2 rounded-3xl border border-border/70 bg-card/65 p-2 shadow-[0_24px_80px_-46px_rgba(0,0,0,0.9)] backdrop-blur-xl">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            title={item.label}
            className={({ isActive }) =>
              cn(
                "group relative flex h-12 w-12 items-center justify-center rounded-2xl text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-primary text-primary-foreground shadow-[0_14px_40px_-22px_hsl(var(--primary))]"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )
            }
          >
            <item.icon className="h-5 w-5" />
            <span className="pointer-events-none absolute left-[calc(100%+0.75rem)] z-20 rounded-lg border border-border/80 bg-popover px-2.5 py-1.5 text-xs text-foreground opacity-0 shadow-xl transition-opacity group-hover:opacity-100">
              {item.label}
            </span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
