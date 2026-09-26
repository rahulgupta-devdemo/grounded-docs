import { createContext, useContext } from "react";

export type Language = "en" | "de";

const en = {
  appTitle: "Document Chat",
  appSubtitle: "Answers come only from your documents.",
  themeDark: "Dark",
  themeLight: "Light",
  upload: "Upload PDF",
  indexing: (name: string) => `Indexing ${name}…`,
  searchIn: "Search in",
  couldNotLoad: (error: string) => `Could not load documents: ${error}`,
  noDocuments: "No documents yet. Upload a PDF to start.",
  filterPlaceholder: "Filter documents by name…",
  shownOf: (shown: number, total: number) => `${shown} of ${total} shown`,
  documentCount: (n: number) => (n === 1 ? "1 document" : `${n} documents`),
  selectShown: "Select shown",
  deselectShown: "Deselect shown",
  noMatch: "No document name matches.",
  pages: (n: number) => (n === 1 ? "1 page" : `${n} pages`),
  passages: (n: number) => (n === 1 ? "1 passage" : `${n} passages`),
  pageNumber: (page: number) => `page ${page}`,
  summary: "Summary",
  open: "Open",
  download: "Download",
  delete: "Delete",
  confirmDelete: (name: string) => `Delete ${name}? Its passages and the stored PDF are removed.`,
  emptyWithDocuments: "Ask a question about your documents",
  emptyWithoutDocuments: "Upload a PDF to get started",
  emptyHint: "Questions in English or German. Every answer cites its sources.",
  summaryHint: " Use “Summary” next to a document for an overview.",
  questionPlaceholder: "Ask a question about your documents…",
  ask: "Ask",
  scopeAll: (n: number) => `Searching all ${n} documents`,
  scopeSome: (selected: number, total: number) => `Searching ${selected} of ${total} documents`,
  summaryOf: (name: string) => `Summary of ${name}`,
  loadingSummary: "Reading the whole document…",
  loadingQuestion: "Searching the documents…",
  costUnknown: "cost unknown",
  tokens: (input: number, output: number) => `${input} in / ${output} out tokens`,
  sources: "Sources",
  alsoRetrieved: (n: number) => `Also retrieved, not used in the answer (${n})`,
  openPage: (page: number) => `Open page ${page} in the PDF ↗`,
  similarity: "Cosine similarity to the question",
  showSource: (n: number) => `Show source ${n}`,
};

export type Messages = typeof en;

const de: Messages = {
  appTitle: "Dokumenten-Chat",
  appSubtitle: "Antworten kommen nur aus Ihren Dokumenten.",
  themeDark: "Dunkel",
  themeLight: "Hell",
  upload: "PDF hochladen",
  indexing: (name) => `${name} wird indexiert…`,
  searchIn: "Suchen in",
  couldNotLoad: (error) => `Dokumente konnten nicht geladen werden: ${error}`,
  noDocuments: "Noch keine Dokumente. Laden Sie ein PDF hoch.",
  filterPlaceholder: "Dokumente nach Namen filtern…",
  shownOf: (shown, total) => `${shown} von ${total} angezeigt`,
  documentCount: (n) => (n === 1 ? "1 Dokument" : `${n} Dokumente`),
  selectShown: "Angezeigte auswählen",
  deselectShown: "Angezeigte abwählen",
  noMatch: "Kein Dokumentname passt.",
  pages: (n) => (n === 1 ? "1 Seite" : `${n} Seiten`),
  passages: (n) => (n === 1 ? "1 Abschnitt" : `${n} Abschnitte`),
  pageNumber: (page) => `Seite ${page}`,
  summary: "Zusammenfassung",
  open: "Öffnen",
  download: "Herunterladen",
  delete: "Löschen",
  confirmDelete: (name) => `${name} löschen? Die Abschnitte und das gespeicherte PDF werden entfernt.`,
  emptyWithDocuments: "Stellen Sie eine Frage zu Ihren Dokumenten",
  emptyWithoutDocuments: "Laden Sie ein PDF hoch, um zu beginnen",
  emptyHint: "Fragen auf Deutsch oder Englisch. Jede Antwort nennt ihre Quellen.",
  summaryHint: " Mit „Zusammenfassung“ neben einem Dokument erhalten Sie einen Überblick.",
  questionPlaceholder: "Frage zu Ihren Dokumenten stellen…",
  ask: "Fragen",
  scopeAll: (n) => `Suche in allen ${n} Dokumenten`,
  scopeSome: (selected, total) => `Suche in ${selected} von ${total} Dokumenten`,
  summaryOf: (name) => `Zusammenfassung von ${name}`,
  loadingSummary: "Das ganze Dokument wird gelesen…",
  loadingQuestion: "Die Dokumente werden durchsucht…",
  costUnknown: "Kosten unbekannt",
  tokens: (input, output) => `${input} ein / ${output} aus Tokens`,
  sources: "Quellen",
  alsoRetrieved: (n) => `Ebenfalls gefunden, nicht in der Antwort verwendet (${n})`,
  openPage: (page) => `Seite ${page} im PDF öffnen ↗`,
  similarity: "Kosinus-Ähnlichkeit zur Frage",
  showSource: (n) => `Quelle ${n} anzeigen`,
};

export const messages: Record<Language, Messages> = { en, de };

const I18nContext = createContext<Messages>(en);

export const I18nProvider = I18nContext.Provider;

export function useT(): Messages {
  return useContext(I18nContext);
}
