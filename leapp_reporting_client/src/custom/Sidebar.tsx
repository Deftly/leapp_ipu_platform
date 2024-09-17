import { NavLink, useLocation } from "react-router-dom";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import {
  LayoutDashboardIcon,
  WorkflowIcon,
  ServerIcon,
  ChartCandlestickIcon,
} from "lucide-react";

const links = [
  { name: "Home", href: "/", icon: LayoutDashboardIcon },
  { name: "Workflows", href: "/workflows", icon: WorkflowIcon },
  { name: "Hosts", href: "/hosts", icon: ServerIcon },
  { name: "Analytics", href: "/analytics", icon: ChartCandlestickIcon },
];

const Sidebar = () => {
  const location = useLocation();
  return (
    <aside className="fixed inset-y-0 left-0 z-10 hidden w-14 flex-col border-r bg-white sm:flex ">
      <nav className="flex flex-col items-center gap-4 px-2 sm:py-5">
        <img src="/logo.svg" className="mb-4" />
        <TooltipProvider>
          {links.map((link) => {
            const LinkIcon = link.icon;
            const isActive = location.pathname === link.href;
            return (
              <Tooltip key={link.name}>
                <TooltipTrigger asChild>
                  <NavLink
                    to={link.href}
                    // transition-colors duration-200 ease-in-out
                    className={`group flex h-9 w-9 shrink-0 items-center justify-center gap-2 rounded-full text-lg font-semibold text-primary-foreground md:h-8 md:w-8 md:text-base 
                      ${isActive ? "bg-gray-200 rounded-sm" : "bg-primary"}`}
                  >
                    <LinkIcon />
                    <span className="sr-only">{link.name}</span>
                  </NavLink>
                </TooltipTrigger>
                <TooltipContent side="right">{link.name}</TooltipContent>
              </Tooltip>
            );
          })}
        </TooltipProvider>
      </nav>
    </aside>
  );
};

export default Sidebar;
