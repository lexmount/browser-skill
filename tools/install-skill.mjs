#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import readline from "node:readline/promises";
import { fileURLToPath } from "node:url";
import { stdin as input, stdout as output } from "node:process";

const skillName = "lexmount-browser";
const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const codexHome = process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
const skillsDir = path.join(codexHome, "skills");
const targetDir = path.join(skillsDir, skillName);

const entriesToCopy = ["SKILL.md", "REFERENCE.md", "README.md", "requirements.txt", "scripts"];

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

function envFileContent(config) {
  const lines = [
    `LEXMOUNT_API_KEY=${config.apiKey}`,
    `LEXMOUNT_PROJECT_ID=${config.projectId}`,
  ];

  return `${lines.join("\n")}\n`;
}

function openPromptStreams() {
  try {
    const ttyInput = fs.createReadStream("/dev/tty");
    const ttyOutput = fs.createWriteStream("/dev/tty");
    return {
      input: ttyInput,
      output: ttyOutput,
      close() {
        ttyInput.destroy();
        ttyOutput.end();
      },
    };
  } catch {
    return {
      input,
      output,
      close() {},
    };
  }
}

async function promptConfig() {
  const streams = openPromptStreams();
  const rl = readline.createInterface({ input: streams.input, output: streams.output });

  try {
    streams.output.write("Lexmount skill setup\n");
    const apiKey = (await rl.question("LEXMOUNT_API_KEY: ")).trim();
    const projectId = (await rl.question("LEXMOUNT_PROJECT_ID: ")).trim();

    return {
      apiKey,
      projectId,
    };
  } finally {
    rl.close();
    streams.close();
  }
}

async function main() {
  const config = await promptConfig();
  if (!config.apiKey || !config.projectId) {
    throw new Error("LEXMOUNT_API_KEY and LEXMOUNT_PROJECT_ID are required. If prompts did not appear, rerun this command from an interactive terminal.");
  }

  ensureDir(skillsDir);
  removeDirIfExists(targetDir);
  ensureDir(targetDir);

  for (const entry of entriesToCopy) {
    copyRecursive(path.join(packageRoot, entry), path.join(targetDir, entry));
  }

  fs.writeFileSync(path.join(targetDir, ".env"), envFileContent(config), "utf8");

  console.log(`Installed skill to ${targetDir}`);
  console.log("");
  console.log("Saved configuration to:");
  console.log(`  ${path.join(targetDir, ".env")}`);
  console.log("");
  console.log("Initialize Python dependencies with:");
  console.log(`  python3 -m venv ${path.join(targetDir, ".venv")}`);
  console.log(`  ${path.join(targetDir, ".venv", "bin", "pip")} install -r ${path.join(targetDir, "requirements.txt")}`);
  console.log("");
  console.log("You can update these values later by editing that file.");
  console.log("Restart Codex to ensure the new skill is discovered.");
}

main().catch((error) => {
  console.error(`Failed to install skill into ${targetDir}`);
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
