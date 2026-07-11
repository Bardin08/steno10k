import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MarkdownView({ source }: { source: string }) {
  return (
    <div className="prose-editorial max-w-[68ch] text-ink [&_a]:text-accent-ink [&_code]:font-mono [&_h1]:text-2xl [&_h2]:text-xl [&_h2]:mt-6 [&_li]:my-1 [&_p]:my-3 [&_ul]:list-disc [&_ul]:pl-5">
      <Markdown remarkPlugins={[remarkGfm]}>{source}</Markdown>
    </div>
  );
}
