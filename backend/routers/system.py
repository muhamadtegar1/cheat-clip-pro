import ipaddress
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from backend.config import _base_dir, logger
from backend.services.system_service import (
    auto_cleanup_expired_files,
    cleanup_expired_temp_files,
    clear_temp_files,
    get_current_git_info,
    get_temp_storage_summary,
    is_server_environment,
    is_update_allowed,
    run_git_command,
    trigger_detached_restart,
)

router = APIRouter(tags=["System"])

# Fork kustom: self-update (git pull + npm/pip install) dan restart via Web UI dimatikan
# agar kustomisasi tidak tertimpa kode repo asli. Update dilakukan manual via git.
# Ubah ke False untuk mengaktifkan kembali perilaku asli.
SELF_UPDATE_DISABLED = True
SELF_UPDATE_DISABLED_MESSAGE = (
    "Self-update dinonaktifkan di fork kustom ini. "
    "Update dilakukan manual via git (git fetch upstream lalu merge ke branch custom)."
)


LOCAL_ORIGIN_RE = re.compile(r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$", re.IGNORECASE)


def _configured_admin_key() -> str:
    return (os.environ.get("ADMIN_API_KEY") or os.environ.get("CHEAT_CLIP_API_KEY") or "").strip()


def _provided_admin_key(x_api_key: Optional[str], authorization: Optional[str]) -> str:
    provided = (x_api_key or "").strip()
    if not provided and authorization and authorization.startswith("Bearer "):
        provided = authorization[7:].strip()
    return provided


def _is_loopback_client(request: Request) -> bool:
    host = request.client.host if request.client else ""
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


def verify_admin_access(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
) -> bool:
    """
    Verifies administrative authorization.
    If ADMIN_API_KEY or CHEAT_CLIP_API_KEY is configured in .env, requires matching token.
    Without a key, only requests from this computer (loopback client, no foreign Origin) are allowed,
    so other devices on the network and other websites cannot call admin endpoints.
    """
    admin_key = _configured_admin_key()
    if admin_key:
        if _provided_admin_key(x_api_key, authorization) != admin_key:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing administrator API key")
        return True

    if not _is_loopback_client(request):
        raise HTTPException(status_code=403, detail="Forbidden: admin endpoints are only available from this computer")
    origin = request.headers.get("origin")
    if origin and not LOCAL_ORIGIN_RE.match(origin.strip()):
        raise HTTPException(status_code=403, detail="Forbidden: cross-origin admin request rejected")
    return True


def require_admin_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
) -> bool:
    """Update/restart always require ADMIN_API_KEY, even for local requests."""
    admin_key = _configured_admin_key()
    if not admin_key:
        raise HTTPException(status_code=403, detail="Forbidden: set ADMIN_API_KEY in .env to use update/restart")
    if _provided_admin_key(x_api_key, authorization) != admin_key:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing administrator API key")
    return True


# ── Gemini API key stored by the backend (backend/.env), never returned in full ──
# backend/.env (not the root .env): Vite restarts and reloads the page whenever the root .env changes.
# config.py loads backend/.env first, so a key saved here wins over the root .env.
GEMINI_KEY_NAME = "GEMINI_API_KEY"
GEMINI_KEY_ENV_PATH = Path(_base_dir) / ".env"
_GEMINI_KEY_LINE_RE = re.compile(r"^\s*(export\s+)?" + GEMINI_KEY_NAME + r"\s*=")
_GEMINI_KEY_VALID_RE = re.compile(r"^[A-Za-z0-9_\-.]{4,200}$")


class GeminiKeyPayload(BaseModel):
    api_key: str


def _read_env_lines() -> tuple:
    path = Path(GEMINI_KEY_ENV_PATH)
    if not path.exists():
        return [], "\n"
    text = path.read_bytes().decode("utf-8")  # keep CRLF/LF as-is
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.splitlines(), newline


def _write_env_lines(lines: list, newline: str) -> None:
    path = Path(GEMINI_KEY_ENV_PATH)
    content = newline.join(lines) + (newline if lines else "")
    path.write_text(content, encoding="utf-8", newline="")


def _gemini_key_status() -> dict:
    key = (os.environ.get(GEMINI_KEY_NAME) or "").strip()
    if not key:
        return {"configured": False, "source": None, "hint": "", "is_mock": False}
    in_file = any(_GEMINI_KEY_LINE_RE.match(line) for line in _read_env_lines()[0])
    is_mock = key.lower() == "mock"
    hint = "mock" if is_mock else (key[-4:] if len(key) >= 12 else "")
    return {"configured": True, "source": "file" if in_file else "env", "hint": hint, "is_mock": is_mock}


@router.get("/api/settings/gemini-key")
def get_gemini_key_status(authorized: bool = Depends(verify_admin_access)):
    """Returns whether a Gemini key is stored, plus its last 4 characters. Never the full key."""
    return _gemini_key_status()


