"""킨들 Paperwhite 4용 날씨/미세먼지 대시보드 이미지 생성기.

데이터: Open-Meteo (무료, API 키 불필요)
출력: 1072x1448 8bit 그레이스케일 PNG
"""
import json
import math
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

# ---- 설정 -------------------------------------------------------------
LAT, LON = 37.5124, 126.9393          # 서울 동작구
PLACE = "서울 동작구"
TZ = "Asia/Seoul"
W, H = 1072, 1448                      # Paperwhite 4 세로 해상도

# 폰트: GitHub Actions(우분투)에서는 나눔고딕, 윈도우 미리보기에서는 맑은 고딕
_FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"),
    (r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\malgunbd.ttf"),
]
FONT_REG, FONT_BOLD = next((r, b) for r, b in _FONT_CANDIDATES if Path(r).exists())


def now_kst():
    """서울 기준 현재 시각 (API 시간과 비교하기 위해 tz 정보는 제거)"""
    return datetime.now(ZoneInfo(TZ)).replace(tzinfo=None)

BLACK, DARK, MID, LIGHT, WHITE = 0, 70, 130, 200, 255

WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def font(size, bold=False):
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size)


# ---- 데이터 -------------------------------------------------------------
def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "kindle-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def get_data():
    weather = fetch_json(
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}&timezone={TZ}&forecast_days=7"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        "weather_code,wind_speed_10m,is_day"
        "&hourly=temperature_2m,precipitation_probability,weather_code,is_day"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,sunrise,sunset"
        "&wind_speed_unit=ms"
    )
    air = fetch_json(
        "https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={LAT}&longitude={LON}&timezone={TZ}"
        "&current=pm10,pm2_5"
    )
    return weather, air


# ---- 날씨 코드 (WMO) -----------------------------------------------------
def describe(code):
    if code == 0: return "맑음", "clear"
    if code == 1: return "대체로 맑음", "mostly_clear"
    if code == 2: return "구름 조금", "partly"
    if code == 3: return "흐림", "cloudy"
    if code in (45, 48): return "안개", "fog"
    if 51 <= code <= 57: return "이슬비", "rain"
    if 61 <= code <= 67: return "비", "rain"
    if 71 <= code <= 77: return "눈", "snow"
    if 80 <= code <= 82: return "소나기", "rain"
    if code in (85, 86): return "눈 소나기", "snow"
    if code >= 95: return "뇌우", "storm"
    return "-", "cloudy"


# 한국 환경부 기준
def grade_pm10(v):
    if v is None: return "-"
    return "좋음" if v <= 30 else "보통" if v <= 80 else "나쁨" if v <= 150 else "매우나쁨"


def grade_pm25(v):
    if v is None: return "-"
    return "좋음" if v <= 15 else "보통" if v <= 35 else "나쁨" if v <= 75 else "매우나쁨"


# ---- 아이콘 (도형으로 직접 그림) ------------------------------------------
def draw_sun(d, cx, cy, r, w):
    d.ellipse([cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5], outline=BLACK, width=w)
    for i in range(8):
        a = math.pi / 4 * i
        d.line([cx + math.cos(a) * r * 0.68, cy + math.sin(a) * r * 0.68,
                cx + math.cos(a) * r * 0.95, cy + math.sin(a) * r * 0.95], fill=BLACK, width=w)


def draw_moon(d, cx, cy, r, w):
    d.ellipse([cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6], fill=BLACK)
    d.ellipse([cx - r * 0.3, cy - r * 0.8, cx + r * 0.8, cy + r * 0.3], fill=WHITE)


def draw_cloud(d, cx, cy, r, w, fill=WHITE):
    parts = [
        (cx - r * 0.45, cy + r * 0.05, r * 0.38),
        (cx + r * 0.05, cy - r * 0.2, r * 0.5),
        (cx + r * 0.5, cy + r * 0.1, r * 0.33),
    ]
    for x, y, rr in parts:  # 외곽선
        d.ellipse([x - rr - w, y - rr - w, x + rr + w, y + rr + w], fill=BLACK)
    d.rectangle([cx - r * 0.45 - w, cy + r * 0.05, cx + r * 0.5 + w, cy + r * 0.43 + w], fill=BLACK)
    for x, y, rr in parts:  # 내부
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=fill)
    d.rectangle([cx - r * 0.45, cy + r * 0.05, cx + r * 0.5, cy + r * 0.43], fill=fill)


def draw_drop(d, x, y, h, fill=DARK):
    """(x, y) = 물방울 꼭대기, h = 높이"""
    r = h * 0.36
    d.polygon([(x, y), (x - r * 0.95, y + h - r * 1.3), (x + r * 0.95, y + h - r * 1.3)], fill=fill)
    d.ellipse([x - r, y + h - 2 * r, x + r, y + h], fill=fill)


