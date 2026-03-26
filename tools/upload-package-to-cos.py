#!/usr/bin/env python3
"""
Build the browser-skill npm tarball and upload it to Tencent COS.
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
PACKAGE_JSON = ROOT / "package.json"
DIST_DIR = ROOT / "dist"

load_dotenv(ROOT / ".env")

BUCKET = os.getenv("COS_BUCKET", "npm-1377899528")
REGION = os.getenv("COS_REGION", "ap-nanjing")
PREFIX = os.getenv("COS_PREFIX", "packages")


def print_step(message: str) -> None:
    print(message)


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        fail(f"Missing required environment variable: {name}")
    return value


def ensure_cos_sdk() -> None:
    try:
        import qcloud_cos  # noqa: F401
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "cos-python-sdk-v5"],
            check=True,
        )


def load_package_meta() -> tuple[str, str]:
    data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    return data["name"], data["version"]


def npm_safe_name(package_name: str) -> str:
    return package_name.replace("@", "").replace("/", "-")


def git_commit_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "nogit"


def build_tarball() -> Path:
    DIST_DIR.mkdir(exist_ok=True)

    for tgz in glob.glob(str(ROOT / "*.tgz")):
        os.remove(tgz)

    env = os.environ.copy()
    env["npm_config_cache"] = env.get("npm_config_cache", "/tmp/npm-cache")

    subprocess.run(
        ["npm", "pack"],
        cwd=ROOT,
        check=True,
        env=env,
    )

    tgz_files = list(ROOT.glob("*.tgz"))
    if len(tgz_files) != 1:
        fail("Expected exactly one .tgz file after npm pack")

    built = tgz_files[0]
    target = DIST_DIR / built.name
    if target.exists():
        target.unlink()
    shutil.move(str(built), str(target))
    return target


def prepare_versioned_copy(tarball: Path, package_name: str, version: str) -> tuple[Path, str]:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    commit = git_commit_hash()
    file_name = f"{npm_safe_name(package_name)}-{version}-{timestamp}-{commit}.tgz"
    target = tarball.with_name(file_name)
    shutil.copy2(tarball, target)
    return target, file_name


def upload_file(local_path: Path, key: str, secret_id: str, secret_key: str) -> str:
    from qcloud_cos import CosConfig, CosS3Client

    config = CosConfig(Region=REGION, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(config)

    with local_path.open("rb") as fp:
        client.put_object(
            Bucket=BUCKET,
            Body=fp,
            Key=key,
            EnableMD5=False,
        )

    return f"https://{BUCKET}.cos.{REGION}.myqcloud.com/{key}"


def write_install_doc(versioned_url: str, latest_url: str) -> Path:
    doc = ROOT / "INSTALL_FROM_COS.md"
    doc.write_text(
        "\n".join(
            [
                "# Install Lexmount Browser Skill From COS",
                "",
                "Versioned tarball:",
                "",
                f"`{versioned_url}`",
                "",
                "Latest tarball:",
                "",
                f"`{latest_url}`",
                "",
                "Example:",
                "",
                "```bash",
                f"npx {latest_url}",
                "```",
                "",
                "If `npx <url>` is not accepted by the local npm version, download the tarball first and run:",
                "",
                "```bash",
                "npm exec --package <downloaded-tgz> lexmount-browser-skill-install",
                "```",
            ]
        ),
        encoding="utf-8",
    )
    return doc


def main() -> None:
    secret_id = require_env("COS_SECRETID")
    secret_key = require_env("COS_SECRETKEY")

    print_step("Checking COS SDK...")
    ensure_cos_sdk()

    package_name, version = load_package_meta()
    print_step(f"Packing npm package {package_name}@{version} ...")
    tarball = build_tarball()

    print_step("Preparing versioned artifact ...")
    versioned_tarball, versioned_name = prepare_versioned_copy(tarball, package_name, version)

    latest_name = f"{npm_safe_name(package_name)}-latest.tgz"
    latest_tarball = DIST_DIR / latest_name
    shutil.copy2(tarball, latest_tarball)

    versioned_key = f"{PREFIX}/{versioned_name}"
    latest_key = f"{PREFIX}/{latest_name}"

    print_step(f"Uploading {versioned_name} ...")
    versioned_url = upload_file(versioned_tarball, versioned_key, secret_id, secret_key)

    print_step(f"Uploading {latest_name} ...")
    latest_url = upload_file(latest_tarball, latest_key, secret_id, secret_key)

    doc = write_install_doc(versioned_url, latest_url)

    print()
    print("Upload complete.")
    print(f"Versioned URL: {versioned_url}")
    print(f"Latest URL:    {latest_url}")
    print(f"Install doc:   {doc}")
    print()
    print("npx example:")
    print(f"npx {latest_url}")


if __name__ == "__main__":
    main()