@router.put("/api/settings/gemini-key")
def save_gemini_key(payload: GeminiKeyPayload, authorized: bool = Depends(verify_admin_access)):
    """Stores the Gemini key in backend/.env (other lines untouched) and activates it immediately."""
    key = (payload.api_key or "").strip()
    if not _GEMINI_KEY_VALID_RE.match(key):
        raise HTTPException(status_code=400, detail="Invalid Gemini API key format")
    lines, newline = _read_env_lines()
    new_line = f"{GEMINI_KEY_NAME}={key}"
    replaced = False
    out = []
    for line in lines:
        if _GEMINI_KEY_LINE_RE.match(line):
            if not replaced:
                out.append(new_line)
                replaced = True
            continue
        out.append(line)
    if not replaced:
        out.append(new_line)
    try:
        _write_env_lines(out, newline)
    except OSError as e:
        logger.error(f"Failed to write Gemini key to .env: {e}")
        raise HTTPException(status_code=500, detail="Failed to save the key to .env")
    os.environ[GEMINI_KEY_NAME] = key
    return _gemini_key_status()


@router.delete("/api/settings/gemini-key")
def delete_gemini_key(authorized: bool = Depends(verify_admin_access)):
    """Removes the Gemini key from backend/.env and from the running process."""
    lines, newline = _read_env_lines()
    out = [line for line in lines if not _GEMINI_KEY_LINE_RE.match(line)]
    if len(out) != len(lines):
        try:
            _write_env_lines(out, newline)
        except OSError as e:
            logger.error(f"Failed to remove Gemini key from .env: {e}")
            raise HTTPException(status_code=500, detail="Failed to remove the key from .env")
    os.environ.pop(GEMINI_KEY_NAME, None)
    return _gemini_key_status()


@router.get("/api/temp-storage-info")
async def get_temp_storage_info():
    """Returns total files, bytes, and formatted size of temp download storage."""
    return get_temp_storage_summary()


@router.post("/api/clear-temp")
async def clear_temp_folder(authorized: bool = Depends(verify_admin_access)):
    """
    Clears all temporary downloaded video clips, audio slices, ASS files, and frames
    from TEMP_DIR and backend/temp. Re-creates empty directories.
    PROTECTED: cookies.txt and any cookie files are strictly PRESERVED and NEVER deleted.
    """
    if not is_update_allowed():
        raise HTTPException(
            status_code=403,
            detail="Manual server-side cache clearing is disabled in server mode for safety. Background auto-cleanup manages server storage automatically."
        )
    return clear_temp_files()


@router.post("/api/cleanup-expired-temp")
async def cleanup_expired_temp(max_age_hours: int = 1, authorized: bool = Depends(verify_admin_access)):
    """Deletes temporary frame images and slices older than max_age_hours."""
    return cleanup_expired_temp_files(max_age_hours=max_age_hours)


@router.post("/api/auto-cleanup")
async def api_trigger_auto_cleanup(
    max_age_seconds: int = 3600,
    max_storage_gb: float = 5.0,
    authorized: bool = Depends(verify_admin_access)
):
    """Manually triggers dual-mode auto-cleanup (Option 1: TTL + Option 2: Quota)."""
    return auto_cleanup_expired_files(
        max_age_seconds=max_age_seconds,
        max_storage_bytes=int(max_storage_gb * 1024 * 1024 * 1024)
    )


@router.get("/api/system/version")
def api_system_version():
    """Returns local git version and environment update permission information."""
    return get_current_git_info()


@router.get("/api/system/check-update")
def api_check_update():
    """Fetches origin and checks if updates are available. Disabled in server environments for security."""
    info = get_current_git_info()
    if SELF_UPDATE_DISABLED:
        return {
            **info,
            "update_available": False,
            "behind_count": 0,
            "changelog": [],
            "allow_update": False,
            "message": SELF_UPDATE_DISABLED_MESSAGE
        }
    if not is_update_allowed():
        return {
            **info,
            "update_available": False,
            "behind_count": 0,
            "changelog": [],
            "is_server": True,
            "allow_update": False,
            "message": "Self-update is disabled in server / Docker environment for security. Please update through your orchestrator (e.g. Dokploy / Git)."
        }

    root_dir = Path(_base_dir).parent
    branch = info.get("branch", "master") or "master"

    # Fetch origin
    rc_fetch, _, err_fetch = run_git_command(["fetch", "origin", branch], cwd=root_dir, timeout=20)
    if rc_fetch != 0:
        return {
            **info,
            "update_available": False,
            "behind_count": 0,
            "changelog": [],
            "error": f"Failed to fetch updates from remote: {err_fetch or 'Network or remote error'}"
        }

    # Count commits behind
    rc_count, count_str, _ = run_git_command(["rev-list", "--count", "HEAD..FETCH_HEAD"], cwd=root_dir)
    behind_count = int(count_str) if rc_count == 0 and count_str.isdigit() else 0

    # Get changelog of new commits
    changelog = []
    if behind_count > 0:
        rc_log, log_str, _ = run_git_command(["log", "HEAD..FETCH_HEAD", "--pretty=format:%h|%s|%cd", "--date=short"], cwd=root_dir)
        if rc_log == 0 and log_str:
            for line in log_str.splitlines():
                p = line.strip().split("|")
                if len(p) >= 3:
                    changelog.append({"hash": p[0], "message": p[1], "date": p[2]})

    rc_remote_commit, remote_commit, _ = run_git_command(["rev-parse", "--short", "FETCH_HEAD"], cwd=root_dir)

    return {
        **info,
        "update_available": behind_count > 0,
        "behind_count": behind_count,
        "remote_commit": remote_commit if rc_remote_commit == 0 else info["current_commit"],
        "changelog": changelog
    }


