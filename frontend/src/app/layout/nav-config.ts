import {
  LayoutDashboard,
  Database,
  LineChart,
  FlaskConical,
  SlidersHorizontal,
  Sigma,
  Briefcase,
  CandlestickChart,
  ShieldAlert,
  BellRing,
  UserCog,
  Settings2,
  type LucideIcon,
} from "lucide-react";
import { ERole } from "@/types";

export type TNavItem = {
  to: string;
  labelKey: string;
  icon: LucideIcon;
  /** 所需角色，缺省为登录用户 */
  role?: ERole;
  end?: boolean;
};

export type TNavGroup = {
  labelKey: string;
  items: TNavItem[];
};

/** 侧边栏导航分组（按模块） */
export const navGroups: TNavGroup[] = [
  {
    labelKey: "nav.overview",
    items: [{ to: "/", labelKey: "nav.dashboard", icon: LayoutDashboard, end: true }],
  },
  {
    labelKey: "nav.research",
    items: [
      { to: "/datasets", labelKey: "nav.datasets", icon: Database },
      { to: "/strategies", labelKey: "nav.strategies", icon: LineChart },
      { to: "/backtests", labelKey: "nav.backtests", icon: FlaskConical },
      { to: "/backtests/compare", labelKey: "nav.backtestCompare", icon: FlaskConical },
      { to: "/optimizations", labelKey: "nav.optimizations", icon: SlidersHorizontal },
      { to: "/factors", labelKey: "nav.factors", icon: Sigma },
    ],
  },
  {
    labelKey: "nav.trading",
    items: [
      { to: "/portfolios", labelKey: "nav.portfolios", icon: Briefcase },
      { to: "/trading", labelKey: "nav.tradingCenter", icon: CandlestickChart },
      { to: "/risk", labelKey: "nav.risk", icon: ShieldAlert },
      { to: "/alerts", labelKey: "nav.alerts", icon: BellRing },
    ],
  },
  {
    labelKey: "nav.system",
    items: [
      { to: "/account", labelKey: "nav.account", icon: Settings2 },
      { to: "/admin", labelKey: "nav.admin", icon: UserCog, role: ERole.Admin },
    ],
  },
];
