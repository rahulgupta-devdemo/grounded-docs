import { type FormEvent, useEffect, useRef, useState } from "react";

import { useT } from "../i18n";
import type { Message } from "../useChat";
import Exchange from "./Exchange";

type Props = {
  messages: Message[];
  busy: boolean;
  hasDocuments: boolean;
  scope: string | null;
  onAsk: (question: string) => void;
};

export default function ChatPanel({ messages, busy, hasDocuments, scope, onAsk }: Props) {
  const t = useT();
  const [question, setQuestion] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const text = question.trim();
    if (!text || busy) return;
    onAsk(text);
    setQuestion("");
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-8 p-6">
          {messages.length === 0 && (
            <div className="mt-24 text-center text-slate-500 dark:text-slate-400">
              <p className="text-lg font-medium text-slate-700 dark:text-slate-200">
                {hasDocuments ? t.emptyWithDocuments : t.emptyWithoutDocuments}
              </p>
              <p className="mt-1 text-sm">
                {t.emptyHint}
                {hasDocuments && t.summaryHint}
              </p>
            </div>
          )}
          {messages.map((message) => (
            <Exchange key={message.id} message={message} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      <form
        onSubmit={submit}
        className="border-t border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="mx-auto flex max-w-3xl gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={2000}
            placeholder={t.questionPlaceholder}
            className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-slate-500 focus:outline-none dark:border-slate-600 dark:bg-slate-800 dark:focus:border-slate-400"
          />
          <button
            type="submit"
            disabled={busy || !question.trim()}
            className="rounded-md bg-slate-900 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:bg-slate-400 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300 dark:disabled:bg-slate-600"
          >
            {t.ask}
          </button>
        </div>
        {scope && <p className="mx-auto mt-2 max-w-3xl text-xs text-slate-500 dark:text-slate-400">{scope}</p>}
      </form>
    </main>
  );
}
