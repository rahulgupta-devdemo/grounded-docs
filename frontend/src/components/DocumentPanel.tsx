import { useRef, useState } from "react";

import { type DocumentInfo, uploadDocument } from "../api";

type Props = {
  documents: DocumentInfo[];
  selectedIds: Set<string>;
  loadError: string | null;
  onToggle: (id: string) => void;
  onUploaded: (document: DocumentInfo) => void;
};

export default function DocumentPanel({ documents, selectedIds, loadError, onToggle, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [errors, setErrors] = useState<string[]>([]);

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
    <aside className="flex w-80 shrink-0 flex-col border-r border-slate-200 bg-white">
      <header className="border-b border-slate-200 p-4">
        <h1 className="text-lg font-semibold">Document Chat</h1>
        <p className="text-sm text-slate-500">Answers come only from your documents.</p>
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
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-wait disabled:bg-slate-500"
        >
          {uploading ? `Indexing ${uploading}…` : "Upload PDF"}
        </button>
        {errors.map((error) => (
          <p key={error} className="mt-2 text-sm text-red-600">
            {error}
          </p>
        ))}
      </div>

      <section className="flex-1 overflow-y-auto px-4 pb-4">
        <h2 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">Search in</h2>
        {loadError && <p className="text-sm text-red-600">Could not load documents: {loadError}</p>}
        {documents.length === 0 && !loadError && (
          <p className="text-sm text-slate-500">No documents yet. Upload a PDF to start.</p>
        )}
        <ul className="space-y-1">
          {documents.map((doc) => (
            <li key={doc.id}>
              <label className="flex cursor-pointer items-start gap-2 rounded-md p-2 hover:bg-slate-50">
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
                  <span className="block text-xs text-slate-500">
                    {doc.pages} {doc.pages === 1 ? "page" : "pages"} · {doc.chunks}{" "}
                    {doc.chunks === 1 ? "passage" : "passages"}
                  </span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );
}
