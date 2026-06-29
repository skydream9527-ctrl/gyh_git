/**
 * Workspace utility functions — extracted from WorkspacePage.tsx for reuse
 * across workspace sub-panels and components.
 */
import type { FileMeta } from "@/types/api";

export type FileCategory = "sql" | "data" | "other";

export const FILE_CATEGORY_DEFS: { key: FileCategory; label: string; icon: string }[] = [
  { key: "sql", label: "SQL", icon: "🗃" },
  { key: "data", label: "数据", icon: "📊" },
  { key: "other", label: "其他文档", icon: "📄" },
];

export const DATA_FORMATS = new Set(["csv", "tsv", "json", "parquet", "xlsx", "xls"]);

export function categorizeFile(f: FileMeta): FileCategory {
  const fmt = (f.format || "").toLowerCase();
  if (fmt === "sql") return "sql";
  if (DATA_FORMATS.has(fmt)) return "data";
  return "other";
}

export function fmtIcon(fmt?: string | null): string {
  switch ((fmt || "").toLowerCase()) {
    case "md":
    case "txt":
      return "📝";
    case "csv":
    case "tsv":
      return "📊";
    case "json":
      return "🧾";
    case "py":
      return "🐍";
    case "sql":
      return "🗃";
    case "png":
    case "jpg":
    case "jpeg":
      return "🖼";
    default:
      return "📄";
  }
}

export function fmtSize(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

/**
 * Skill 描述右栏展示只保留极短概述。
 */
export function shortDesc(s: string): string {
  const clean = s
    .replace(/\r?\n/g, " ")
    .replace(/[*_`]+/g, "")
    .replace(/\s+/g, " ")
    .trim();
  let weight = 0;
  let out = "";
  for (const ch of clean) {
    const isCJK = /[一-鿿]/.test(ch);
    const w = isCJK ? 1 : 0.5;
    if (weight + w > 10) {
      out += "…";
      break;
    }
    weight += w;
    out += ch;
  }
  return out;
}
