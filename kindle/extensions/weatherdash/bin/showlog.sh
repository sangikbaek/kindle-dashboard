#!/bin/sh
# 최근 로그를 화면 아래쪽에 표시 + 저장소에 복사
cp /tmp/weatherdash.log /mnt/us/extensions/weatherdash/last.log 2>/dev/null
row=30
tail -n 8 /tmp/weatherdash.log 2>/dev/null | while read -r line; do
  eips 1 $row "$(echo "$line" | cut -c1-48)"
  row=$((row + 1))
done
exit 0
