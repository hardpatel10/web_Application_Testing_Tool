import { FileBarChart, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";

export default function Reports() {
  return (
    <div className="space-y-7">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Output</p>
        <h1 className="text-4xl font-semibold tracking-normal text-foreground">Reports</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Generated assessment reports will collect here as completed work becomes available.
        </p>
      </div>

      <EmptyState
        title="No reports available"
        description="Reports generated from completed assessments will appear here with export options and review status."
        action={<Button variant="outline" disabled><Sparkles className="h-4 w-4" /> Awaiting completed work</Button>}
        tip="This page intentionally stays empty until real report data exists."
        icon={<FileBarChart className="h-5 w-5" />}
      />
    </div>
  );
}
