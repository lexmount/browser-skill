#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
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
  return {
    input,
    output,
    close() {
      input.pause();
    },
  };
}

function finalizeTerminal() {
  if (output.isTTY) {
    output.write("\n");
  }
}

async function promptConfig() {
  const streams = openPromptStreams();
  const rl = readline.createInterface({
    input: streams.input,
    output: streams.output,
    terminal: Boolean(streams.output.isTTY),
  });

  try {
    streams.output.write("Lexmount skill setup (Windows)\n");
    const apiKey = (await rl.question("LEXMOUNT_API_KEY: ")).trim();
    const projectId = (await rl.question("LEXMOUNT_PROJECT_ID: ")).trim();
    const installDepsAnswer = (
      await rl.question("Create ~/.codex/skills/lexmount-browser/.venv and install requirements now? [Y/n]: ")
    ).trim().toLowerCase();

    return {
      apiKey,
      projectId,
      installDeps: installDepsAnswer === "" || installDepsAnswer === "y" || installDepsAnswer === "yes",
    };
  } finally {
    rl.close();
    streams.close();
  }
}

function runCommand(command, args, cwd) {
  const result = spawnSync(command, args, {
    cwd,
    stdio: "inherit",
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed with exit code ${result.status}`);
  }
}

function installPythonVenv() {
  const venvDir = path.join(targetDir, ".venv");
  const requirementsFile = path.join(targetDir, "requirements.txt");
  const pipPath = path.join(venvDir, "Scripts", "pip.exe");

  runCommand("python", ["-m", "venv", venvDir], targetDir);
  runCommand(pipPath, ["install", "-r", requirementsFile], targetDir);
}

function printHelp() {
  console.log("Install the Lexmount Codex browser skill on Windows.");
  console.log("");
  console.log("Usage:");
  console.log("  node tools/install-skill-win.mjs");
  console.log("");
  console.log("This script is the Windows-specific installer variant.");
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes("-h") || args.includes("--help")) {
    printHelp();
    return;
  }

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

  if (config.installDeps) {
    console.log("");
    console.log("Creating skill-local virtual environment and installing Python dependencies...");
    installPythonVenv();
  }

  console.log(`Installed skill to ${targetDir}`);
  finalizeTerminal();
}

main().catch((error) => {
  console.error(`Failed to install skill into ${targetDir}`);
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
