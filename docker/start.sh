#!/bin/sh
set -eu

if [ "${SHUGUANG_NOTE_REMOTE_BROWSER:-true}" = "true" ]; then
  export DISPLAY="${DISPLAY:-:99}"
  SCREEN_SIZE="${SHUGUANG_NOTE_SCREEN_SIZE:-1280x900x24}"
  VNC_PORT="${SHUGUANG_NOTE_VNC_PORT:-5900}"
  NOVNC_PORT="${SHUGUANG_NOTE_NOVNC_PORT:-6080}"

  Xvfb "$DISPLAY" -screen 0 "$SCREEN_SIZE" -nolisten tcp >/tmp/xvfb.log 2>&1 &
  fluxbox >/tmp/fluxbox.log 2>&1 &

  if [ -n "${SHUGUANG_NOTE_VNC_PASSWORD:-}" ]; then
    x11vnc -display "$DISPLAY" -forever -shared -rfbport "$VNC_PORT" -passwd "$SHUGUANG_NOTE_VNC_PASSWORD" >/tmp/x11vnc.log 2>&1 &
  else
    x11vnc -display "$DISPLAY" -forever -shared -rfbport "$VNC_PORT" -nopw >/tmp/x11vnc.log 2>&1 &
  fi

  websockify --web=/usr/share/novnc/ "0.0.0.0:${NOVNC_PORT}" "127.0.0.1:${VNC_PORT}" >/tmp/novnc.log 2>&1 &
fi

exec uv run --no-sync python -m backend.app
