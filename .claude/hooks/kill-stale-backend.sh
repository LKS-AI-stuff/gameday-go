#!/bin/bash
# Stop hook: kill local backend processes that are running stale code or settings.
#
# - API (uvicorn on :8000). Started with --reload, it reloads itself on .py changes but not on
#   .env, pyproject.toml or uv.lock changes, so only those count as stale. Started without
#   --reload, a changed backend .py file counts too.
# - Worker (`python -m app.main_worker`, from M4). It never reloads, so any of these count.
#
# A process is killed only when one of those files changed AFTER it started (comparing with
# `git status` alone would kill servers after every turn). Expo dev servers are left alone:
# they hot-reload.

cd "$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

# Process start time (epoch seconds) from ps's [[dd-]hh:]mm:ss elapsed time.
started_at() {
  local ETIME DAYS=0 A B C H M S
  ETIME=$(ps -o etime= -p "$1" 2>/dev/null | tr -d ' ')
  [ -z "$ETIME" ] && return 1
  [[ "$ETIME" == *-* ]] && { DAYS=${ETIME%%-*}; ETIME=${ETIME#*-}; }
  IFS=: read -r A B C <<< "$ETIME"
  if [ -n "$C" ]; then H=$A; M=$B; S=$C; else H=0; M=$A; S=$B; fi
  echo $(( $(date +%s) - (10#$DAYS*86400 + 10#$H*3600 + 10#$M*60 + 10#$S) ))
}

# Files whose change always makes a running backend stale (settings and dependencies).
settings_files() {
  printf '%s\n' .env
  git ls-files -m -o --exclude-standard -- 'backend/pyproject.toml' 'backend/uv.lock' 2>/dev/null
}

# Backend source files (modified or untracked; ignored paths such as .venv excluded).
source_files() {
  git ls-files -m -o --exclude-standard -- 'backend/*.py' 2>/dev/null
}

# kill_if_stale PID NAME INCLUDE_SOURCES(0|1)
kill_if_stale() {
  local PID=$1 NAME=$2 WITH_SOURCES=$3 STARTED NEWER=""
  STARTED=$(started_at "$PID") || return 0
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    if [ "$(stat -f %m "$f" 2>/dev/null)" -gt "$STARTED" ]; then NEWER="$f"; break; fi
  done < <(settings_files; [ "$WITH_SOURCES" = 1 ] && source_files)

  if [ -n "$NEWER" ]; then
    echo "gameday-go stop-hook: $NEWER changed after the $NAME (pid $PID) started, so it is running stale code or settings; killing it. Restart it to pick up the change." >&2
    kill "$PID" 2>/dev/null
    sleep 1
    kill -9 "$PID" 2>/dev/null
  fi
}

for API_PID in $(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null); do
  CMD=$(ps -o command= -p "$API_PID" 2>/dev/null)
  [[ "$CMD" == *uvicorn* || "$CMD" == *python* ]] || continue  # leave non-backend listeners alone
  if [[ "$CMD" == *--reload* ]]; then
    kill_if_stale "$API_PID" "API on :8000 (--reload)" 0
  else
    kill_if_stale "$API_PID" "API on :8000" 1
  fi
done

for WORKER_PID in $(pgrep -f 'app\.main_worker' 2>/dev/null); do
  kill_if_stale "$WORKER_PID" "worker" 1
done

exit 0
