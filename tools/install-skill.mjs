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
const sourceSkillDir = path.join(packageRoot, "skills", skillName);
const isWindows = process.platform === "win32";

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

function codexHome() {
  return process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
}

function targetDirectories(target) {
  const targets = {
    codex: path.join(codexHome(), "skills", skillName),
    claude: path.join(os.homedir(), ".claude", "skills", skillName),
  };
  if (target === "both") {
    return [targets.codex, targets.claude];
  }
  return [targets[target]];
}

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
  fs.chmodSync(dest, stat.mode);
}

function assertEnvValueSafe(key, value) {
  if (value.includes("\n") || value.includes("\r")) {
    throw new Error(`${key} must not contain newline characters.`);
  }
}

function quoteEnvValue(value) {
  return `"${value.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}

function parseEnvValue(value) {
  if (value.length >= 2 && value.startsWith('"') && value.endsWith('"')) {
    let parsed = "";
    for (let index = 1; index < value.length - 1; index += 1) {
      const char = value[index];
      if (char === "\\" && index < value.length - 2) {
        index += 1;
        parsed += value[index];
        continue;
      }
      parsed += char;
    }
    return parsed;
  }
  if (value.length >= 2 && value.startsWith("'") && value.endsWith("'")) {
    return value.slice(1, -1);
  }
  return value;
}

function envFileContent(config) {
  const values = {
    LEXMOUNT_API_KEY: config.apiKey,
    LEXMOUNT_PROJECT_ID: config.projectId,
    LEXMOUNT_BASE_URL: config.baseUrl,
  };
  const lines = [];
  for (const [key, value] of Object.entries(values)) {
    if (!value) {
      continue;
    }
    assertEnvValueSafe(key, value);
    lines.push(`${key}=${quoteEnvValue(value)}`);
  }
  return `${lines.join("\n")}\n`;
}

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
    const value = parseEnvValue(line.slice(separatorIndex + 1).trim());
    values[key] = value;
  }
  return values;
}

function detectExistingConfig(targetDirs) {
  for (const targetDir of targetDirs) {
    const envPath = path.join(targetDir, ".env");
    if (!fs.existsSync(envPath)) {
      continue;
    }

    const envValues = parseEnvFile(fs.readFileSync(envPath, "utf8"));
    const apiKey = (envValues.LEXMOUNT_API_KEY || "").trim();
    const projectId = (envValues.LEXMOUNT_PROJECT_ID || "").trim();
    const rawBaseUrl = (envValues.LEXMOUNT_BASE_URL || "").trim();
    if (!apiKey || !projectId) {
      continue;
    }

    const region = rawBaseUrl.includes(".com") ? "global" : "china";
    return { apiKey, projectId, rawBaseUrl, region, envPath };
  }
  return null;
}

function maskSecret(value) {
  if (value.length <= 4) {
    return "****";
  }
  return `****${value.slice(-4)}`;
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

function parseTarget(value) {
  const target = (value || "").trim().toLowerCase() || "codex";
  if (!["codex", "claude", "both"].includes(target)) {
    throw new Error("Target must be codex, claude, or both.");
  }
  return target;
}

function nonInteractiveConfig() {
  const enabled = parseBooleanEnv("LEXMOUNT_INSTALL_NONINTERACTIVE");
  if (!enabled) {
    return null;
  }

  const target = parseTarget(process.env.LEXMOUNT_INSTALL_TARGET || "codex");
  const region =
    (process.env.LEXMOUNT_INSTALL_REGION || "").trim().toLowerCase() || "china";
  if (!Object.hasOwn(REGIONS, region)) {
    throw new Error("LEXMOUNT_INSTALL_REGION must be 'china' or 'global'.");
  }

  const apiKey = (process.env.LEXMOUNT_API_KEY || "").trim();
  const projectId = (process.env.LEXMOUNT_PROJECT_ID || "").trim();
  if (!apiKey || !projectId) {
    throw new Error(
      "LEXMOUNT_API_KEY and LEXMOUNT_PROJECT_ID are required in non-interactive mode."
    );
  }

  const bootstrap = parseBooleanEnv("LEXMOUNT_INSTALL_DEPS");
  return {
    target,
    region,
    apiKey,
    projectId,
    baseUrl: REGIONS[region].baseUrl,
    bootstrap: bootstrap ?? true,
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
    streams.output.write("Lexmount browser skill setup\n");
    streams.output.write("Choose install target:\n");
    streams.output.write("  a. Codex (~/.codex/skills)\n");
    streams.output.write("  b. Claude Code (~/.claude/skills)\n");
    streams.output.write("  c. Both\n");

    let targetAnswer = "";
    while (!["a", "b", "c"].includes(targetAnswer)) {
      targetAnswer = (await rl.question("Install target [a/b/c]: "))
        .trim()
        .toLowerCase();
    }
    const target = { a: "codex", b: "claude", c: "both" }[targetAnswer];
    const selectedTargetDirs = targetDirectories(target);

    streams.output.write("\nChoose region preset:\n");
    streams.output.write(
      `  a. ${REGIONS.china.label} (${REGIONS.china.endpointLabel})\n`
    );
    streams.output.write(
      `  b. ${REGIONS.global.label} (${REGIONS.global.endpointLabel})\n`
    );

    let regionAnswer = "";
    while (!["a", "b"].includes(regionAnswer)) {
      regionAnswer = (await rl.question("Region preset [a/b]: "))
        .trim()
        .toLowerCase();
    }

    const region = regionAnswer === "b" ? "global" : "china";
    const regionConfig = REGIONS[region];
    const existingConfig = detectExistingConfig(selectedTargetDirs);

    let apiKey = "";
    let projectId = "";

    if (existingConfig) {
      streams.output.write("\n");
      streams.output.write("Detected existing Lexmount skill configuration.\n");
      streams.output.write(`  File: ${existingConfig.envPath}\n`);
      streams.output.write(
        `  Region preset: ${REGIONS[existingConfig.region].label} (${REGIONS[existingConfig.region].endpointLabel})\n`
      );
      streams.output.write(
        `  LEXMOUNT_API_KEY: ${maskSecret(existingConfig.apiKey)}\n`
      );
      streams.output.write(`  LEXMOUNT_PROJECT_ID: ${existingConfig.projectId}\n`);
      if (existingConfig.rawBaseUrl) {
        streams.output.write(`  LEXMOUNT_BASE_URL: ${existingConfig.rawBaseUrl}\n`);
      }

      const importAnswer = (
        await rl.question("Import this configuration into the installed skill? [Y/n]: ")
      )
        .trim()
        .toLowerCase();

      if (["", "y", "yes"].includes(importAnswer)) {
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

    const bootstrapAnswer = (
      await rl.question("Bootstrap skill-local runtime environment now? [Y/n]: ")
    )
      .trim()
      .toLowerCase();

    return {
      target,
      region,
      apiKey,
      projectId,
      baseUrl: regionConfig.baseUrl,
      bootstrap: ["", "y", "yes"].includes(bootstrapAnswer),
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

function installSkill(targetDir, config) {
  removeDirIfExists(targetDir);
  ensureDir(path.dirname(targetDir));
  copyRecursive(sourceSkillDir, targetDir);
  fs.writeFileSync(path.join(targetDir, ".env"), envFileContent(config), "utf8");

  if (config.bootstrap) {
    runCommand(
      pythonCommand(),
      [path.join(targetDir, "scripts", "bootstrap_runtime.py")],
      targetDir
    );
  }
}

function printHelp() {
  console.log("Install the Lexmount browser skill backed by lex-browser-runtime.");
  console.log("");
  console.log("Usage:");
  console.log("  npx @lexmount/browser-skill-installer");
  console.log("  node tools/install-skill.mjs");
  console.log("");
  console.log("Non-interactive mode:");
  console.log("  Set LEXMOUNT_INSTALL_NONINTERACTIVE=1");
  console.log("  Set LEXMOUNT_API_KEY and LEXMOUNT_PROJECT_ID");
  console.log("  Optional: LEXMOUNT_INSTALL_TARGET=codex|claude|both");
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
    throw new Error(
      "LEXMOUNT_API_KEY and LEXMOUNT_PROJECT_ID are required. If prompts did not appear, rerun this command from an interactive terminal."
    );
  }

  const selectedTargetDirs = targetDirectories(config.target);
  for (const targetDir of selectedTargetDirs) {
    installSkill(targetDir, config);
  }

  console.log("");
  console.log("Installed Lexmount browser skill:");
  for (const targetDir of selectedTargetDirs) {
    console.log(`  ${targetDir}`);
  }
  console.log("");
  console.log("Saved configuration into each installed skill .env file.");
  console.log("");
  console.log("Example command:");
  console.log(
    `  ${path.join(selectedTargetDirs[0], "scripts", "lexmount-browser")} session create`
  );
  console.log("");
  console.log("Restart Codex or Claude Code so the new skill is discovered.");
  finalizeTerminal();
}

main().catch((error) => {
  console.error("Failed to install Lexmount browser skill.");
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
