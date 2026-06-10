import type { LucideIcon } from "lucide-react";
import {
  Briefcase,
  CircleDollarSign,
  LayoutDashboard,
  Percent,
  Settings,
  Shield,
} from "lucide-react";

export type NavLink = {
  href: string;
  label: string;
  icon: LucideIcon;
};

/** 全站左侧/顶部导航（所有前台页面一致） */
export const MAIN_NAV_LINKS: NavLink[] = [
  { href: "/", label: "总览", icon: LayoutDashboard },
  { href: "/funds", label: "我的基金", icon: Briefcase },
  { href: "/compound", label: "复利计算器", icon: Percent },
  { href: "/all-in", label: "ALL IN 收益", icon: CircleDollarSign },
  { href: "/settings", label: "设置", icon: Settings },
  { href: "/admin/funds", label: "管理", icon: Shield },
];

export function isNavLinkActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href.startsWith("/admin")) return pathname.startsWith("/admin");
  return pathname === href || pathname.startsWith(`${href}/`);
}
