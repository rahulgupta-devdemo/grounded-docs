import { useState } from "react";

import { askQuestion, type ChatResponse, summarizeDocument } from "./api";

export type Message = {
  id: number;
  kind: "question" | "summary";
  question: string;
  status: "loading" | "done" | "error";
  response?: ChatResponse;
  error?: string;
  seconds?: number;
};

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const busy = messages.some((m) => m.status === "loading");

  function update(id: number, patch: Partial<Message>) {
    setMessages((current) => current.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }

  async function run(kind: Message["kind"], question: string, request: () => Promise<ChatResponse>) {
    const id = Date.now();
    setMessages((current) => [...current, { id, kind, question, status: "loading" }]);
    const started = performance.now();
    try {
      const response = await request();
      update(id, { status: "done", response, seconds: (performance.now() - started) / 1000 });
    } catch (error) {
      update(id, { status: "error", error: (error as Error).message });
    }
  }

  return {
    messages,
    busy,
    ask: (question: string, documentIds: string[] | null) =>
      run("question", question, () => askQuestion(question, documentIds)),
    summarize: (documentId: string, label: string) =>
      run("summary", label, () => summarizeDocument(documentId)),
  };
}
