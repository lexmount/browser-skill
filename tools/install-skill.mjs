#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const skillName = "lexmount-browser";
const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const codexHome = process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
const skillsDir = path.join(codexHome, "skills");
const targetDir = path.join(skillsDir, skillName);

const entriesToCopy = ["SKILL.md", "REFERENCE.md", "README.md", "scripts"];

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function removeDirIfExists(dir) {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    ensureDir(dest);
    for (const entry of fs.readdirSync(src)) {
      copyRecursive(path.join(src, entry), path.join(dest, entry));
    }
    return;
  }

  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
}

function main() {
  try {
    ensureDir(skillsDir);
    removeDirIfExists(targetDir);
    ensureDir(targetDir);

    for (const entry of entriesToCopy) {
      copyRecursive(path.join(packageRoot, entry), path.join(targetDir, entry));
    }

    console.log(`Installed skill to ${targetDir}`);
    console.log("Restart Codex to ensure the new skill is discovered.");
  } catch (error) {
    console.error(`Failed to install skill into ${targetDir}`);
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}

main();
