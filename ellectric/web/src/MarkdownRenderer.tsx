/**
 * Lightweight markdown renderer for Copilot assistant messages.
 * Zero external dependencies — hand-rolled regex-based parser.
 *
 * Supported: paragraphs, H3/H4 headings, bullet lists (-/*),
 * numbered lists (1.), bold (**text**), inline code (`code`),
 * fenced code blocks (```), links ([text](url)).
 *
 * Streaming-safe: unclosed markers render as plain text.
 */
import type { ReactNode } from "react";

interface InlineToken {
  type: "text" | "bold" | "code" | "link";
  text?: string;
  url?: string;
}

function parseInline(text: string): InlineToken[] {
  const tokens: InlineToken[] = [];
  let remaining = text;
  const re = /(\*\*(.+?)\*\*)|(`(.+?)`)|(\[(.+?)\]\((.+?)\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = re.exec(remaining)) !== null) {
    // Text before this match
    if (match.index > lastIndex) {
      tokens.push({ type: "text", text: remaining.slice(lastIndex, match.index) });
    }
    if (match[1]) {
      tokens.push({ type: "bold", text: match[2] });
    } else if (match[3]) {
      tokens.push({ type: "code", text: match[4] });
    } else if (match[5]) {
      tokens.push({ type: "link", text: match[6], url: match[7] });
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < remaining.length) {
    tokens.push({ type: "text", text: remaining.slice(lastIndex) });
  }
  return tokens;
}

function renderInline(tokens: InlineToken[], keyPrefix: string): ReactNode[] {
  return tokens.map((t, i) => {
    const key = `${keyPrefix}-i${i}`;
    switch (t.type) {
      case "bold":
        return <strong key={key} className="chat-md-strong">{t.text}</strong>;
      case "code":
        return <code key={key} className="chat-md-code">{t.text}</code>;
      case "link":
        return <a key={key} className="chat-md-a" href={t.url} target="_blank" rel="noopener noreferrer">{t.text}</a>;
      default:
        return t.text || null;
    }
  });
}

interface Block {
  type: "h3" | "h4" | "p" | "pre" | "ul" | "ol" | "empty";
  content: string;
}

function isListLine(line: string): boolean {
  return /^[-*]\s/.test(line) || /^\d+\.\s/.test(line);
}

function listType(line: string): "ul" | "ol" {
  return /^\d+\.\s/.test(line) ? "ol" : "ul";
}

export function renderMarkdown(text: string): ReactNode[] {
  if (!text) return [];

  const blocks: Block[] = [];
  const lines = text.split("\n");
  let inCodeBlock = false;
  let codeAccum: string[] = [];
  let listAccum: string[] = [];
  let currentListType: "ul" | "ol" | null = null;

  function flushList(): void {
    if (listAccum.length > 0 && currentListType) {
      blocks.push({ type: currentListType, content: listAccum.join("\n") });
      listAccum = [];
      currentListType = null;
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Fenced code block
    if (line.trimStart().startsWith("```")) {
      if (inCodeBlock) {
        blocks.push({ type: "pre", content: codeAccum.join("\n") });
        codeAccum = [];
        inCodeBlock = false;
      } else {
        flushList();
        inCodeBlock = true;
        codeAccum = [];
      }
      continue;
    }
    if (inCodeBlock) {
      codeAccum.push(line);
      continue;
    }

    // Heading
    if (line.startsWith("### ")) {
      flushList();
      blocks.push({ type: "h3", content: line.slice(4) });
      continue;
    }
    if (line.startsWith("#### ")) {
      flushList();
      blocks.push({ type: "h4", content: line.slice(5) });
      continue;
    }

    // List item
    if (isListLine(line)) {
      const lt = listType(line);
      if (currentListType && currentListType !== lt) {
        flushList();
      }
      currentListType = lt;
      listAccum.push(line.replace(/^[-*]\s/, "").replace(/^\d+\.\s/, ""));
      continue;
    }

    // Non-list line after list items
    if (listAccum.length > 0 && line.trim() === "") {
      flushList();
      continue;
    }
    if (listAccum.length > 0 && !isListLine(line)) {
      flushList();
    }

    // Empty line = paragraph break
    if (line.trim() === "") {
      continue;
    }

    // Regular paragraph line
    blocks.push({ type: "p", content: line });
  }

  // Flush remaining
  if (inCodeBlock) {
    // Unclosed code block during streaming — render as plain code
    blocks.push({ type: "pre", content: codeAccum.join("\n") });
  }
  flushList();

  // Merge consecutive paragraph lines
  const merged: Block[] = [];
  for (const block of blocks) {
    if (block.type === "p" && merged.length > 0 && merged[merged.length - 1].type === "p") {
      merged[merged.length - 1] = {
        type: "p",
        content: merged[merged.length - 1].content + "\n" + block.content,
      };
    } else {
      merged.push(block);
    }
  }

  // Render blocks
  return merged.map((block, bi) => {
    const key = `md-${bi}`;
    switch (block.type) {
      case "h3":
        return <h3 key={key} className="chat-md-h3">{renderInline(parseInline(block.content), key)}</h3>;
      case "h4":
        return <h4 key={key} className="chat-md-h4">{renderInline(parseInline(block.content), key)}</h4>;
      case "p":
        return <p key={key} className="chat-md-p">{renderInline(parseInline(block.content), key)}</p>;
      case "pre":
        return <pre key={key} className="chat-md-pre">{block.content}</pre>;
      case "ul": {
        const items = block.content.split("\n").filter(Boolean);
        return (
          <ul key={key} className="chat-md-ul">
            {items.map((item, ii) => (
              <li key={`${key}-li${ii}`}>{renderInline(parseInline(item), `${key}-li${ii}`)}</li>
            ))}
          </ul>
        );
      }
      case "ol": {
        const oitems = block.content.split("\n").filter(Boolean);
        return (
          <ol key={key} className="chat-md-ol">
            {oitems.map((item, ii) => (
              <li key={`${key}-li${ii}`}>{renderInline(parseInline(item), `${key}-li${ii}`)}</li>
            ))}
          </ol>
        );
      }
      default:
        return null;
    }
  });
}
