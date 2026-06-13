import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Activity } from "lucide-react";
import { cn } from "@/core/lib";
import { useAuth } from "@/core/auth";
import { ERole } from "@/types";
import { navGroups } from "./nav-config";

export function Sidebar() {
  const { t } = useTranslation();
  const { isAdmin } = useAuth();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r bg-card/40 md:flex">
      <div className="flex h-14 items-center gap-2 border-b px-5">
        <Activity className="h-5 w-5 text-primary" />
        <span className="font-semibold">{t("common.appName")}</span>
      </div>
      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {navGroups.map((group) => {
          const items = group.items.filter(
            (item) => item.role !== ERole.Admin || isAdmin,
          );
          if (!items.length) return null;
          return (
            <div key={group.labelKey}>
              <p className="px-2 pb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {t(group.labelKey)}
              </p>
              <div className="space-y-1">
                {items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors",
                        isActive
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                      )
                    }
                  >
                    <item.icon className="h-4 w-4" />
                    {t(item.labelKey)}
                  </NavLink>
                ))}
              </div>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
