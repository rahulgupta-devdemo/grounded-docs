import { useEffect, useState } from "react";

import { type DocumentInfo, listDocuments } from "./api";
import ChatPanel from "./components/ChatPanel";
import DocumentPanel from "./components/DocumentPanel";

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loadError, setLoadError] = useState<string | null>(null);

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

  function toggleSelected(id: string) {
    setSelectedIds((ids) => {
      const next = new Set(ids);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900">
      <DocumentPanel
        documents={documents}
        selectedIds={selectedIds}
        loadError={loadError}
        onToggle={toggleSelected}
        onUploaded={handleUploaded}
      />
      <ChatPanel documentIds={[...selectedIds]} hasDocuments={documents.length > 0} />
    </div>
  );
}
