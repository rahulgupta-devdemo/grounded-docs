import type { Language } from "./i18n";

export type Theme = "light" | "dark";

// localStorage can be unavailable (private mode, blocked storage); the app
// then simply starts with the defaults.
function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function save(key: "language" | "theme", value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // ignore
  }
}

export function initialLanguage(): Language {
  const stored = read("language");
  if (stored === "en" || stored === "de") return stored;
  return navigator.language.toLowerCase().startsWith("de") ? "de" : "en";
}

export function initialTheme(): Theme {
  const stored = read("theme");
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
