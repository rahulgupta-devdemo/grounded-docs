import { type FormEvent, useEffect, useRef, useState } from "react";

import { askQuestion, type ChatResponse } from "../api";
import Exchange from "./Exchange";

export type Message = {
  id: number;
  question: string;
  status: "loading" | "done" | "error";
  response?: ChatResponse;
  error?: string;
  seconds?: number;
};

type Props = {
  documentIds: string[];
  hasDocuments: boolean;
};

export default function ChatPanel({ documentIds, hasDocuments }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const busy = messages.some((m) => m.status === "loading");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function update(id: number, patch: Partial<Message>) {
    setMessages((current) => current.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = question.trim();
    if (!text || busy) return;

    const id = Date.now();
    setMessages((current) => [...current, { id, question: text, status: "loading" }]);
    setQuestion("");
    const started = performance.now();
    try {
      const response = await askQuestion(text, documentIds);
      update(id, { status: "done", response, seconds: (performance.now() - started) / 1000 });
    } catch (error) {
      update(id, { status: "error", error: (error as Error).message });
    }
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
              <p className="mt-1 text-sm">Questions in English or German. Every answer cites its sources.</p>
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
      </form>
    </main>
  );
}
