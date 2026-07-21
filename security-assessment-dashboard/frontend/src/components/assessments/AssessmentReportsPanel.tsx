import { FileBarChart, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";

/** Assessment-scoped placeholder mirroring the global Reports page -- report generation
 * (`backend/reporting/`) remains an unbuilt future phase; this stays honestly empty until it exists. */
export function AssessmentReportsPanel() {
  return (
    <EmptyState
      title="No reports available"
      description="Generating a report for this assessment will appear here once report generation is built."
      action={<Button variant="outline" disabled><Sparkles className="h-4 w-4" /> Awaiting completed work</Button>}
      tip="This tab intentionally stays empty until real report data exists."
      icon={<FileBarChart className="h-5 w-5" />}
    />
  );
}
