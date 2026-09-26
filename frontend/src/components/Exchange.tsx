import { useState } from "react";

import type { Usage } from "../api";
import { type Messages, useT } from "../i18n";
import type { Message } from "../useChat";
import AnswerText from "./AnswerText";
import SourceList from "./SourceList";

export default function Exchange({ message }: { message: Message }) {
  const t = useT();
  const [activeSource, setActiveSource] = useState<number | null>(null);

  function showSource(number: number) {
    setActiveSource(number);
    requestAnimationFrame(() =>
      document
        .getElementById(sourceElementId(message.id, number))
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" }),
    );
  }

  return (
    <article className="space-y-3">
      <div className="flex justify-end">
        <p className="max-w-[80%] rounded-lg bg-slate-900 px-4 py-2 text-sm text-white dark:bg-slate-700">
          {message.question}
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        {message.status === "loading" && (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {message.kind === "summary" ? t.loadingSummary : t.loadingQuestion}
          </p>
        )}
        {message.status === "error" && <p className="text-sm text-red-600 dark:text-red-400">{message.error}</p>}
        {message.status === "done" && message.response && (
          <>
            <AnswerText text={message.response.answer} onCite={showSource} />
            {message.response.sources.length > 0 && (
              <SourceList
                sources={message.response.sources}
                active={activeSource}
                onSelect={(n) => setActiveSource(activeSource === n ? null : n)}
                elementId={(n) => sourceElementId(message.id, n)}
              />
            )}
            {message.response.usage && <UsageLine usage={message.response.usage} seconds={message.seconds} t={t} />}
          </>
        )}
      </div>
    </article>
  );
}

function UsageLine({ usage, seconds, t }: { usage: Usage; seconds?: number; t: Messages }) {
  const cost =
    usage.cost_usd === null ? t.costUnknown : usage.cost_usd < 0.0001 ? "< $0.0001" : `$${usage.cost_usd.toFixed(4)}`;
  const parts = [usage.model, t.tokens(usage.input_tokens, usage.output_tokens), cost];
  if (seconds !== undefined) parts.push(`${seconds.toFixed(1)} s`);
  return (
    <p className="mt-3 border-t border-slate-100 pt-2 text-xs text-slate-400 dark:border-slate-800 dark:text-slate-500">
      {parts.join(" · ")}
    </p>
  );
}

function sourceElementId(messageId: number, number: number): string {
  return `source-${messageId}-${number}`;
}
