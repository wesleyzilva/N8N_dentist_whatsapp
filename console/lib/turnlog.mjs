import fs from "node:fs";
import path from "node:path";
import { ROOT } from "./repo.mjs";

export const TURN_LOG = path.join(ROOT, "logs", "turns.jsonl");

export function readTurnLog(limit = 100) {
  if (!fs.existsSync(TURN_LOG)) return { path: "logs/turns.jsonl", exists: false, total: 0, entries: [] };
  const lines = fs.readFileSync(TURN_LOG, "utf8").split(/\r?\n/).filter(Boolean);
  const entries = lines
    .slice(-Math.min(Math.max(limit, 1), 500))
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean)
    .reverse();
  return { path: "logs/turns.jsonl", exists: true, total: lines.length, entries };
}

export function clearTurnLog() {
  if (fs.existsSync(TURN_LOG)) fs.writeFileSync(TURN_LOG, "");
  return { cleared: true };
}
