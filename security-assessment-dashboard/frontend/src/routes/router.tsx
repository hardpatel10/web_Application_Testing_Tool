import { createBrowserRouter } from "react-router-dom";

import { DashboardLayout } from "@/layouts/DashboardLayout";
import AssessmentDetails from "@/pages/AssessmentDetails";
import Assessments from "@/pages/Assessments";
import Dashboard from "@/pages/Dashboard";
import Executions from "@/pages/Executions";
import FindingDetails from "@/pages/FindingDetails";
import Findings from "@/pages/Findings";
import NotFound from "@/pages/NotFound";
import Reports from "@/pages/Reports";
import Search from "@/pages/Search";
import SecurityOverview from "@/pages/SecurityOverview";
import Settings from "@/pages/Settings";
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
      { path: "findings", element: <Findings /> },
      { path: "findings/:id", element: <FindingDetails /> },
      // Not in main navigation (superseded by Findings' own severity summary + Dashboard), but
      // kept reachable via a link from the Findings page rather than deleted outright -- it
      // wasn't named in the removal list and still has real content nothing else duplicates.
      { path: "security-overview", element: <SecurityOverview /> },
      { path: "search", element: <Search /> },
      { path: "reports", element: <Reports /> },
      { path: "settings", element: <Settings /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
