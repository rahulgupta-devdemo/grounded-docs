import { type FormEvent, useEffect, useRef, useState } from "react";

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
            <div className="mt-24 text-center text-slate-500">
              <p className="text-lg font-medium text-slate-700">
                {hasDocuments ? "Ask a question about your documents" : "Upload a PDF to get started"}
              </p>
              <p className="mt-1 text-sm">
                Questions in English or German. Every answer cites its sources.
                {hasDocuments && " Use “Summary” next to a document for an overview."}
              </p>
            </div>
          )}
          {messages.map((message) => (
            <Exchange key={message.id} message={message} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      <form onSubmit={submit} className="border-t border-slate-200 bg-white p-4">
        <div className="mx-auto flex max-w-3xl gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={2000}
            placeholder="Ask a question about your documents…"
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy || !question.trim()}
            className="rounded-md bg-slate-900 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:bg-slate-400"
          >
            Ask
          </button>
        </div>
        {scope && <p className="mx-auto mt-2 max-w-3xl text-xs text-slate-500">{scope}</p>}
      </form>
    </main>
  );
}
