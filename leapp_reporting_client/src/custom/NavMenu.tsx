import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuList,
  NavigationMenuTrigger,
} from "@/components/ui/navigation-menu";
import { NavLink } from "react-router-dom";

const dataOptions: { title: string; href: string; description: string }[] = [
  {
    title: "Workflows",
    href: "/data/workflows",
    description:
      "Tabulated workflow data that provides troubleshooting information as well as the current status of LEAPP workflows. Data is refreshed roughly every 20 minutes",
  },
  {
    title: "Hosts",
    href: "/data/hosts",
    description:
      "Tabulated workflow data that provides troubleshooting information as well as the current status of LEAPP workflows. Data is refreshed roughly every 20 minutes",
  },
  {
    title: "Analytics",
    href: "/data/analytics",
    description:
      "Tabulated workflow data that provides troubleshooting information as well as the current status of LEAPP workflows. Data is refreshed roughly every 20 minutes",
  },
];

const NavMenu = () => {
  return (
    <NavigationMenu>
      <NavigationMenuList>
        <NavigationMenuItem>
          <NavigationMenuTrigger className="font-bold text-lg bg-primary text-primary-foreground">
            Data
          </NavigationMenuTrigger>
          <NavigationMenuContent>
            <ul className="grid w-[400px] gap-3 p-4 md:w-[500px] md:grid-cols-2 lg:w-[600px]">
              {dataOptions.map((option) => {
                return (
                  <li>
                    <NavLink
                      to={option.href}
                      className="block select-none space-y-1 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-gray-100 hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground"
                    >
                      <div className="text-sm font-medium leading-none">
                        {option.title}
                      </div>
                      <p className="line-clamp-2 text-sm leading-snug text-muted-foreground">
                        {option.description}
                      </p>
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </NavigationMenuContent>
        </NavigationMenuItem>
      </NavigationMenuList>
    </NavigationMenu>
  );
};

export default NavMenu;
