import { type PropsWithChildren, useEffect } from "react";

export function ThemeProvider({ children }: PropsWithChildren) {
  useEffect(() => {
    const root = document.documentElement;
    root.classList.add("dark");
  }, []);

  return children;
}
