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

  if (config.baseUrl) {
    lines.push(`LEXMOUNT_BASE_URL=${config.baseUrl}`);
  }

  return `${lines.join("\n")}\n`;
}

const ENVIRONMENTS = {
  cn: {
    label: "browser.lexmount.cn",
    apiKeysUrl: "https://browser.lexmount.cn/settings/api-keys",
    baseUrl: "",
  },
  com: {
    label: "browser.lexmount.com",
    apiKeysUrl: "https://browser.lexmount.com/settings/api-keys",
    baseUrl: "https://api.lexmount.com",
  },
};

function detectExistingConfig() {
  const apiKey = (process.env.LEXMOUNT_API_KEY || "").trim();
  const projectId = (process.env.LEXMOUNT_PROJECT_ID || "").trim();
  const rawBaseUrl = (process.env.LEXMOUNT_BASE_URL || "").trim();

  if (!apiKey || !projectId) {
    return null;
  }

  const environment = rawBaseUrl.includes(".com") ? "com" : "cn";

  return {
    apiKey,
    projectId,
    rawBaseUrl,
    environment,
  };
}

function openPromptStreams() {
  if (input.isTTY && output.isTTY) {
    return {
      input,
      output,
      close() {
        input.pause();
      },
    };
  }

  try {
    const ttyInput = fs.createReadStream("/dev/tty");
    const ttyOutput = fs.createWriteStream("/dev/tty");
    return {
      input: ttyInput,
      output: ttyOutput,
      close() {
        ttyInput.destroy();
        ttyOutput.destroy();
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
    streams.output.write("Lexmount skill setup\n");
    streams.output.write("Choose environment:\n");
    streams.output.write("  a. browser.lexmount.cn\n");
    streams.output.write("  b. browser.lexmount.com\n");

    let environmentAnswer = "";
    while (!["a", "b"].includes(environmentAnswer)) {
      environmentAnswer = (await rl.question("Environment [a/b]: ")).trim().toLowerCase();
    }

    const environment = environmentAnswer === "b" ? "com" : "cn";
    const environmentConfig = ENVIRONMENTS[environment];
    const existingConfig = detectExistingConfig();

    let apiKey = "";
    let projectId = "";

    if (existingConfig) {
      streams.output.write("\n");
      streams.output.write("Detected existing Lexmount environment variables in the current shell.\n");
      streams.output.write(`  Environment: ${ENVIRONMENTS[existingConfig.environment].label}\n`);
      streams.output.write(`  LEXMOUNT_API_KEY: ${existingConfig.apiKey}\n`);
      streams.output.write(`  LEXMOUNT_PROJECT_ID: ${existingConfig.projectId}\n`);
      if (existingConfig.rawBaseUrl) {
        streams.output.write(`  LEXMOUNT_BASE_URL: ${existingConfig.rawBaseUrl}\n`);
      }

      const importAnswer = (
        await rl.question("Import this configuration into the installed skill? [Y/n]: ")
      ).trim().toLowerCase();

      if (importAnswer === "" || importAnswer === "y" || importAnswer === "yes") {
        apiKey = existingConfig.apiKey;
        projectId = existingConfig.projectId;
      }
    }

    if (!apiKey || !projectId) {
      streams.output.write("\n");
      streams.output.write("Get your project_id and api_key from:\n");
      streams.output.write(`  ${environmentConfig.apiKeysUrl}\n`);
      apiKey = (await rl.question("LEXMOUNT_API_KEY: ")).trim();
      projectId = (await rl.question("LEXMOUNT_PROJECT_ID: ")).trim();
    }

    const installDepsAnswer = (
      await rl.question("Create ~/.codex/skills/lexmount-browser/.venv and install requirements now? [Y/n]: ")
    ).trim().toLowerCase();

    return {
      environment,
      apiKey,
      projectId,
      baseUrl: environmentConfig.baseUrl,
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
  const pipPath = path.join(venvDir, "bin", "pip");

  runCommand("python3", ["-m", "venv", venvDir], targetDir);
  runCommand(pipPath, ["install", "-r", requirementsFile], targetDir);
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

  if (config.installDeps) {
    console.log("");
    console.log("Creating skill-local virtual environment and installing Python dependencies...");
    installPythonVenv();
  }

  console.log(`Installed skill to ${targetDir}`);
  console.log("");
  console.log("Saved configuration to:");
  console.log(`  ${path.join(targetDir, ".env")}`);
  console.log("");
  console.log("Create the virtual environment inside the installed skill directory:");
  console.log(`  ${path.join(targetDir, ".venv")}`);
  console.log("");
  if (config.installDeps) {
    console.log("Python dependencies were installed into:");
    console.log(`  ${path.join(targetDir, ".venv")}`);
  } else {
    console.log("Initialize Python dependencies with:");
    console.log(`  python3 -m venv ${path.join(targetDir, ".venv")}`);
    console.log(`  ${path.join(targetDir, ".venv", "bin", "pip")} install -r ${path.join(targetDir, "requirements.txt")}`);
  }
  console.log("");
  console.log("You can update these values later by editing that file.");
  console.log("Restart Codex to ensure the new skill is discovered.");
  finalizeTerminal();
}

main().catch((error) => {
  console.error(`Failed to install skill into ${targetDir}`);
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
