import { ChevronRight } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

import { navItems } from "@/routes/nav-items";

export function Breadcrumbs() {
  const { pathname } = useLocation();
  const activeItem = navItems.find((item) =>
    item.path === "/" ? pathname === "/" : pathname.startsWith(item.path),
  );

  return (
    <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1.5 text-sm text-muted-foreground">
      <Link to="/" className="shrink-0 hover:text-foreground">
        Workspace
      </Link>
      {activeItem && activeItem.path !== "/" && (
        <>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="truncate text-foreground">{activeItem.label}</span>
        </>
      )}
    </nav>
  );
}
