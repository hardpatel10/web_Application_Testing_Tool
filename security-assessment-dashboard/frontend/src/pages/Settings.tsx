import { Moon, Settings as SettingsIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function Settings() {
  return (
    <div className="space-y-7">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Preferences</p>
        <h1 className="text-4xl font-semibold tracking-normal text-foreground">Settings</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Manage application preferences as configuration options become available.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>Dark mode is active for the redesigned interface.</CardDescription>
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-border/70 bg-secondary/55 text-primary">
            <Moon className="h-5 w-5" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4 text-sm leading-6 text-muted-foreground">
            Future preferences will appear here. The current visual system is dark-only to keep contrast, hierarchy, and depth consistent.
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Application</CardTitle>
            <CardDescription>Workspace-level settings and integrations.</CardDescription>
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-border/70 bg-secondary/55 text-primary">
            <SettingsIcon className="h-5 w-5" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 p-4 text-sm leading-6 text-muted-foreground">
            Additional settings will appear once they are backed by real application configuration.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