def precip(d, x, y, p, size, anchor="ra"):
    """강수확률: 물방울 + 숫자. anchor 'ra' = x가 오른쪽 끝, 'ma' = x가 가운데"""
    if not p:
        return
    f = font(size)
    s = f"{p}%"
    tw = d.textlength(s, font=f)
    dw = size * 0.75
    total = dw + tw
    left = x - total if anchor == "ra" else x - total / 2
    draw_drop(d, left + dw * 0.4, y + size * 0.2, size * 0.85)
    text(d, (left + dw, y), s, f, fill=DARK)


def draw_icon(d, kind, cx, cy, size, day=True):
    r = size / 2
    w = max(2, int(size / 22))
    if kind in ("clear", "mostly_clear"):
        (draw_sun if day else draw_moon)(d, cx, cy, r, w)
        if kind == "mostly_clear":
            draw_cloud(d, cx + r * 0.35, cy + r * 0.45, r * 0.5, w)
    elif kind == "partly":
        (draw_sun if day else draw_moon)(d, cx - r * 0.25, cy - r * 0.25, r * 0.7, w)
        draw_cloud(d, cx + r * 0.1, cy + r * 0.15, r * 0.8, w)
    elif kind == "cloudy":
        draw_cloud(d, cx, cy, r, w, fill=LIGHT)
    elif kind == "fog":
        for i in range(4):
            y = cy - r * 0.45 + i * r * 0.3
            d.line([cx - r * 0.8, y, cx + r * 0.8, y], fill=BLACK, width=w)
    elif kind in ("rain", "snow", "storm"):
        draw_cloud(d, cx, cy - r * 0.25, r * 0.85, w, fill=LIGHT)
        for i in range(3):
            x = cx - r * 0.4 + i * r * 0.4
            y = cy + r * 0.45
            if kind == "rain":
                d.line([x + r * 0.08, y, x - r * 0.08, y + r * 0.35], fill=BLACK, width=w)
            elif kind == "snow":
                s = r * 0.1
                d.ellipse([x - s, y + r * 0.1, x + s, y + r * 0.1 + 2 * s], fill=BLACK)
        if kind == "storm":
            d.polygon([(cx + r * 0.05, cy + r * 0.3), (cx - r * 0.2, cy + r * 0.65),
                       (cx, cy + r * 0.65), (cx - r * 0.1, cy + r * 0.95),
                       (cx + r * 0.25, cy + r * 0.55), (cx + r * 0.05, cy + r * 0.55)], fill=BLACK)


