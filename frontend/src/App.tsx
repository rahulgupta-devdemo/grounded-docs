import { useEffect, useState } from "react";

import { type DocumentInfo, listDocuments } from "./api";
import ChatPanel from "./components/ChatPanel";
import DocumentPanel from "./components/DocumentPanel";
import { useChat } from "./useChat";

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loadError, setLoadError] = useState<string | null>(null);
  const chat = useChat();

  useEffect(() => {
    listDocuments()
      .then((docs) => {
        setDocuments(docs);
        setSelectedIds(new Set(docs.map((d) => d.id)));
      })
      .catch((error: Error) => setLoadError(error.message));
  }, []);

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
    <div className="flex h-screen bg-slate-50 text-slate-900">
      <DocumentPanel
        documents={documents}
        selectedIds={selectedIds}
        loadError={loadError}
        busy={chat.busy}
        onToggle={toggleSelected}
        onSelect={setSelected}
        onUploaded={handleUploaded}
        onDeleted={handleDeleted}
        onSummarize={chat.summarize}
      />
      <ChatPanel
        messages={chat.messages}
        busy={chat.busy}
        hasDocuments={documents.length > 0}
        scope={
          documents.length === 0
            ? null
            : allSelected
              ? `Searching all ${documents.length} documents`
              : `Searching ${selectedCount} of ${documents.length} documents`
        }
        onAsk={(question) => chat.ask(question, searchScope)}
      />
    </div>
  );
}
