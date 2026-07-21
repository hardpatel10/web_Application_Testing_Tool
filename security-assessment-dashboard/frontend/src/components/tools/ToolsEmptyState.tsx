import { ExternalLink, PackageSearch, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const SUPPORTED_TOOLS: { name: string; install: string; homepage: string }[] = [
  { name: "Nmap", install: "https://nmap.org/download.html", homepage: "https://nmap.org" },
  { name: "Nuclei", install: "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest", homepage: "https://github.com/projectdiscovery/nuclei" },
  { name: "WhatWeb", install: "gem install whatweb", homepage: "https://github.com/urbanadventurer/WhatWeb" },
  { name: "Nikto", install: "apt install nikto  /  brew install nikto", homepage: "https://cirt.net/Nikto2" },
  { name: "HTTPX", install: "go install github.com/projectdiscovery/httpx/cmd/httpx@latest", homepage: "https://github.com/projectdiscovery/httpx" },
  { name: "Gobuster", install: "go install github.com/OJ/gobuster/v3@latest", homepage: "https://github.com/OJ/gobuster" },
  { name: "Dirsearch", install: "pip install dirsearch", homepage: "https://github.com/maurosoria/dirsearch" },
  { name: "Feroxbuster", install: "cargo install feroxbuster", homepage: "https://github.com/epi052/feroxbuster" },
  { name: "FFUF", install: "go install github.com/ffuf/ffuf/v2@latest", homepage: "https://github.com/ffuf/ffuf" },
  { name: "SSLScan", install: "apt install sslscan  /  brew install sslscan", homepage: "https://github.com/rbsec/sslscan" },
  { name: "Katana", install: "go install github.com/projectdiscovery/katana/cmd/katana@latest", homepage: "https://github.com/projectdiscovery/katana" },
  { name: "Naabu", install: "go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest", homepage: "https://github.com/projectdiscovery/naabu" },
  { name: "Subfinder", install: "go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest", homepage: "https://github.com/projectdiscovery/subfinder" },
  { name: "Amass", install: "go install github.com/owasp-amass/amass/v4/...@master", homepage: "https://github.com/owasp-amass/amass" },
  { name: "DNSx", install: "go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest", homepage: "https://github.com/projectdiscovery/dnsx" },
];

interface ToolsEmptyStateProps {
  onRefresh: () => void;
  isRefreshing: boolean;
}

export function ToolsEmptyState({ onRefresh, isRefreshing }: ToolsEmptyStateProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-border/70 bg-secondary/60 text-primary">
            <PackageSearch className="h-5 w-5" />
          </div>
          <div>
            <CardTitle>No supported tools are installed</CardTitle>
            <p className="mt-1 max-w-xl text-sm leading-6 text-muted-foreground">
              This dashboard doesn't bundle any security tools — it detects tools you install yourself. Install one or
              more of the tools below, then click Refresh Detection.
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={onRefresh} disabled={isRefreshing}>
          <RefreshCw className={isRefreshing ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh Detection
        </Button>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {SUPPORTED_TOOLS.map((tool) => (
            <div key={tool.name} className="rounded-xl border border-border/60 bg-secondary/25 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-foreground">{tool.name}</p>
                <a href={tool.homepage} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-primary">
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
              <code className="mt-1 block truncate text-xs text-muted-foreground" title={tool.install}>
                {tool.install}
              </code>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