@router.post("/api/system/update")
async def api_perform_update(authorized: bool = Depends(require_admin_key)):
    """Pulls latest code, syncs dependencies if modified, and triggers background restart."""
    if SELF_UPDATE_DISABLED:
        raise HTTPException(status_code=403, detail=SELF_UPDATE_DISABLED_MESSAGE)
    if not is_update_allowed():
        raise HTTPException(
            status_code=403,
            detail="System self-update via Web UI is disabled in server / Docker environment for security. Please update through your server orchestrator (e.g. Dokploy / Git pull)."
        )

    root_dir = Path(_base_dir).parent
    info = get_current_git_info()
    branch = info.get("branch", "master") or "master"
    old_head = info.get("current_commit_full", "HEAD")

    # 1. Fetch latest
    rc_fetch, _, err_fetch = run_git_command(["fetch", "origin", branch], cwd=root_dir, timeout=25)
    if rc_fetch != 0:
        raise HTTPException(status_code=500, detail=f"Failed to fetch updates: {err_fetch}")

    # 2. Check if working tree has tracked changes
    rc_status, status_out, _ = run_git_command(["status", "--porcelain"], cwd=root_dir)
    has_local_changes = False
    if rc_status == 0 and status_out:
        for line in status_out.splitlines():
            if not line.startswith("??"):
                has_local_changes = True
                break

    if has_local_changes:
        logger.info("Local changes detected. Stashing before update...")
        run_git_command(["stash", "save", "Auto-stash before Cheat Clip PRO update"], cwd=root_dir)

    # 3. Pull latest changes
    rc_pull, pull_out, err_pull = run_git_command(["pull", "origin", branch], cwd=root_dir, timeout=40)
    if rc_pull != 0:
        if has_local_changes:
            run_git_command(["stash", "pop"], cwd=root_dir)
        raise HTTPException(status_code=500, detail=f"Git pull failed: {err_pull or pull_out}")

    if has_local_changes:
        logger.info("Reapplying stashed local changes...")
        run_git_command(["stash", "pop"], cwd=root_dir)

    # 4. Check what files changed between old_head and new HEAD
    rc_diff, diff_files, _ = run_git_command(["diff", f"{old_head}..HEAD", "--name-only"], cwd=root_dir)
    changed_files = diff_files.splitlines() if rc_diff == 0 and diff_files else []

    updated_deps = []
    # If package.json changed, run npm install
    if "package.json" in changed_files:
        logger.info("package.json changed. Running npm install...")
        try:
            import shutil
            npm_bin = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
            subprocess.run([npm_bin, "install"], shell=False, cwd=str(root_dir), timeout=120)
            updated_deps.append("Node modules (npm install)")
        except Exception as e:
            logger.warning(f"npm install warning: {e}")

    # If requirements.txt changed, run pip install
    if any("requirements.txt" in f for f in changed_files):
        logger.info("requirements.txt changed. Running pip install...")
        try:
            req_file = root_dir / "backend" / "requirements.txt"
            if not req_file.exists():
                req_file = root_dir / "requirements.txt"
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)], shell=False, cwd=str(root_dir), timeout=180)
            updated_deps.append("Python dependencies (pip install)")
        except Exception as e:
            logger.warning(f"pip install warning: {e}")

    # 5. Trigger detached restart runner
    trigger_detached_restart(delay=2.5)

    new_info = get_current_git_info()
    return {
        "success": True,
        "status": "restarting",
        "previous_commit": info["current_commit"],
        "new_commit": new_info["current_commit"],
        "updated_deps": updated_deps,
        "message": "Cheat Clip PRO has been updated successfully. Server is restarting in background..."
    }


@router.post("/api/system/restart")
async def api_restart_app(authorized: bool = Depends(require_admin_key)):
    """Triggers an immediate background restart without pulling code. Disabled in server environments for security."""
    if SELF_UPDATE_DISABLED:
        raise HTTPException(status_code=403, detail=SELF_UPDATE_DISABLED_MESSAGE)
    if not is_update_allowed():
        raise HTTPException(
            status_code=403,
            detail="Server restarts via Web UI are disabled in server / Docker environment for security."
        )
    trigger_detached_restart(delay=2.5)
    return {
        "success": True,
        "status": "restarting",
        "message": "Cheat Clip PRO is restarting..."
    }
