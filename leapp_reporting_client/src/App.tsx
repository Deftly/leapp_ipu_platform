import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppLayout from "@/pages/AppLayout";
import UnderConstruction from "@/pages/UnderConstruction";
import Analytics from "@/pages/Analytics";
import Workflows from "@/pages/Workflows";
import Dashboard from "@/pages/Dashboard";
import Hosts from "@/pages/Hosts";
import Stages from "@/pages/Stages";

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="/data/workflows" element={<Workflows />} />
          <Route
            path="/data/workflows/:hostname/:txId/stages"
            element={<Stages />}
          />
          <Route path="/data/hosts" element={<Hosts />} />
          <Route path="/data/analytics" element={<Analytics />} />
          <Route
            path="/docs/knownIssues"
            element={<UnderConstruction page="Known Issues" />}
          />
          <Route
            path="/docs/releaseInfo"
            element={<UnderConstruction page="Release Info" />}
          />
          <Route
            path="/docs/endUserAgreement"
            element={<UnderConstruction page="End User Agreement" />}
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
