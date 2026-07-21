import { createBrowserRouter } from "react-router-dom";

import { DashboardLayout } from "@/layouts/DashboardLayout";
import AssessmentDetails from "@/pages/AssessmentDetails";
import Assessments from "@/pages/Assessments";
import Dashboard from "@/pages/Dashboard";
import Executions from "@/pages/Executions";
import FindingDetails from "@/pages/FindingDetails";
import Findings from "@/pages/Findings";
import HostDetails from "@/pages/HostDetails";
import HostOverview from "@/pages/HostOverview";
import Hosts from "@/pages/Hosts";
import NotFound from "@/pages/NotFound";
import Observations from "@/pages/Observations";
import OperatingSystems from "@/pages/OperatingSystems";
import Reports from "@/pages/Reports";
import Search from "@/pages/Search";
import SecurityOverview from "@/pages/SecurityOverview";
import Services from "@/pages/Services";
import Settings from "@/pages/Settings";
import TechnologyOverview from "@/pages/TechnologyOverview";
import Technologies from "@/pages/Technologies";
import Tools from "@/pages/Tools";
import ToolDetails from "@/pages/ToolDetails";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <DashboardLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "assessments", element: <Assessments /> },
      { path: "assessments/:id", element: <AssessmentDetails /> },
      { path: "tools", element: <Tools /> },
      { path: "tools/:name", element: <ToolDetails /> },
      { path: "executions", element: <Executions /> },
      { path: "hosts", element: <Hosts /> },
      { path: "hosts/:id", element: <HostDetails /> },
      { path: "findings", element: <Findings /> },
      { path: "findings/:id", element: <FindingDetails /> },
      { path: "security-overview", element: <SecurityOverview /> },
      { path: "host-overview", element: <HostOverview /> },
      { path: "technology-overview", element: <TechnologyOverview /> },
      { path: "services", element: <Services /> },
      { path: "technologies", element: <Technologies /> },
      { path: "observations", element: <Observations /> },
      { path: "operating-systems", element: <OperatingSystems /> },
      { path: "search", element: <Search /> },
      { path: "reports", element: <Reports /> },
      { path: "settings", element: <Settings /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
