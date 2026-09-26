import { useRef, useState } from "react";

import { deleteDocument, type DocumentInfo, fileUrl, uploadDocument } from "../api";

type Props = {
  documents: DocumentInfo[];
  selectedIds: Set<string>;
  loadError: string | null;
  busy: boolean;
  onToggle: (id: string) => void;
  onSelect: (ids: string[], selected: boolean) => void;
  onUploaded: (document: DocumentInfo) => void;
  onDeleted: (id: string) => void;
  onSummarize: (document: DocumentInfo) => void;
};

export default function DocumentPanel({
  documents,
  selectedIds,
  loadError,
  busy,
  onToggle,
  onSelect,
  onUploaded,
  onDeleted,
  onSummarize,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [query, setQuery] = useState("");

  const needle = query.trim().toLowerCase();
  const shown = needle ? documents.filter((d) => d.filename.toLowerCase().includes(needle)) : documents;
  const shownIds = shown.map((d) => d.id);

  async function remove(document: DocumentInfo) {
    if (!window.confirm(`Delete ${document.filename}? Its passages and the stored PDF are removed.`)) return;
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
        {documents.length > 0 && (
          <div className="mb-2 space-y-1">
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter documents by name…"
              className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm focus:border-slate-500 focus:outline-none"
            />
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span>
                {needle ? `${shown.length} of ${documents.length} shown` : `${documents.length} documents`}
              </span>
              <button
                type="button"
                onClick={() => onSelect(shownIds, true)}
                className="ml-auto font-medium text-slate-700 hover:underline"
              >
                Select shown
              </button>
              <button
                type="button"
                onClick={() => onSelect(shownIds, false)}
                className="font-medium text-slate-700 hover:underline"
              >
                Deselect shown
              </button>
            </div>
          </div>
        )}
        {needle && shown.length === 0 && <p className="text-sm text-slate-500">No document name matches.</p>}
        <ul className="space-y-1">
          {shown.map((doc) => (
            <li key={doc.id} className="rounded-md p-2 hover:bg-slate-50">
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
                  <span className="block text-xs text-slate-500">
                    {doc.pages} {doc.pages === 1 ? "page" : "pages"} · {doc.chunks}{" "}
                    {doc.chunks === 1 ? "passage" : "passages"}
                  </span>
                </span>
              </label>
              <div className="mt-1 flex gap-3 pl-6 text-xs">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onSummarize(doc)}
                  className="font-medium text-slate-700 hover:underline disabled:text-slate-400 disabled:no-underline"
                >
                  Summary
                </button>
                <a href={fileUrl(doc.id)} target="_blank" rel="noreferrer" className="text-slate-600 hover:underline">
                  Open
                </a>
                <a href={fileUrl(doc.id)} download={doc.filename} className="text-slate-600 hover:underline">
                  Download
                </a>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => remove(doc)}
                  className="ml-auto text-red-600 hover:underline disabled:text-slate-400 disabled:no-underline"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );
}
