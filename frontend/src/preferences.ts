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

export const SIDEBAR_MIN = 260;
export const SIDEBAR_MAX = 600;
const SIDEBAR_DEFAULT = 320;

export function clampSidebarWidth(width: number): number {
  return Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, Math.round(width)));
}

export function initialSidebarWidth(): number {
  const stored = Number(read("sidebarWidth"));
  return Number.isFinite(stored) && stored > 0 ? clampSidebarWidth(stored) : SIDEBAR_DEFAULT;
}

export function save(key: "language" | "theme" | "sidebarWidth", value: string): void {
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
