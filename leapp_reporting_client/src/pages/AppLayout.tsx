import { Outlet } from "react-router-dom";
import Sidebar from "@/custom/Sidebar";

const AppLayout = () => {
  return (
    <div className="flex min-h-screen w-full flex-col bg-gray-100">
      <Sidebar />
      <div className="flex flex-col sm:gap-4 sm:py-4 sm:pl-14">
        <Outlet />
      </div>
    </div>
  );
};

export default AppLayout;
