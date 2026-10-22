import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

export const abs = (...parts) => path.join(ROOT, ...parts);
export const exists = (...parts) => fs.existsSync(abs(...parts));

export function readText(...parts) {
  return fs.readFileSync(abs(...parts), "utf8").replace(/^\uFEFF/, "");
}

export function readJson(...parts) {
  return JSON.parse(readText(...parts));
}

export function tryReadJson(...parts) {
  try {
    return readJson(...parts);
  } catch {
    return null;
  }
}

const PLACEHOLDER = /(changeme|your[-_]|replace|example|troque|sk-\.\.\.|SUA_CHAVE|^x{3,}$|^\.{3}$|defina)/i;

export function isPlaceholder(value) {
  return !value || PLACEHOLDER.test(value);
}

export function loadEnvFile() {
  const values = {};
  if (!exists(".env")) return { exists: false, values };
  for (const line of readText(".env").split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/);
    if (!match || line.trim().startsWith("#")) continue;
    values[match[1]] = match[2].replace(/^["']|["']$/g, "");
  }
  return { exists: true, values };
}

export function envValue(name) {
  const fromFile = loadEnvFile().values[name];
  return process.env[name] ?? fromFile ?? "";
}

let pythonCache;
export function findPython() {
  if (pythonCache !== undefined) return pythonCache;
  const candidates = [process.env.PYTHON, "python3", "python", "py"].filter(Boolean);
  for (const cmd of candidates) {
    const probe = spawnSync(cmd, ["--version"], { encoding: "utf8" });
    if (probe.status === 0) {
      pythonCache = { cmd, version: (probe.stdout || probe.stderr).trim() };
      return pythonCache;
    }
  }
  pythonCache = null;
  return null;
}

export function run(cmd, args, { cwd = ROOT, timeout = 120_000, env = {} } = {}) {
  return new Promise((resolve) => {
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let child;
    try {
      child = spawn(cmd, args, {
        cwd,
        env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", PYTHONIOENCODING: "utf-8", ...env },
        windowsHide: true,
      });
    } catch (error) {
      resolve({ code: -1, stdout, stderr: String(error), timedOut });
      return;
    }
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill();
    }, timeout);
    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.stderr.on("data", (chunk) => (stderr += chunk));
    child.on("error", (error) => {
      clearTimeout(timer);
      resolve({ code: -1, stdout, stderr: stderr + String(error), timedOut });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr, timedOut });
    });
  });
}

export async function runPython(args, options) {
  const python = findPython();
  if (!python) {
    return { code: -1, stdout: "", stderr: "Python não encontrado (defina PYTHON=caminho)", timedOut: false };
  }
  return run(python.cmd, args, options);
}

export async function gitFiles() {
  const result = await run("git", ["ls-files"]);
  if (result.code !== 0) return null;
  return result.stdout.split(/\r?\n/).filter(Boolean);
}

export function walkFiles(dir = ROOT, out = []) {
  const skip = new Set([".git", "node_modules", "__pycache__", ".cache", ".pytest_cache"]);
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (skip.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walkFiles(full, out);
    else out.push(path.relative(ROOT, full).split(path.sep).join("/"));
  }
  return out;
}
