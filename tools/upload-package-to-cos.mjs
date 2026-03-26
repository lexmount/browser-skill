#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import dotenv from "dotenv";
import COS from "cos-nodejs-sdk-v5";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DIST_DIR = path.join(ROOT, "dist");
const PACKAGE_JSON = JSON.parse(fs.readFileSync(path.join(ROOT, "package.json"), "utf8"));

dotenv.config({ path: path.join(ROOT, ".env") });

const BUCKET = process.env.COS_BUCKET || "npm-1377899528";
const REGION = process.env.COS_REGION || "ap-nanjing";
const PREFIX = process.env.COS_PREFIX || "packages";
const SECRET_ID = process.env.COS_SECRETID;
const SECRET_KEY = process.env.COS_SECRETKEY;

if (!SECRET_ID || !SECRET_KEY) {
  console.error("Missing COS_SECRETID or COS_SECRETKEY in browser-skill/.env");
  process.exit(1);
}

function safeName(pkg) {
  return pkg.replace("@", "").replace("/", "-");
}

function gitCommit() {
  try {
    return execFileSync("git", ["rev-parse", "--short", "HEAD"], {
      cwd: ROOT,
      encoding: "utf8",
    }).trim();
  } catch {
    return "nogit";
  }
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function packTarball() {
  ensureDir(DIST_DIR);

  for (const entry of fs.readdirSync(ROOT)) {
    if (entry.endsWith(".tgz")) {
      fs.rmSync(path.join(ROOT, entry), { force: true });
    }
  }

  execFileSync("npm", ["pack"], {
    cwd: ROOT,
    stdio: "inherit",
    env: {
      ...process.env,
      npm_config_cache: process.env.npm_config_cache || "/tmp/npm-cache",
    },
  });

  const built = fs.readdirSync(ROOT).find((entry) => entry.endsWith(".tgz"));
  if (!built) {
    throw new Error("npm pack did not produce a .tgz file");
  }

  const src = path.join(ROOT, built);
  const dest = path.join(DIST_DIR, built);
  fs.rmSync(dest, { force: true });
  fs.renameSync(src, dest);
  return dest;
}

function copyFile(src, dest) {
  fs.copyFileSync(src, dest);
  return dest;
}

function uploadFile(cos, localPath, key) {
  const body = fs.createReadStream(localPath);
  const size = fs.statSync(localPath).size;

  return new Promise((resolve, reject) => {
    cos.putObject(
      {
        Bucket: BUCKET,
        Region: REGION,
        Key: key,
        Body: body,
        ContentLength: size,
      },
      (err) => {
        if (err) {
          reject(err);
          return;
        }
        resolve(`https://${BUCKET}.cos.${REGION}.myqcloud.com/${key}`);
      },
    );
  });
}

function writeInstallDoc(versionedUrl, latestUrl) {
  const docPath = path.join(ROOT, "INSTALL_FROM_COS.md");
  fs.writeFileSync(
    docPath,
    [
      "# Install Lexmount Browser Skill From COS",
      "",
      "Versioned tarball:",
      "",
      `\`${versionedUrl}\``,
      "",
      "Latest tarball:",
      "",
      `\`${latestUrl}\``,
      "",
      "Example:",
      "",
      "```bash",
      `npx ${latestUrl}`,
      "```",
      "",
      "Fallback:",
      "",
      "```bash",
      "curl -O <latest-url>",
      "npm exec --package ./<downloaded-file>.tgz lexmount-browser-skill-install",
      "```",
      "",
    ].join("\n"),
    "utf8",
  );
  return docPath;
}

async function main() {
  const pkgName = PACKAGE_JSON.name;
  const version = PACKAGE_JSON.version;
  const baseName = safeName(pkgName);
  const timestamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
  const commit = gitCommit();

  const packed = packTarball();
  const versionedName = `${baseName}-${version}-${timestamp}-${commit}.tgz`;
  const latestName = `${baseName}-latest.tgz`;
  const versionedPath = copyFile(packed, path.join(DIST_DIR, versionedName));
  const latestPath = copyFile(packed, path.join(DIST_DIR, latestName));

  const cos = new COS({
    SecretId: SECRET_ID,
    SecretKey: SECRET_KEY,
  });

  const versionedKey = `${PREFIX}/${versionedName}`;
  const latestKey = `${PREFIX}/${latestName}`;

  console.log(`Uploading ${versionedName} ...`);
  const versionedUrl = await uploadFile(cos, versionedPath, versionedKey);

  console.log(`Uploading ${latestName} ...`);
  const latestUrl = await uploadFile(cos, latestPath, latestKey);

  const docPath = writeInstallDoc(versionedUrl, latestUrl);

  console.log("");
  console.log(`Versioned URL: ${versionedUrl}`);
  console.log(`Latest URL: ${latestUrl}`);
  console.log(`Install doc: ${docPath}`);
  console.log("");
  console.log("npx example:");
  console.log(`npx ${latestUrl}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
