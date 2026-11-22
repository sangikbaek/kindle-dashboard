#!/bin/sh
# 대시보드 시작: 스크립트를 /tmp로 복사해서 실행 (USB 연결로 /mnt/us가 내려가도 계속 돌도록)
EXT=/mnt/us/extensions/weatherdash
PIDF=/tmp/weatherdash.pid

if [ -f "$PIDF" ] && kill -0 "$(cat $PIDF)" 2>/dev/null; then
  exit 0
fi

cp "$EXT/bin/dash.sh" /tmp/weatherdash.sh
cp "$EXT/config.sh" /tmp/weatherdash.conf
# 저장소에 로그 사본을 남겨 PC에서 볼 수 있게
cp /tmp/weatherdash.log "$EXT/last.log" 2>/dev/null

setsid sh /tmp/weatherdash.sh > /dev/null 2>&1 < /dev/null &
exit 0
