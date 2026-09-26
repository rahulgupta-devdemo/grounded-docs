import { useEffect, useState } from "react";

import { type DocumentInfo, listDocuments } from "./api";
import ChatPanel from "./components/ChatPanel";
import DocumentPanel from "./components/DocumentPanel";
import { I18nProvider, type Language, messages } from "./i18n";
import { initialLanguage, initialTheme, save, type Theme } from "./preferences";
import { useChat } from "./useChat";

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loadError, setLoadError] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language>(initialLanguage);
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const chat = useChat();
  const t = messages[language];

  // Loaded once when the page opens. Right after `docker compose up` the backend
  // can need a few seconds more than nginx, so a failed load is retried for up to
  // 20 seconds before the error is shown. Once loaded, nothing runs again.
  useEffect(() => {
    let cancelled = false;
    let retry: ReturnType<typeof setTimeout> | undefined;

    function load(attemptsLeft: number) {
      listDocuments()
        .then((docs) => {
          if (cancelled) return;
          setDocuments(docs);
          setSelectedIds(new Set(docs.map((d) => d.id)));
        })
        .catch((error: Error) => {
          if (cancelled) return;
          if (attemptsLeft > 0) retry = setTimeout(() => load(attemptsLeft - 1), 2000);
          else setLoadError(error.message);
        });
    }

    load(10);
    return () => {
      cancelled = true;
      clearTimeout(retry);
    };
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    save("theme", theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = language;
    document.title = t.appTitle;
    save("language", language);
  }, [language, t]);

  function handleUploaded(document: DocumentInfo) {
    setDocuments((docs) =>
      [...docs.filter((d) => d.id !== document.id), document].sort((a, b) =>
        a.filename.localeCompare(b.filename),
      ),
    );
    setSelectedIds((ids) => new Set(ids).add(document.id));
  }

  function handleDeleted(id: string) {
    setDocuments((docs) => docs.filter((d) => d.id !== id));
    setSelectedIds((ids) => {
      const next = new Set(ids);
      next.delete(id);
      return next;
    });
  }

  function toggleSelected(id: string) {
    setSelectedIds((ids) => {
      const next = new Set(ids);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function setSelected(ids: string[], selected: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      for (const id of ids) {
        if (selected) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  }

  const selectedCount = documents.filter((d) => selectedIds.has(d.id)).length;
  const allSelected = documents.length > 0 && selectedCount === documents.length;
  // With everything selected, search all documents instead of sending every id.
  const searchScope = allSelected ? null : documents.filter((d) => selectedIds.has(d.id)).map((d) => d.id);

  return (
    <I18nProvider value={t}>
      <div className="flex h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        <DocumentPanel
          documents={documents}
          selectedIds={selectedIds}
          loadError={loadError}
          busy={chat.busy}
          language={language}
          theme={theme}
          onLanguageChange={setLanguage}
          onThemeChange={setTheme}
          onToggle={toggleSelected}
          onSelect={setSelected}
          onUploaded={handleUploaded}
          onDeleted={handleDeleted}
          onSummarize={(doc) => chat.summarize(doc.id, t.summaryOf(doc.filename))}
        />
        <ChatPanel
          messages={chat.messages}
          busy={chat.busy}
          hasDocuments={documents.length > 0}
          scope={
            documents.length === 0
              ? null
              : allSelected
                ? t.scopeAll(documents.length)
                : t.scopeSome(selectedCount, documents.length)
          }
          onAsk={(question) => chat.ask(question, searchScope)}
        />
      </div>
    </I18nProvider>
  );
}
