"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FileSearch,
  Trophy,
  History,
  Settings,
  Target,
  Wand2,
  Files,
  BarChart3,
  ClipboardList,
} from "lucide-react";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/analysis", label: "Resume Analysis", icon: FileSearch },
  { href: "/optimizer", label: "Optimizer", icon: Wand2 },
  { href: "/tracker", label: "App Tracker", icon: ClipboardList },
  { href: "/variants", label: "Resume Variants", icon: Files },
  { href: "/market", label: "Market Analyzer", icon: BarChart3 },
  { href: "/ranking", label: "Candidate Ranking", icon: Trophy },
  { href: "/history", label: "History", icon: History },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 min-h-screen bg-slate-900 text-white flex flex-col">
      <div className="p-6 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600 rounded-lg">
            <Target className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg leading-none">ATS Checker</h1>
            <p className="text-slate-400 text-xs mt-0.5">Personal Resume Tool</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-blue-600 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-700">
        <p className="text-slate-500 text-xs text-center">100% Local · No Cloud · No Cost · v4.0</p>
      </div>
    </aside>
  );
}
