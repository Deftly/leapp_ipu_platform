import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppLayout from "@/pages/AppLayout";
import UnderConstruction from "@/pages/UnderConstruction";
import Workflows from "@/pages/Workflows";
import Stages from "@/pages/Stages";

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<UnderConstruction page="Dashboard" />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="workflows/:hostname/:txId/stages" element={<Stages />} />
          <Route path="hosts" element={<UnderConstruction page="Hosts" />} />
          <Route
            path="analytics"
            element={<UnderConstruction page="Analytics" />}
          />
          <Route path="FAQ" element={<UnderConstruction page="FAQ" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
