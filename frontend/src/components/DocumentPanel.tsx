import { useRef, useState } from "react";

import { deleteDocument, type DocumentInfo, fileUrl, uploadDocument } from "../api";
import { type Language, useT } from "../i18n";
import type { Theme } from "../preferences";

type Props = {
  documents: DocumentInfo[];
  selectedIds: Set<string>;
  loadError: string | null;
  busy: boolean;
  language: Language;
  theme: Theme;
  onLanguageChange: (language: Language) => void;
  onThemeChange: (theme: Theme) => void;
  onToggle: (id: string) => void;
  onSelect: (ids: string[], selected: boolean) => void;
  onUploaded: (document: DocumentInfo) => void;
  onDeleted: (id: string) => void;
  onSummarize: (document: DocumentInfo) => void;
};

const iconProps = {
  width: 16,
  height: 16,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

function SunIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg {...iconProps}>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

const linkButton =
  "text-slate-600 hover:underline disabled:text-slate-400 disabled:no-underline dark:text-slate-300 dark:disabled:text-slate-600";

export default function DocumentPanel({
  documents,
  selectedIds,
  loadError,
  busy,
  language,
  theme,
  onLanguageChange,
  onThemeChange,
  onToggle,
  onSelect,
  onUploaded,
  onDeleted,
  onSummarize,
}: Props) {
  const t = useT();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [query, setQuery] = useState("");

  const needle = query.trim().toLowerCase();
  const shown = needle ? documents.filter((d) => d.filename.toLowerCase().includes(needle)) : documents;
  const shownIds = shown.map((d) => d.id);

  async function remove(document: DocumentInfo) {
    if (!window.confirm(t.confirmDelete(document.filename))) return;
    try {
      await deleteDocument(document.id);
      onDeleted(document.id);
    } catch (error) {
      setErrors([`${document.filename}: ${(error as Error).message}`]);
    }
  }

  async function uploadFiles(files: FileList | null) {
    if (!files) return;
    setErrors([]);
    for (const file of Array.from(files)) {
      setUploading(file.name);
      try {
        onUploaded(await uploadDocument(file));
      } catch (error) {
        setErrors((current) => [...current, `${file.name}: ${(error as Error).message}`]);
      }
    }
    setUploading(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <aside className="flex w-80 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <header className="border-b border-slate-200 p-4 dark:border-slate-800">
        <div className="flex items-center justify-between gap-2">
          <h1 className="text-lg font-semibold">{t.appTitle}</h1>
          <div className="flex items-center gap-2 text-xs">
            <div className="flex overflow-hidden rounded-md border border-slate-300 dark:border-slate-600">
              {(["en", "de"] as const).map((code) => (
                <button
                  key={code}
                  type="button"
                  aria-pressed={language === code}
                  onClick={() => onLanguageChange(code)}
                  className={`px-2 py-0.5 font-medium uppercase ${
                    language === code
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                      : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                  }`}
                >
                  {code}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => onThemeChange(theme === "dark" ? "light" : "dark")}
              aria-label={theme === "dark" ? t.themeLight : t.themeDark}
              title={theme === "dark" ? t.themeLight : t.themeDark}
              className="rounded-md border border-slate-300 p-1 text-slate-600 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            </button>
          </div>
        </div>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{t.appSubtitle}</p>
      </header>

      <div className="p-4">
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="hidden"
          onChange={(e) => uploadFiles(e.target.files)}
        />
        <button
          type="button"
          disabled={uploading !== null}
          onClick={() => inputRef.current?.click()}
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-wait disabled:bg-slate-500 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300 dark:disabled:bg-slate-600"
        >
          {uploading ? t.indexing(uploading) : t.upload}
        </button>
        {errors.map((error) => (
          <p key={error} className="mt-2 text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        ))}
      </div>

      <section className="flex-1 overflow-y-auto px-4 pb-4">
        <h2 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
          {t.searchIn}
        </h2>
        {loadError && <p className="text-sm text-red-600 dark:text-red-400">{t.couldNotLoad(loadError)}</p>}
        {documents.length === 0 && !loadError && (
          <p className="text-sm text-slate-500 dark:text-slate-400">{t.noDocuments}</p>
        )}
        {documents.length > 0 && (
          <div className="mb-2 space-y-1">
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t.filterPlaceholder}
              className="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm focus:border-slate-500 focus:outline-none dark:border-slate-600 dark:bg-slate-800 dark:focus:border-slate-400"
            />
            <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
              <span>{needle ? t.shownOf(shown.length, documents.length) : t.documentCount(documents.length)}</span>
              <button
                type="button"
                onClick={() => onSelect(shownIds, true)}
                className="ml-auto font-medium text-slate-700 hover:underline dark:text-slate-300"
              >
                {t.selectShown}
              </button>
              <button
                type="button"
                onClick={() => onSelect(shownIds, false)}
                className="font-medium text-slate-700 hover:underline dark:text-slate-300"
              >
                {t.deselectShown}
              </button>
            </div>
          </div>
        )}
        {needle && shown.length === 0 && <p className="text-sm text-slate-500 dark:text-slate-400">{t.noMatch}</p>}
        <ul className="space-y-1">
          {shown.map((doc) => (
            <li key={doc.id} className="rounded-md p-2 hover:bg-slate-50 dark:hover:bg-slate-800">
              <label className="flex cursor-pointer items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={selectedIds.has(doc.id)}
                  onChange={() => onToggle(doc.id)}
                />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium" title={doc.filename}>
                    {doc.filename}
                  </span>
                  <span className="block text-xs text-slate-500 dark:text-slate-400">
                    {t.pages(doc.pages)} · {t.passages(doc.chunks)}
                  </span>
                </span>
              </label>
              <div className="mt-1 flex gap-3 pl-6 text-xs">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onSummarize(doc)}
                  className={`font-medium ${linkButton}`}
                >
                  {t.summary}
                </button>
                <a href={fileUrl(doc.id)} target="_blank" rel="noreferrer" className={linkButton}>
                  {t.open}
                </a>
                <a href={fileUrl(doc.id)} download={doc.filename} className={linkButton}>
                  {t.download}
                </a>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => remove(doc)}
                  className="ml-auto text-red-600 hover:underline disabled:text-slate-400 disabled:no-underline dark:text-red-400 dark:disabled:text-slate-600"
                >
                  {t.delete}
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );
}
