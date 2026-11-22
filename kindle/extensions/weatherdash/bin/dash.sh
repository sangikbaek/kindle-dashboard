#!/bin/sh
# 날씨 대시보드 메인 루프 (/tmp/weatherdash.sh 로 복사되어 실행됨)
. /tmp/weatherdash.conf

LOG=/tmp/weatherdash.log
PNG=/tmp/weatherdash.png
STOPF=/tmp/weatherdash.stop
PIDF=/tmp/weatherdash.pid
WATCH_PIDS=""

echo $$ > "$PIDF"
rm -f "$STOPF"

log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }

cleanup() {
  for p in $WATCH_PIDS; do kill "$p" 2>/dev/null; done
  killall dd 2>/dev/null
  lipc-set-prop com.lab126.powerd preventScreenSaver 0
  rm -f "$PIDF" "$STOPF"
  log "stopped"
  if [ "$STOP_GUI" = "1" ]; then
    eips -c
    eips 10 35 "Restarting Kindle UI..."
    start lab126_gui
  fi
  exit 0
}
trap cleanup TERM INT

wifi_up() {
  [ "$(lipc-get-prop com.lab126.wifid cmState 2>/dev/null)" = "CONNECTED" ] && return 0
  lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
  i=0
  while [ $i -lt 30 ]; do
    [ "$(lipc-get-prop com.lab126.wifid cmState 2>/dev/null)" = "CONNECTED" ] && return 0
    sleep 2
    i=$((i + 1))
  done
  log "wifi not connected"
  return 1
}

fetch() {
  u="$URL?t=$(date +%s)"   # 캐시 우회
  rm -f "$PNG"
  if command -v curl > /dev/null 2>&1; then
    curl -s -f -m 40 -o "$PNG" "$u"
  else
    wget -q -O "$PNG" "$u"
  fi
  [ -s "$PNG" ]
}

# 화면 터치(또는 버튼) 입력이 들어오면 종료 플래그 생성
start_watchers() {
  for ev in /dev/input/event*; do
    ( dd if="$ev" bs=64 count=1 of=/dev/null 2>/dev/null && touch "$STOPF" ) &
    WATCH_PIDS="$WATCH_PIDS $!"
  done
}

log "start (url=$URL interval=$INTERVAL stop_gui=$STOP_GUI)"
lipc-set-prop com.lab126.powerd preventScreenSaver 1

if [ "$STOP_GUI" = "1" ]; then
  stop lab126_gui
  sleep 3
  eips -c
  eips 10 35 "Weather dashboard loading..."
fi

first=1
while true; do
  if wifi_up && fetch; then
    eips -f -g "$PNG"
    bat=$(lipc-get-prop com.lab126.powerd battLevel 2>/dev/null)
    if [ -n "$bat" ] && [ "$bat" -lt 20 ]; then
      eips 1 1 "Battery low: ${bat}%"
    fi
    log "updated (battery ${bat}%)"
    wait_sec=$INTERVAL
  else
    log "fetch failed"
    eips 1 1 "Update failed $(date '+%H:%M'), retry in 1 min"
    wait_sec=60
  fi

  if [ -n "$first" ]; then
    sleep 3
    start_watchers
    first=""
  fi

  n=0
  while [ $n -lt "$wait_sec" ]; do
    [ -f "$STOPF" ] && cleanup
    sleep 2
    n=$((n + 2))
  done
done
