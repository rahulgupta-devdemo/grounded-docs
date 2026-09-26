import { useT } from "../i18n";

// Same citation format the backend parses: [1], [2][3], [1, 4].
const CITATION = /(\[\d+(?:\s*,\s*\d+)*\])/;
const BOLD = /(\*\*[^*]+\*\*)/;
// "* item" or "- item" at the start of a line; "**bold**" is not matched.
const BULLET = /^(\s*)[*-]\s+/gm;

type Props = {
  text: string;
  onCite: (number: number) => void;
};

export default function AnswerText({ text, onCite }: Props) {
  const t = useT();
  return (
    <p className="text-[15px] leading-relaxed whitespace-pre-wrap">
      {text.replace(BULLET, "$1• ").split(CITATION).map((part, i) =>
        CITATION.test(part) ? (
          part
            .slice(1, -1)
            .split(",")
            .map((n) => Number(n.trim()))
            .map((number) => (
              <button
                key={`${i}-${number}`}
                type="button"
                onClick={() => onCite(number)}
                title={t.showSource(number)}
                className="mx-0.5 rounded bg-slate-200 px-1.5 align-baseline text-xs font-semibold text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
              >
                {number}
              </button>
            ))
        ) : (
          <WithBold key={i} text={part} />
        ),
      )}
    </p>
  );
}

function WithBold({ text }: { text: string }) {
  return (
    <>
      {text.split(BOLD).map((part, i) =>
        BOLD.test(part) ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
      )}
    </>
  );
}
