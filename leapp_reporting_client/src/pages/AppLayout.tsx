import { Outlet } from "react-router-dom";
import Sidebar from "@/custom/Sidebar";
import NavMenu from "@/custom/NavMenu";

const AppLayout = () => {
  return (
    <div className="flex min-h-screen w-full flex-col bg-gray-100">
      <Sidebar />
      <div className="flex flex-col sm:gap-4 sm:p-6 sm:pl-20">
        <NavMenu />
        <Outlet />
      </div>
    </div>
  );
};

export default AppLayout;
