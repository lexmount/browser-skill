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
const isWindows = process.platform === "win32";

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

const REGIONS = {
  china: {
    label: "China region",
    endpointLabel: "browser.lexmount.cn",
    apiKeysUrl: "https://browser.lexmount.cn/settings/api-keys",
    baseUrl: "",
  },
  global: {
    label: "Global region",
    endpointLabel: "browser.lexmount.com",
    apiKeysUrl: "https://browser.lexmount.com/settings/api-keys",
    baseUrl: "https://api.lexmount.com",
  },
};

function parseEnvFile(content) {
  const values = {};

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    const separatorIndex = line.indexOf("=");
    if (separatorIndex === -1) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();
    const value = line.slice(separatorIndex + 1).trim();
    values[key] = value;
  }

  return values;
}

function detectExistingConfig() {
  const envPath = path.join(targetDir, ".env");
  if (!fs.existsSync(envPath)) {
    return null;
  }

  const envValues = parseEnvFile(fs.readFileSync(envPath, "utf8"));
  const apiKey = (envValues.LEXMOUNT_API_KEY || "").trim();
  const projectId = (envValues.LEXMOUNT_PROJECT_ID || "").trim();
  const rawBaseUrl = (envValues.LEXMOUNT_BASE_URL || "").trim();

  if (!apiKey || !projectId) {
    return null;
  }

  const region = rawBaseUrl.includes(".com") ? "global" : "china";

  return {
    apiKey,
    projectId,
    rawBaseUrl,
    region,
    envPath,
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

  if (isWindows) {
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

function parseBooleanEnv(name) {
  const raw = (process.env[name] || "").trim().toLowerCase();
  if (!raw) {
    return null;
  }
  if (["1", "true", "yes", "y"].includes(raw)) {
    return true;
  }
  if (["0", "false", "no", "n"].includes(raw)) {
    return false;
  }
  throw new Error(`${name} must be one of: 1, true, yes, y, 0, false, no, n`);
}

function nonInteractiveConfig() {
  const enabled = parseBooleanEnv("LEXMOUNT_INSTALL_NONINTERACTIVE");
  if (!enabled) {
    return null;
  }

  const region = ((process.env.LEXMOUNT_INSTALL_REGION || "").trim().toLowerCase()) || "china";
  if (!Object.hasOwn(REGIONS, region)) {
    throw new Error("LEXMOUNT_INSTALL_REGION must be 'china' or 'global'.");
  }

  const apiKey = (process.env.LEXMOUNT_API_KEY || "").trim();
  const projectId = (process.env.LEXMOUNT_PROJECT_ID || "").trim();
  if (!apiKey || !projectId) {
    throw new Error("LEXMOUNT_API_KEY and LEXMOUNT_PROJECT_ID are required in non-interactive mode.");
  }

  const installDeps = parseBooleanEnv("LEXMOUNT_INSTALL_DEPS");
  return {
    region,
    apiKey,
    projectId,
    baseUrl: REGIONS[region].baseUrl,
    installDeps: installDeps ?? true,
  };
}

async function promptConfig() {
  const preconfigured = nonInteractiveConfig();
  if (preconfigured) {
    return preconfigured;
  }

  const streams = openPromptStreams();
  const rl = readline.createInterface({
    input: streams.input,
    output: streams.output,
    terminal: Boolean(streams.output.isTTY),
  });

  try {
    streams.output.write("Lexmount skill setup\n");
    streams.output.write("Choose region preset:\n");
    streams.output.write(`  a. ${REGIONS.china.label} (${REGIONS.china.endpointLabel})\n`);
    streams.output.write(`  b. ${REGIONS.global.label} (${REGIONS.global.endpointLabel})\n`);

    let regionAnswer = "";
    while (!["a", "b"].includes(regionAnswer)) {
      regionAnswer = (await rl.question("Region preset [a/b]: ")).trim().toLowerCase();
    }

    const region = regionAnswer === "b" ? "global" : "china";
    const regionConfig = REGIONS[region];
    const existingConfig = detectExistingConfig();

    let apiKey = "";
    let projectId = "";

    if (existingConfig) {
      streams.output.write("\n");
      streams.output.write("Detected existing Lexmount skill configuration.\n");
      streams.output.write(`  File: ${existingConfig.envPath}\n`);
      streams.output.write(`  Region preset: ${REGIONS[existingConfig.region].label} (${REGIONS[existingConfig.region].endpointLabel})\n`);
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
      streams.output.write(`  ${regionConfig.apiKeysUrl}\n`);
      apiKey = (await rl.question("LEXMOUNT_API_KEY: ")).trim();
      projectId = (await rl.question("LEXMOUNT_PROJECT_ID: ")).trim();
    }

    const installDepsAnswer = (
      await rl.question("Create ~/.codex/skills/lexmount-browser/.venv and install requirements now? [Y/n]: ")
    ).trim().toLowerCase();

    return {
      region,
      apiKey,
      projectId,
      baseUrl: regionConfig.baseUrl,
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

function pythonCommand() {
  return isWindows ? "python" : "python3";
}

function venvBinary(venvDir, name) {
  if (isWindows) {
    return path.join(venvDir, "Scripts", `${name}.exe`);
  }
  return path.join(venvDir, "bin", name);
}

function installPythonVenv() {
  const venvDir = path.join(targetDir, ".venv");
  const requirementsFile = path.join(targetDir, "requirements.txt");
  const pipPath = venvBinary(venvDir, "pip");

  runCommand(pythonCommand(), ["-m", "venv", venvDir], targetDir);
  runCommand(pipPath, ["install", "-r", requirementsFile], targetDir);
}

function printHelp() {
  console.log("Install the Lexmount Codex browser skill.");
  console.log("");
  console.log("Usage:");
  console.log("  npx @lexmount/browser-skill-installer");
  console.log("  node tools/install-skill.mjs");
  console.log("");
  console.log("Non-interactive mode:");
  console.log("  Set LEXMOUNT_INSTALL_NONINTERACTIVE=1");
  console.log("  Set LEXMOUNT_API_KEY and LEXMOUNT_PROJECT_ID");
  console.log("  Optional: LEXMOUNT_INSTALL_REGION=china|global");
  console.log("  Optional: LEXMOUNT_INSTALL_DEPS=1|0");
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
    const venvDir = path.join(targetDir, ".venv");
    const pipPath = venvBinary(venvDir, "pip");
    console.log("Initialize Python dependencies with:");
    console.log(`  ${pythonCommand()} -m venv ${venvDir}`);
    console.log(`  ${pipPath} install -r ${path.join(targetDir, "requirements.txt")}`);
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