# ---- 그리기 헬퍼 -----------------------------------------------------------
def text(d, xy, s, f, fill=BLACK, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def hline(d, y, x0=40, x1=W - 40, fill=MID, width=2):
    d.line([x0, y, x1, y], fill=fill, width=width)


# ---- 렌더 ----------------------------------------------------------------
def render(weather, air, battery=None):
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    now = now_kst()
    cur = weather["current"]

    # 헤더
    text(d, (40, 30), f"{now.month}월 {now.day}일 {WEEKDAYS[now.weekday()]}요일", font(52, True))
    text(d, (W - 40, 36), PLACE, font(34), anchor="ra")
    sub = f"업데이트 {now:%H:%M}"
    if battery is not None:
        sub += f" · 배터리 {battery}%"
    text(d, (W - 40, 82), sub, font(26), fill=DARK, anchor="ra")
    hline(d, 130, fill=BLACK, width=3)

    # 현재 날씨
    desc, kind = describe(cur["weather_code"])
    draw_icon(d, kind, 210, 320, 300, day=bool(cur.get("is_day", 1)))
    text(d, (420, 165), f"{round(cur['temperature_2m'])}°", font(210, True))
    text(d, (430, 420), desc, font(52, True))
    today = weather["daily"]
    text(d, (430, 485),
         f"최고 {round(today['temperature_2m_max'][0])}°  최저 {round(today['temperature_2m_min'][0])}°",
         font(32), fill=DARK)
    detail = (f"체감 {round(cur['apparent_temperature'])}°   습도 {cur['relative_humidity_2m']}%   "
              f"바람 {cur['wind_speed_10m']:.1f}m/s   "
              f"일출 {today['sunrise'][0][-5:]}  일몰 {today['sunset'][0][-5:]}")
    text(d, (W / 2, 560), detail, font(28), fill=DARK, anchor="ma")
    hline(d, 615)

    # 미세먼지
    ac = air.get("current", {})
    pm10, pm25 = ac.get("pm10"), ac.get("pm2_5")
    boxes = [("미세먼지 PM10", pm10, grade_pm10(pm10)), ("초미세먼지 PM2.5", pm25, grade_pm25(pm25))]
    bw, bh, by = 476, 170, 640
    for i, (label, val, grade) in enumerate(boxes):
        x0 = 40 + i * (bw + 40)
        bad = grade in ("나쁨", "매우나쁨")
        bg, fg = (BLACK, WHITE) if bad else (WHITE, BLACK)
        d.rounded_rectangle([x0, by, x0 + bw, by + bh], radius=18, fill=bg, outline=BLACK, width=3)
        text(d, (x0 + 28, by + 18), label, font(30), fill=fg)
        text(d, (x0 + 28, by + 62), grade, font(66, True), fill=fg)
        vs = "-" if val is None else f"{round(val)}"
        text(d, (x0 + bw - 28, by + 70), vs, font(62, True), fill=fg, anchor="ra")
        text(d, (x0 + bw - 28, by + 140), "㎍/㎥", font(24), fill=fg, anchor="ra")
    hline(d, 845)

    # 시간별 (2시간 간격 8칸)
    hr = weather["hourly"]
    times = [datetime.fromisoformat(t) for t in hr["time"]]
    start = next(i for i, t in enumerate(times) if t >= now.replace(minute=0, second=0, microsecond=0))
    idx = [start + 2 * k for k in range(1, 9) if start + 2 * k < len(times)]
    text(d, (40, 860), "시간별 예보", font(30, True))
    cw = (W - 80) / len(idx)
    for k, i in enumerate(idx):
        cx = 40 + cw * k + cw / 2
        t = times[i]
        label = f"{t.hour}시" if t.hour else f"{t.day}일"
        text(d, (cx, 910), label, font(28), fill=DARK, anchor="ma")
        _, hk = describe(hr["weather_code"][i])
        draw_icon(d, hk, cx, 990, 72, day=bool(hr["is_day"][i]))
        text(d, (cx, 1040), f"{round(hr['temperature_2m'][i])}°", font(36, True), anchor="ma")
        precip(d, cx, 1086, hr["precipitation_probability"][i], 26, anchor="ma")
    hline(d, 1130)

    # 주간 (7일)
    dl = weather["daily"]
    tmin_all, tmax_all = min(dl["temperature_2m_min"]), max(dl["temperature_2m_max"])
    span = max(1, tmax_all - tmin_all)
    row_h = 41
    y0 = 1145
    bar_x0, bar_x1 = 640, W - 120
    for k in range(len(dl["time"])):
        y = y0 + k * row_h
        dt = datetime.fromisoformat(dl["time"][k])
        name = "오늘" if k == 0 else WEEKDAYS[dt.weekday()]
        text(d, (40, y), name, font(30, True))
        text(d, (112, y + 4), f"{dt.month}/{dt.day}", font(24), fill=DARK)
        dk_desc, dk = describe(dl["weather_code"][k])
        draw_icon(d, dk, 225, y + 20, 40)
        text(d, (260, y + 2), dk_desc, font(26))
        precip(d, 530, y + 4, dl["precipitation_probability_max"][k], 24)
        lo, hi = dl["temperature_2m_min"][k], dl["temperature_2m_max"][k]
        text(d, (bar_x0 - 14, y + 2), f"{round(lo)}°", font(28), fill=DARK, anchor="ra")
        xa = bar_x0 + (lo - tmin_all) / span * (bar_x1 - bar_x0)
        xb = bar_x0 + (hi - tmin_all) / span * (bar_x1 - bar_x0)
        d.rounded_rectangle([bar_x0, y + 15, bar_x1, y + 25], radius=5, fill=LIGHT)
        d.rounded_rectangle([xa, y + 13, max(xb, xa + 10), y + 27], radius=7, fill=BLACK)
        text(d, (bar_x1 + 14, y + 2), f"{round(hi)}°", font(28, True))

    return img


def render_error(msg):
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    text(d, (W / 2, H / 2 - 40), "데이터를 가져오지 못했어요", font(48, True), anchor="mm")
    text(d, (W / 2, H / 2 + 30), f"{now_kst():%H:%M} · {msg[:60]}", font(26), fill=DARK, anchor="mm")
    return img


if __name__ == "__main__":
    # 사용법: python dashboard.py [출력경로]   (기본: preview.png)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("preview.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    weather, air = get_data()  # 실패하면 예외 → Actions 실패로 남기고 이전 이미지는 유지
    render(weather, air).save(out)
    print(out)
