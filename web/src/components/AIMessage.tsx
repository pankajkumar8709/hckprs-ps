"use client";
import React from "react";

/**
 * Lightweight, dependency-free renderer for AI answers. Handles:
 *  - markdown tables (| a | b |)
 *  - headings (#, ##)
 *  - bullet lists (-, *, •) and numbered lists (1.)
 *  - bold (**x**)
 *  - dates (YYYY-MM-DD / DD Month YYYY) -> highlighted chips
 *  - currency amounts ($1,120 / ₹24,500 / Rs 500) -> emphasized
 * Falls back to clean paragraphs for anything else.
 */

const DATE_RE =
  /\b(\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b/gi;
const MONEY_RE = /(?:[$₹]|Rs\.?\s?)\s?\d[\d,]*(?:\.\d+)?/g;

/** Render inline: bold, dates, money. Returns React nodes. */
function inline(text: string, keyBase: string): React.ReactNode[] {
  // First split on bold
  const nodes: React.ReactNode[] = [];
  const boldParts = text.split(/(\*\*[^*]+\*\*)/g);
  boldParts.forEach((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      nodes.push(
        <strong key={`${keyBase}-b${i}`} className="font-semibold text-ink">
          {highlight(part.slice(2, -2), `${keyBase}-b${i}`)}
        </strong>
      );
    } else {
      nodes.push(...highlight(part, `${keyBase}-t${i}`));
    }
  });
  return nodes;
}

/** Highlight dates and money within a plain string. */
function highlight(text: string, keyBase: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  let last = 0;
  // Combine matches from both regexes, sorted by index.
  const matches: { start: number; end: number; kind: "date" | "money"; val: string }[] = [];
  let m: RegExpExecArray | null;
  const d = new RegExp(DATE_RE);
  while ((m = d.exec(text))) matches.push({ start: m.index, end: m.index + m[0].length, kind: "date", val: m[0] });
  const mo = new RegExp(MONEY_RE);
  while ((m = mo.exec(text))) matches.push({ start: m.index, end: m.index + m[0].length, kind: "money", val: m[0] });
  matches.sort((a, b) => a.start - b.start);
  // Drop overlaps (keep earliest).
  const clean = matches.filter((x, i) => i === 0 || x.start >= matches[i - 1].end);

  clean.forEach((mt, i) => {
    if (mt.start > last) out.push(text.slice(last, mt.start));
    if (mt.kind === "date") {
      out.push(
        <span key={`${keyBase}-d${i}`} className="inline-flex items-center rounded-md bg-brand-50 text-brand-600 font-medium px-1.5 py-0.5 text-[0.82em]">
          {mt.val}
        </span>
      );
    } else {
      out.push(
        <span key={`${keyBase}-m${i}`} className="font-semibold text-ink">{mt.val}</span>
      );
    }
    last = mt.end;
  });
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function Table({ rows, keyBase }: { rows: string[]; keyBase: string }) {
  // rows: raw markdown table lines (header, separator, body...)
  const parse = (line: string) =>
    line.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
  const header = parse(rows[0]);
  const body = rows.slice(2).map(parse); // skip separator row (rows[1])
  return (
    <div className="my-2 overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-subtle">
            {header.map((h, i) => (
              <th key={i} className="text-left font-medium text-body px-3 py-2 whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((r, ri) => (
            <tr key={ri} className="border-t border-border">
              {r.map((c, ci) => (
                <td key={ci} className="px-3 py-2 align-top text-ink">{inline(c, `${keyBase}-${ri}-${ci}`)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AIMessage({ text }: { text: string }) {
  const lines = text.split("\n");
  const blocks: React.ReactNode[] = [];
  let i = 0;
  let listBuf: { ordered: boolean; items: string[] } | null = null;

  const flushList = () => {
    if (!listBuf) return;
    const L = listBuf; listBuf = null;
    const key = `list-${blocks.length}`;
    blocks.push(
      L.ordered ? (
        <ol key={key} className="list-decimal ml-5 space-y-1 text-body">
          {L.items.map((it, k) => <li key={k}>{inline(it, `${key}-${k}`)}</li>)}
        </ol>
      ) : (
        <ul key={key} className="list-disc ml-5 space-y-1 text-body">
          {L.items.map((it, k) => <li key={k}>{inline(it, `${key}-${k}`)}</li>)}
        </ul>
      )
    );
  };

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Table: current line looks like a row AND next line is a separator
    if (/^\|.*\|$/.test(trimmed) && i + 1 < lines.length && /^\|[\s:|-]+\|$/.test(lines[i + 1].trim())) {
      flushList();
      const tbl: string[] = [];
      while (i < lines.length && /^\|.*\|$/.test(lines[i].trim())) { tbl.push(lines[i].trim()); i++; }
      blocks.push(<Table key={`tbl-${blocks.length}`} rows={tbl} keyBase={`tbl-${blocks.length}`} />);
      continue;
    }

    if (trimmed === "") { flushList(); i++; continue; }

    // Headings
    if (/^#{1,3}\s+/.test(trimmed)) {
      flushList();
      const txt = trimmed.replace(/^#{1,3}\s+/, "");
      blocks.push(<h4 key={`h-${blocks.length}`} className="font-semibold text-ink mt-1">{inline(txt, `h-${blocks.length}`)}</h4>);
      i++; continue;
    }
    // Bullet
    if (/^[-*•]\s+/.test(trimmed)) {
      const it = trimmed.replace(/^[-*•]\s+/, "");
      if (!listBuf || listBuf.ordered) { flushList(); listBuf = { ordered: false, items: [] }; }
      listBuf.items.push(it); i++; continue;
    }
    // Numbered
    if (/^\d+\.\s+/.test(trimmed)) {
      const it = trimmed.replace(/^\d+\.\s+/, "");
      if (!listBuf || !listBuf.ordered) { flushList(); listBuf = { ordered: true, items: [] }; }
      listBuf.items.push(it); i++; continue;
    }
    // Paragraph
    flushList();
    blocks.push(<p key={`p-${blocks.length}`} className="text-body leading-relaxed">{inline(trimmed, `p-${blocks.length}`)}</p>);
    i++;
  }
  flushList();

  return <div className="space-y-2 text-sm">{blocks}</div>;
}
