import { File, Folder, FolderUp } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useBrowseFilesystem } from "@/hooks/useTools";

interface FilesystemBrowseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /** If true, only directories can be selected (e.g. working/output/temp dir); otherwise only files (e.g. wordlists, executables). */
  selectDirectories?: boolean;
  onSelect: (path: string) => void;
}

export function FilesystemBrowseDialog({
  open,
  onOpenChange,
  title,
  selectDirectories = false,
  onSelect,
}: FilesystemBrowseDialogProps) {
  const [path, setPath] = useState<string | undefined>(undefined);
  const { data, isLoading, isError } = useBrowseFilesystem(path, open);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription className="truncate">{data?.path ?? "Loading…"}</DialogDescription>
        </DialogHeader>

        <div className="max-h-80 space-y-1 overflow-y-auto rounded-xl border border-border/60 bg-secondary/20 p-2">
          {isLoading && <Skeleton className="h-8 w-full" />}
          {isError && <p className="p-2 text-sm text-destructive">Couldn't read that directory.</p>}

          {data?.parent && (
            <button
              type="button"
              onClick={() => setPath(data.parent ?? undefined)}
              className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-secondary/60"
            >
              <FolderUp className="h-4 w-4 text-muted-foreground" /> ..
            </button>
          )}

          {data?.entries.map((entry) => (
            <button
              key={entry.path}
              type="button"
              onClick={() => (entry.is_directory ? setPath(entry.path) : selectDirectories ? undefined : onSelect(entry.path))}
              className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-secondary/60 disabled:opacity-40"
              disabled={!entry.is_directory && selectDirectories}
            >
              {entry.is_directory ? (
                <Folder className="h-4 w-4 text-primary" />
              ) : (
                <File className="h-4 w-4 text-muted-foreground" />
              )}
              <span className="truncate">{entry.name}</span>
            </button>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          {selectDirectories && data && (
            <Button onClick={() => onSelect(data.path)}>Select this folder</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
