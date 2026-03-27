"""arezzo init — setup wizard and platform config generation."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "arezzo"
CREDENTIALS_DEST = CONFIG_DIR / "credentials.json"
TOKEN_DEST = CONFIG_DIR / "token.json"


# ── Platform config templates ────────────────────────────────────────────

def _claude_code_config() -> dict:
    return {"mcpServers": {"arezzo": {"command": "arezzo"}}}


def _cursor_config() -> dict:
    return {"mcpServers": {"arezzo": {"command": "arezzo"}}}


def _vscode_config() -> dict:
    return {"servers": {"arezzo": {"type": "stdio", "command": "arezzo"}}}


# ── Config generation ────────────────────────────────────────────────────

def generate_platform_configs(target_dir: Path) -> list[str]:
    """Write platform config files to target_dir. Returns list of written paths."""
    written = []

    # Claude Code (.mcp.json in project root)
    p = target_dir / ".mcp.json"
    p.write_text(json.dumps(_claude_code_config(), indent=2) + "\n")
    written.append(str(p))

    # Cursor (.cursor/mcp.json)
    cursor_dir = target_dir / ".cursor"
    cursor_dir.mkdir(exist_ok=True)
    p = cursor_dir / "mcp.json"
    p.write_text(json.dumps(_cursor_config(), indent=2) + "\n")
    written.append(str(p))

    # VS Code (.vscode/mcp.json)
    vscode_dir = target_dir / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    p = vscode_dir / "mcp.json"
    p.write_text(json.dumps(_vscode_config(), indent=2) + "\n")
    written.append(str(p))

    return written


def _claude_desktop_path() -> Path:
    """Return the Claude Desktop config path for this platform."""
    import platform
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    # Linux
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


# ── Init wizard ─────────────────────────────────────────────────────────

def run_init():
    """Interactive setup wizard for Arezzo."""
    print("Arezzo Setup\n")

    # ── Step 1: Credentials ──────────────────────────────────────────────
    if CREDENTIALS_DEST.exists():
        print(f"  credentials.json found at {CREDENTIALS_DEST}")
    else:
        print("  credentials.json not found at ~/.config/arezzo/credentials.json")
        print()
        print("  To get credentials.json:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create an OAuth 2.0 client ID (Desktop application)")
        print("  3. Download the JSON file")
        print()
        src_input = input("  Path to your credentials.json: ").strip()
        src = Path(src_input).expanduser()

        if not src.exists():
            print(f"  Error: file not found: {src}", file=sys.stderr)
            sys.exit(1)

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, CREDENTIALS_DEST)
        print(f"  Copied to {CREDENTIALS_DEST}")

    # ── Step 2: OAuth token ──────────────────────────────────────────────
    print()
    if TOKEN_DEST.exists():
        print("  OAuth token already present — skipping authorization flow.")
    else:
        print("  Running OAuth authorization flow (browser will open)...")
        try:
            from arezzo.auth import get_credentials
            get_credentials()
            print(f"  Token saved to {TOKEN_DEST}")
        except Exception as e:
            print(f"  Error during authorization: {e}", file=sys.stderr)
            sys.exit(1)

    # ── Step 3: Platform configs ─────────────────────────────────────────
    print()
    cwd = Path.cwd()
    answer = input(f"  Generate platform config files in {cwd}? [Y/n] ").strip().lower()
    if answer in ("", "y", "yes"):
        written = generate_platform_configs(cwd)
        print()
        for path in written:
            print(f"  Wrote {path}")

        # Claude Desktop — print instructions, don't write automatically
        desktop_path = _claude_desktop_path()
        print()
        print("  For Claude Desktop, add this to:")
        print(f"  {desktop_path}")
        print()
        print('  "mcpServers": {')
        print('    "arezzo": {')
        print('      "command": "arezzo"')
        print('    }')
        print('  }')

    # ── Done ─────────────────────────────────────────────────────────────
    print()
    print("Setup complete. Test with: arezzo (runs the MCP server on stdio)")
    print()
    print("In your MCP client, Arezzo exposes three tools:")
    print("  read_document(document_id)             — see document structure")
    print("  edit_document(document_id, operations) — compile + execute changes")
    print("  validate_operations(document_id, ops)  — dry-run compile only")
