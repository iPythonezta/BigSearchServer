"""
Utility: copy frontend production build into backend `dist/` folder.

Usage:
    python sync_frontend_build.py

It copies from `frontend/dist/` → `dist/` (backend root).
"""

import os
import shutil
import sys


def main() -> int:
    # Absolute path to backend root (where this script lives)
    repo_root = os.path.dirname(os.path.abspath(__file__))

    # Frontend build path (frontend is INSIDE backend root)
    frontend_build = os.path.join(repo_root, "frontend", "dist")
    frontend_build = os.path.normpath(frontend_build)

    # Backend dist folder
    backend_dist = os.path.join(repo_root, "dist")

    # Sanity checks
    if not os.path.isdir(os.path.join(repo_root, "frontend")):
        print("ERROR: 'frontend/' folder not found next to this script.")
        return 1

    if not os.path.exists(frontend_build):
        print(
            f"ERROR: Frontend build not found at:\n  {frontend_build}\n"
            "Run `npm run build` inside the frontend directory first."
        )
        return 1

    # Remove existing backend dist if present
    if os.path.exists(backend_dist):
        shutil.rmtree(backend_dist)

    # Copy frontend dist → backend dist
    shutil.copytree(frontend_build, backend_dist)

    print("✓ Frontend build synced successfully")
    print(f"  Source: {frontend_build}")
    print(f"  Target: {backend_dist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
