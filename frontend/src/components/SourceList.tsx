import type { Source } from "../api";

type Props = {
  sources: Source[];
  active: number | null;
  onSelect: (number: number) => void;
  elementId: (number: number) => string;
};

export default function SourceList({ sources, active, onSelect, elementId }: Props) {
  const cited = sources.filter((s) => s.cited);
  const other = sources.filter((s) => !s.cited);
  const activeIsOther = other.some((s) => s.number === active);

  return (
    <div className="mt-4 space-y-3">
      {cited.length > 0 && (
        <div>
          <h3 className="mb-1 text-xs font-semibold tracking-wide text-slate-500 uppercase">Sources</h3>
          <SourceItems sources={cited} active={active} onSelect={onSelect} elementId={elementId} />
        </div>
      )}
      {other.length > 0 && (
        <details open={activeIsOther || undefined}>
          <summary className="cursor-pointer text-xs font-semibold tracking-wide text-slate-500 uppercase">
            Also retrieved, not used in the answer ({other.length})
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
  return (
    <ul className="space-y-1">
      {sources.map((source) => {
        const isActive = source.number === active;
        return (
          <li
            key={source.number}
            id={elementId(source.number)}
            className={`rounded-md border ${isActive ? "border-slate-400 bg-slate-50" : "border-slate-200"}`}
          >
            <button
              type="button"
              onClick={() => onSelect(source.number)}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm"
            >
              <span className="rounded bg-slate-200 px-1.5 text-xs font-semibold text-slate-700">{source.number}</span>
              <span className="min-w-0 flex-1 truncate">
                {source.filename} <span className="text-slate-500">· page {source.page}</span>
              </span>
              <span className="text-xs text-slate-400" title="Cosine similarity to the question">
                {source.score.toFixed(2)}
              </span>
            </button>
            {isActive && (
              <p className="border-t border-slate-200 px-3 py-2 text-sm whitespace-pre-wrap text-slate-700">
                {source.text}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
