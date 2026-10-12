#!/bin/bash
# Installs yt-dlp for the watch plugin in ephemeral cloud sessions.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
command -v yt-dlp >/dev/null 2>&1 || pip install -q yt-dlp
