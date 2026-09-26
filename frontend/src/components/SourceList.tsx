import { fileUrl, type Source } from "../api";
import { useT } from "../i18n";

type Props = {
  sources: Source[];
  active: number | null;
  onSelect: (number: number) => void;
  elementId: (number: number) => string;
};

export default function SourceList({ sources, active, onSelect, elementId }: Props) {
  const t = useT();
  const cited = sources.filter((s) => s.cited);
  const other = sources.filter((s) => !s.cited);
  const activeIsOther = other.some((s) => s.number === active);

  return (
    <div className="mt-4 space-y-3">
      {cited.length > 0 && (
        <div>
          <h3 className="mb-1 text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
            {t.sources}
          </h3>
          <SourceItems sources={cited} active={active} onSelect={onSelect} elementId={elementId} />
        </div>
      )}
      {other.length > 0 && (
        <details open={activeIsOther || undefined}>
          <summary className="cursor-pointer text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-400">
            {t.alsoRetrieved(other.length)}
          </summary>
          <div className="mt-1">
            <SourceItems sources={other} active={active} onSelect={onSelect} elementId={elementId} />
          </div>
        </details>
      )}
    </div>
  );
}

function SourceItems({ sources, active, onSelect, elementId }: Props) {
  const t = useT();
  return (
    <ul className="space-y-1">
      {sources.map((source) => {
        const isActive = source.number === active;
        return (
          <li
            key={source.number}
            id={elementId(source.number)}
            className={`rounded-md border ${
              isActive
                ? "border-slate-400 bg-slate-50 dark:border-slate-500 dark:bg-slate-800"
                : "border-slate-200 dark:border-slate-700"
            }`}
          >
            <button
              type="button"
              onClick={() => onSelect(source.number)}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm"
            >
              <span className="rounded bg-slate-200 px-1.5 text-xs font-semibold text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                {source.number}
              </span>
              <span className="min-w-0 flex-1 truncate">
                {source.filename}{" "}
                <span className="text-slate-500 dark:text-slate-400">· {t.pageNumber(source.page)}</span>
              </span>
              {source.score !== null && (
                <span className="text-xs text-slate-400 dark:text-slate-500" title={t.similarity}>
                  {source.score.toFixed(2)}
                </span>
              )}
            </button>
            {isActive && (
              <div className="border-t border-slate-200 px-3 py-2 dark:border-slate-700">
                <p className="text-sm whitespace-pre-wrap text-slate-700 dark:text-slate-300">{source.text}</p>
                <a
                  href={fileUrl(source.document_id, source.page)}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block text-xs font-medium text-slate-700 hover:underline dark:text-slate-300"
                >
                  {t.openPage(source.page)}
                </a>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
