import { Toaster } from "./components";
import { QueueMonitor, type QueueItem } from "./screens/QueueMonitor";
import { ThemeProvider } from "./theme/ThemeProvider";

const SAMPLE: QueueItem[] = [
  {
    id: "1",
    title: "Judicial Review — parts 1–3",
    sub: "3 recordings · 02:41:12 · large-v3",
    status: "run",
    statusLabel: "transcribing",
    progress: 64,
  },
  {
    id: "2",
    title: "Standing & ripeness — seminar",
    sub: "1 recording · 00:52:08 · summary.md ready",
    status: "done",
    statusLabel: "done",
  },
  {
    id: "3",
    title: "Commerce clause — guest lecture",
    sub: "2 recordings · 01:18:44 · queued #3",
    status: "queued",
    statusLabel: "queued",
  },
];

export default function App() {
  return (
    <ThemeProvider>
      <QueueMonitor state="ready" items={SAMPLE} />
      <Toaster />
    </ThemeProvider>
  );
}
