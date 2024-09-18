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
      "View and filter LEAPP-related workflow data. Apply filters such as hostname, region, date, workflow type, failure stage, and error to analyze specific subsets of data.",
  },
  {
    title: "Hosts",
    href: "/data/hosts",
    description:
      "Access detailed information about individual hosts, including upgrade attempt history, current RHEL version, and pre-upgrade preparation status for LEAPP upgrades.",
  },
  {
    title: "Analytics",
    href: "/data/analytics",
    description:
      "Explore visual representations of LEAPP automation workflow success and failure rates. Analyze trends over time to identify areas for improvement in the automation process.",
  },
];

const docOptions: { title: string; href: string; description: string }[] = [
  {
    title: "Known Issues",
    href: "/docs/knownIssues",
    description:
      "Access information on known issues during LEAPP upgrades, including associated behaviors and resolution steps.",
  },
  {
    title: "Release Information",
    href: "/docs/releaseInfo",
    description:
      "Stay updated on the latest LEAPP automation releases, including bug fixes, new features, configuration changes, and other developments.",
  },
  {
    title: "End User Agreement",
    href: "/docs/endUserAgreement",
    description:
      "Find guidance on where to seek support for LEAPP-related issues and understand the terms of use for the LEAPP automation tool.",
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
            <div className="flex w-[800px]">
              <ul className="grid w-[600px] gap-3 p-4 md:grid-cols-2">
                {dataOptions.map((option) => (
                  <li key={option.href}>
                    <NavLink
                      to={option.href}
                      className="block select-none space-y-1 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-gray-100 hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground"
                    >
                      <div className="text-sm font-semibold leading-none text-gray-900">
                        {option.title}
                      </div>
                      {/* <p className="line-clamp-2 text-sm leading-snug text-gray-500"> */}
                      <p className="text-sm leading-snug text-gray-500">
                        {option.description}
                      </p>
                    </NavLink>
                  </li>
                ))}
              </ul>
              <div className="w-[200px] p-4 bg-gray-100 text-gray-600">
                <div>
                  <h3 className="text-sm font-semibold mb-2">
                    General Information
                  </h3>
                  <p className="text-xs">
                    These data pages provide comprehensive insights into LEAPP
                    workflows, host statuses, and overall performance analytics.
                    Use these tools to monitor, analyze, and improve the LEAPP
                    upgrade process across your infrastructure.
                  </p>
                </div>
                <div className="mt-auto pt-8">
                  <p className="text-xs text-gray-500 italic">
                    Note: Data is refreshed roughly every 20 minutes.
                  </p>
                </div>
              </div>
            </div>
          </NavigationMenuContent>
        </NavigationMenuItem>
        <NavigationMenuItem>
          <NavigationMenuTrigger className="font-bold text-lg bg-primary text-primary-foreground">
            Docs
          </NavigationMenuTrigger>
          <NavigationMenuContent>
            <div className="flex w-[600px]">
              <ul className="grid w-[600px] gap-3 p-4 md:grid-cols-2">
                {docOptions.map((option) => (
                  <li key={option.href}>
                    <NavLink
                      to={option.href}
                      className="block select-none space-y-1 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-gray-100 hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground"
                    >
                      <div className="text-sm font-semibold leading-none text-gray-900">
                        {option.title}
                      </div>
                      <p className="text-sm leading-snug text-gray-500">
                        {option.description}
                      </p>
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          </NavigationMenuContent>
        </NavigationMenuItem>
      </NavigationMenuList>
    </NavigationMenu>
  );
};

export default NavMenu;
