import streamlit as st
import streamlit.components.v1 as components
from pyecharts import options as opts
from pyecharts.charts import Line
from streamlit_echarts import st_pyecharts
import requests
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import pytz
import holidays
import re
from urllib.parse import urljoin, urlparse
import subprocess
import json

# 페이지 설정
st.set_page_config(
    page_title="KOSPI & KOSDAQ 실시간 지수",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Light Mode, Stability, and Refinement (Value Horizon Style)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* Minimize Streamlit Padding and Margins */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        max-width: 1000px !important;
    }
    
    [data-testid="stHeader"] {
        display: none;
    }

    /* Global Light Mode Styles */
    .stApp {
        background-color: #ffffff;
        color: #1a1a1a;
        font-family: 'Inter', sans-serif;
    }

    /* Hero Section - Compact */
    .hero-container {
        padding: 1.5rem 0;
        text-align: center;
        border-bottom: 1px solid #f0f0f0;
        margin-bottom: 2rem;
    }

    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #111111;
        margin-bottom: 0.25rem;
        letter-spacing: -0.5px;
    }

    .hero-subtitle {
        font-size: 0.95rem;
        font-weight: 400;
        color: #888888;
    }

    /* Hide Streamlit components */
    #MainMenu, footer, header, .stDeployButton {
        display: none !important;
    }

    /* Metric Styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }

    /* Custom Button Styling */
    .stButton > button {
        font-size: 0.85rem !important;
        height: 2.5rem !important;
        margin-top: 2rem !important;
        padding: 0 1rem !important;
        background-color: #f8fafc !important;
        color: #64748b !important;
        border: 1px solid #e2e8f0 !important;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
        border-color: #cbd5e1 !important;
    }
</style>
""", unsafe_allow_html=True)

KST_TZ = pytz.timezone('Asia/Seoul')
KRX_OPEN_TIME = time(9, 0, 0)
KRX_CLOSE_TIME = time(15, 30, 0)

@st.cache_data(show_spinner=False, ttl=3600)
def get_kr_holiday_dates(years):
    return sorted({day.strftime("%Y-%m-%d") for day in holidays.KR(years=years).keys()})

def is_krx_trading_day(date_kst, kr_holiday_set=None):
    if date_kst.weekday() >= 5:
        return False
    if kr_holiday_set is None:
        years = (date_kst.year - 1, date_kst.year, date_kst.year + 1)
        kr_holiday_set = set(get_kr_holiday_dates(years))
    return date_kst.strftime("%Y-%m-%d") not in kr_holiday_set

def get_next_krx_open_datetime(now_kst, kr_holiday_set=None):
    candidate_date = now_kst.date()
    if kr_holiday_set is None:
        years = (candidate_date.year - 1, candidate_date.year, candidate_date.year + 1)
        kr_holiday_set = set(get_kr_holiday_dates(years))

    for _ in range(370):
        open_dt = KST_TZ.localize(datetime.combine(candidate_date, KRX_OPEN_TIME))
        if is_krx_trading_day(candidate_date, kr_holiday_set) and now_kst < open_dt:
            return open_dt
        candidate_date += timedelta(days=1)
    return KST_TZ.localize(datetime.combine(candidate_date, KRX_OPEN_TIME))

def get_market_countdown_context(now_kst):
    years = (now_kst.year - 1, now_kst.year, now_kst.year + 1, now_kst.year + 2)
    holiday_dates = get_kr_holiday_dates(years)
    holiday_set = set(holiday_dates)

    today = now_kst.date()
    open_dt = KST_TZ.localize(datetime.combine(today, KRX_OPEN_TIME))
    close_dt = KST_TZ.localize(datetime.combine(today, KRX_CLOSE_TIME))

    if is_krx_trading_day(today, holiday_set) and open_dt <= now_kst < close_dt:
        market_state = "open"
        target_dt_kst = close_dt
        label = "장 종료까지"
    else:
        market_state = "closed"
        target_dt_kst = get_next_krx_open_datetime(now_kst, holiday_set)
        label = "다음 장 시작까지"

    return {
        "market_state": market_state,
        "target_dt_kst": target_dt_kst,
        "target_epoch_ms": int(target_dt_kst.timestamp() * 1000),
        "label": label,
        "holiday_dates": holiday_dates,
    }

def render_market_countdown(context):
    config = {
        "initialState": context["market_state"],
        "initialLabel": context["label"],
        "initialTargetEpochMs": context["target_epoch_ms"],
        "holidayDates": context["holiday_dates"],
    }
    html_template = """
    <style>
      body {
        margin: 0;
      }
      .krx-countdown-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.52rem 0.72rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.6rem;
        white-space: nowrap;
        overflow: hidden;
      }
      .krx-countdown-left {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        min-width: 0;
        flex: 1 1 auto;
        color: #334155;
        font-size: 0.84rem;
      }
      .krx-status-badge {
        border: 1px solid #cbd5e1;
        background: #ffffff;
        color: #475569;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        padding: 0.14rem 0.5rem;
        flex: 0 0 auto;
      }
      .krx-divider {
        width: 1px;
        height: 14px;
        background: #cbd5e1;
        flex: 0 0 auto;
      }
      .krx-countdown-label {
        font-size: 0.83rem;
      }
      .krx-countdown-time {
        color: #0f172a;
        font-size: 1.08rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        font-variant-numeric: tabular-nums;
        flex: 0 0 auto;
      }
    </style>
    <div class="krx-countdown-card">
      <div class="krx-countdown-left">
        <div id="krx-status" class="krx-status-badge"></div>
        <div class="krx-divider"></div>
        <div id="krx-label" class="krx-countdown-label"></div>
      </div>
      <div id="krx-time" class="krx-countdown-time">00:00:00</div>
    </div>
    <script>
      const config = __CONFIG__;
      const holidaySet = new Set(config.holidayDates || []);
      const KST_OFFSET_MS = 9 * 60 * 60 * 1000;
      const DAY_MS = 24 * 60 * 60 * 1000;

      const statusEl = document.getElementById("krx-status");
      const labelEl = document.getElementById("krx-label");
      const timeEl = document.getElementById("krx-time");

      function toKstParts(epochMs) {
        const d = new Date(epochMs + KST_OFFSET_MS);
        return {
          year: d.getUTCFullYear(),
          month: d.getUTCMonth() + 1,
          day: d.getUTCDate(),
          hour: d.getUTCHours(),
          minute: d.getUTCMinutes(),
          second: d.getUTCSeconds(),
          weekday: d.getUTCDay()
        };
      }

      function ymd(parts) {
        const m = String(parts.month).padStart(2, "0");
        const d = String(parts.day).padStart(2, "0");
        return `${parts.year}-${m}-${d}`;
      }

      function isTradingDay(parts) {
        if (parts.weekday === 0 || parts.weekday === 6) {
          return false;
        }
        return !holidaySet.has(ymd(parts));
      }

      function epochFromKst(y, m, d, h, min, sec) {
        return Date.UTC(y, m - 1, d, h - 9, min, sec);
      }

      function addKstDays(parts, days) {
        const midnightEpoch = epochFromKst(parts.year, parts.month, parts.day, 0, 0, 0);
        return toKstParts(midnightEpoch + (days * DAY_MS));
      }

      function findNextOpenEpoch(fromEpoch) {
        let cursor = toKstParts(fromEpoch);
        for (let i = 0; i < 370; i += 1) {
          const openEpoch = epochFromKst(cursor.year, cursor.month, cursor.day, 9, 0, 0);
          if (isTradingDay(cursor) && fromEpoch < openEpoch) {
            return openEpoch;
          }
          cursor = addKstDays(cursor, 1);
        }
        return fromEpoch + DAY_MS;
      }

      function computeContext(nowEpoch) {
        const p = toKstParts(nowEpoch);
        const openEpoch = epochFromKst(p.year, p.month, p.day, 9, 0, 0);
        const closeEpoch = epochFromKst(p.year, p.month, p.day, 15, 30, 0);

        if (isTradingDay(p) && nowEpoch >= openEpoch && nowEpoch < closeEpoch) {
          return {
            state: "open",
            label: "장 종료까지",
            targetEpoch: closeEpoch
          };
        }
        return {
          state: "closed",
          label: "다음 장 시작까지",
          targetEpoch: findNextOpenEpoch(nowEpoch)
        };
      }

      function formatHms(seconds) {
        const s = Math.max(0, seconds);
        const hh = String(Math.floor(s / 3600)).padStart(2, "0");
        const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
        const ss = String(s % 60).padStart(2, "0");
        return `${hh}:${mm}:${ss}`;
      }

      function render(ctx, nowEpoch) {
        const stateUpper = ctx.state === "open" ? "OPEN" : "CLOSED";
        const remainSec = Math.max(0, Math.floor((ctx.targetEpoch - nowEpoch) / 1000));
        statusEl.textContent = stateUpper;
        labelEl.textContent = ctx.label;
        timeEl.textContent = formatHms(remainSec);
      }

      function tick() {
        const now = Date.now();
        const ctx = computeContext(now);
        render(ctx, now);
      }

      statusEl.textContent = String(config.initialState || "closed").toUpperCase();
      labelEl.textContent = config.initialLabel || "다음 장 시작까지";
      timeEl.textContent = "00:00:00";
      tick();
      setInterval(tick, 1000);
    </script>
    """
    html = html_template.replace("__CONFIG__", json.dumps(config, ensure_ascii=False))
    components.html(html, height=62)

def fetch_index_data(index_type, today_str):
    """네이버 증권 API를 통해 특정 지수(KOSPI/KOSDAQ) 데이터를 가져옴"""
    url = f"https://stock.naver.com/api/domestic/indexSise/time?koreaIndexType={index_type}&thistime={today_str}&startIdx=0&pageSize=500"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"{index_type} 데이터를 가져오는 중 오류 발생: {e}")
        return pd.DataFrame()

def get_krx_auth_key():
    """Streamlit secret에서 KRX AUTH_KEY를 안전하게 읽음"""
    try:
        if "KRX_AUTH_KEY" in st.secrets:
            auth_key = st.secrets["KRX_AUTH_KEY"]
        elif "krx" in st.secrets and "auth_key" in st.secrets["krx"]:
            auth_key = st.secrets["krx"]["auth_key"]
        else:
            auth_key = None
    except Exception:
        auth_key = None
    if not auth_key:
        return None, "KRX_AUTH_KEY가 설정되지 않았습니다."
    return str(auth_key), None

def iter_basdd_candidates_kst():
    """한국시간 기준 내일 포함 과거 10일까지(총 11일) YYYYMMDD 생성"""
    seoul_tz = pytz.timezone('Asia/Seoul')
    tomorrow = datetime.now(seoul_tz).date() + timedelta(days=1)
    return [(tomorrow - timedelta(days=offset)).strftime("%Y%m%d") for offset in range(11)]

def extract_rows_from_krx_payload(payload):
    """KRX 응답에서 행 리스트를 방어적으로 추출"""
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    rows = []
    preferred_keys = ["OutBlock_1", "output", "result", "data", "list"]
    for key in preferred_keys:
        val = payload.get(key)
        if isinstance(val, list):
            rows.extend([row for row in val if isinstance(row, dict)])

    if rows:
        return rows

    for val in payload.values():
        if isinstance(val, list):
            rows.extend([row for row in val if isinstance(row, dict)])
    return rows

def fetch_krx_futures_by_date(bas_dd, auth_key):
    """지정 기준일자 KRX 선물 데이터 조회"""
    url = "https://data-dbg.krx.co.kr/svc/apis/drv/fut_bydd_trd.json"
    params = {"AUTH_KEY": auth_key, "basDd": bas_dd}
    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    header_profiles = [
        # 브라우저 직접 URL 진입과 유사한 최소 헤더
        {
            "name": "minimal",
            "headers": {
                "User-Agent": user_agent,
                "Accept": "*/*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            },
            "warmup": False,
        },
        # 브라우저 navigate 흐름과 유사한 헤더
        {
            "name": "navigate",
            "headers": {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
            "warmup": False,
        },
        # 세션/쿠키 확보 후 호출
        {
            "name": "session",
            "headers": {
                "User-Agent": user_agent,
                "Accept": "application/json,text/plain,*/*",
                "Referer": "https://data-dbg.krx.co.kr/",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
            },
            "warmup": True,
        },
    ]

    last_err = None
    last_profile = "-"
    for profile in header_profiles:
        for timeout_sec in (10, 20):
            try:
                session = requests.Session()
                session.headers.update(profile["headers"])

                if profile["warmup"]:
                    session.get("https://data-dbg.krx.co.kr/", timeout=timeout_sec, allow_redirects=True)

                response = session.get(
                    url,
                    params=params,
                    timeout=timeout_sec,
                    allow_redirects=False,
                )
                if response.is_redirect or response.is_permanent_redirect:
                    redirect_url = response.headers.get("Location", "")
                    if redirect_url:
                        target = urljoin(url, redirect_url)
                        parsed = urlparse(target)
                        if parsed.scheme == "http":
                            target = target.replace("http://", "https://", 1)
                        response = session.get(target, timeout=timeout_sec, allow_redirects=False)
                response.raise_for_status()
                payload = response.json()
                return extract_rows_from_krx_payload(payload)
            except Exception as e:
                last_profile = profile["name"]
                last_err = e
                continue

    if isinstance(last_err, requests.HTTPError) and last_err.response is not None:
        body_preview = last_err.response.text[:200].replace("\n", " ")
        request_err = RuntimeError(
            f"HTTP {last_err.response.status_code}: {body_preview} "
            f"(profile={last_profile}, 브라우저는 성공/앱은 실패 시 서버측 IP 차단 또는 봇 차단 가능)"
        )
    else:
        request_err = last_err

    # requests가 WAF에 차단될 때 curl이 통과하는 경우가 있어 fallback 시도
    curl_cmd = [
        "curl",
        "-sS",
        "--http1.1",
        "--max-time",
        "20",
        "-H",
        f"User-Agent: {user_agent}",
        "-H",
        "Accept: */*",
        "-H",
        "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        f"{url}?AUTH_KEY={auth_key}&basDd={bas_dd}",
    ]
    try:
        out = subprocess.check_output(curl_cmd, stderr=subprocess.STDOUT, text=True)
        payload = json.loads(out)
        rows = extract_rows_from_krx_payload(payload)
        if rows:
            return rows
    except Exception as curl_err:
        raise RuntimeError(f"{request_err} | curl_fallback_error={str(curl_err)[:200]}") from curl_err

    raise request_err

def normalize_kr_text(value):
    return re.sub(r"\s+", "", str(value or "")).strip()

def parse_yyyymm_contract(value):
    text = normalize_kr_text(value)

    # 1) YYYYMM or YYYY-MM/ YYYY.MM
    match = re.search(r"(20\d{2})[-./]?(0[1-9]|1[0-2])", text)
    if match:
        return int(f"{match.group(1)}{match.group(2)}")

    # 2) YYMM (ex: 2603)
    match = re.search(r"(?<!\d)(\d{2})(0[1-9]|1[0-2])(?!\d)", text)
    if match:
        return int(f"20{match.group(1)}{match.group(2)}")

    # 3) YYYY년M월 / YY년M월
    match = re.search(r"((?:20)?\d{2})년\s*([1-9]|1[0-2])월", text)
    if match:
        year = match.group(1)
        if len(year) == 2:
            year = f"20{year}"
        month = int(match.group(2))
        return int(f"{year}{month:02d}")

    return None

def yyyymm_to_serial(yyyymm):
    year = int(yyyymm) // 100
    month = int(yyyymm) % 100
    return year * 12 + month

def get_current_yyyymm_kst():
    seoul_tz = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(seoul_tz)
    return now_kst.year * 100 + now_kst.month

def normalize_bas_dd(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) >= 8:
        return int(digits[:8])
    return 0

def format_bas_dd(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return str(value) if value is not None else "-"

def format_metric_number(value):
    num = clean_value(value)
    if num is None:
        return "-" if value is None else str(value)
    if float(num).is_integer():
        return f"{int(num):,}"
    return f"{num:,.2f}"

def calculate_change_rate_from_close_and_delta(close_value, delta_value):
    close_num = clean_value(close_value)
    delta_num = clean_value(delta_value)
    if close_num is None or delta_num is None:
        return None
    prev_close = close_num - delta_num
    if prev_close == 0:
        return None
    return f"{(delta_num / prev_close) * 100:.2f}"

def build_kospi_night_candidates(rows):
    """코스피200 선물/야간 후보에서 파싱 가능한 월물 목록 생성"""
    candidates = []
    for row in rows:
        prod_nm = normalize_kr_text(row.get("PROD_NM"))
        mkt_nm = normalize_kr_text(row.get("MKT_NM"))

        # API별 표기 차이(공백/접미어)를 허용
        if "코스피200선물" not in prod_nm:
            continue
        if "야간" not in mkt_nm:
            continue

        # 요구 조건: ISU_NM == "코스피200 F {YYYYMM} (야간)" 형식만 허용
        isu_nm = str(row.get("ISU_NM") or "").strip()
        match = re.match(r"^코스피200\s*F\s*(20\d{2})(0[1-9]|1[0-2])\s*\(야간\)$", isu_nm)
        if not match:
            continue
        yyyymm = int(f"{match.group(1)}{match.group(2)}")
        candidates.append((yyyymm, row))
    return candidates

def select_latest_kospi_night_contract(rows):
    """코스피200 선물/야간 중 현재 기준 최근(근접) 월물 계약 선택"""
    candidates = build_kospi_night_candidates(rows)

    if not candidates:
        return None

    current_yyyymm = get_current_yyyymm_kst()
    current_serial = yyyymm_to_serial(current_yyyymm)

    unique_months = sorted({month for month, _ in candidates})
    target_month = min(
        unique_months,
        key=lambda month: (
            abs(yyyymm_to_serial(month) - current_serial),
            0 if yyyymm_to_serial(month) >= current_serial else 1,
            yyyymm_to_serial(month),
        ),
    )

    same_month_rows = [row for month, row in candidates if month == target_month]
    same_month_rows.sort(
        key=lambda row: (
            normalize_bas_dd(row.get("BAS_DD")),
            str(row.get("ISU_NM", "")),
        ),
        reverse=True
    )
    return same_month_rows[0] if same_month_rows else None

@st.cache_data(show_spinner=False, ttl=60)
def _get_latest_kospi_night_futures_cached(auth_key, bas_dd_candidates, debug_version):
    """KRX AUTH_KEY와 기준일 후보에 종속된 캐시 조회"""
    debug_logs = []
    last_error = None
    current_yyyymm = get_current_yyyymm_kst()
    for bas_dd in bas_dd_candidates:
        try:
            rows = fetch_krx_futures_by_date(bas_dd, auth_key)
        except Exception as e:
            last_error = str(e)
            debug_logs.append({
                "request_bas_dd": bas_dd,
                "bas_dd": bas_dd,
                "status": "error",
                "rows": 0,
                "filtered": 0,
                "selected_isu_nm": "-",
                "selected_bas_dd": "-",
                "selected_close": "-",
                "message": str(e),
                "current_yyyymm": current_yyyymm,
                "candidate_months": "-",
                "target_month": "-",
            })
            continue

        candidates = build_kospi_night_candidates(rows)
        filtered_count = len(candidates)
        unique_months = sorted({month for month, _ in candidates})
        target_month = "-"
        if unique_months:
            current_serial = yyyymm_to_serial(current_yyyymm)
            target_month = min(
                unique_months,
                key=lambda month: (
                    abs(yyyymm_to_serial(month) - current_serial),
                    0 if yyyymm_to_serial(month) >= current_serial else 1,
                    yyyymm_to_serial(month),
                ),
            )
        selected = select_latest_kospi_night_contract(rows)
        debug_logs.append({
            "request_bas_dd": bas_dd,
            "bas_dd": bas_dd,
            "status": "ok",
            "rows": len(rows),
            "filtered": filtered_count,
            "selected_isu_nm": str(selected.get("ISU_NM")) if selected else "-",
            "selected_bas_dd": str(selected.get("BAS_DD")) if selected else "-",
            "selected_close": str(selected.get("TDD_CLSPRC")) if selected else "-",
            "message": "selected" if selected else "no-match",
            "current_yyyymm": current_yyyymm,
            "candidate_months": ",".join(str(m) for m in unique_months) if unique_months else "-",
            "target_month": str(target_month),
        })
        if selected is not None:
            return selected, None, debug_logs

    if last_error:
        return None, f"KRX API 호출 실패: {last_error}", debug_logs
    return None, "최근 10일(내일 기준) 내 야간 코스피200 선물 데이터가 없습니다.", debug_logs

def get_latest_kospi_night_futures():
    """최신 유효 코스피200 야간선물 데이터 1건 조회"""
    auth_key, auth_msg = get_krx_auth_key()
    if not auth_key:
        return None, auth_msg, []
    bas_dd_candidates = tuple(iter_basdd_candidates_kst())
    return _get_latest_kospi_night_futures_cached(auth_key, bas_dd_candidates, "debug-v2")

def render_kospi_night_debug_logs(debug_logs):
    """야간선물 조회 이력을 화면에 디버그용으로 표시"""
    if not debug_logs:
        return

    logs_df = pd.DataFrame(debug_logs).copy()
    logs_df["조회순서"] = range(1, len(logs_df) + 1)
    preferred_cols = [
        "조회순서",
        "request_bas_dd",
        "status",
        "rows",
        "filtered",
        "candidate_months",
        "target_month",
        "selected_bas_dd",
        "selected_isu_nm",
        "selected_close",
        "message",
    ]
    visible_cols = [col for col in preferred_cols if col in logs_df.columns]
    logs_df = logs_df[visible_cols]
    logs_df = logs_df.rename(
        columns={
            "request_bas_dd": "요청기준일",
            "status": "상태",
            "rows": "전체건수",
            "filtered": "필터통과건수",
            "candidate_months": "후보월물",
            "target_month": "선택월물",
            "selected_bas_dd": "응답기준일",
            "selected_isu_nm": "선택종목",
            "selected_close": "종가",
            "message": "메시지",
        }
    )

    with st.expander("야간선물 데이터 조회 디버그", expanded=False):
        st.caption("조회순서 1이 가장 먼저 요청된 기준일입니다. (내일→오늘→과거)")
        st.dataframe(logs_df, use_container_width=True, hide_index=True)

def get_valid_data(start_date):
    """
    선택된 날짜부터 시작하여 데이터가 있는 가장 최근 평일의 데이터를 찾습니다.
    (주말 제외, 최대 10일 검색)
    """
    current_date = start_date
    for _ in range(10): # 최대 10일 전까지 검색
        # 주말 체크 (5: 토요일, 6: 일요일)
        if current_date.weekday() >= 5:
            current_date -= timedelta(days=1)
            continue

        date_str = current_date.strftime('%Y%m%d')
        df_kospi = fetch_index_data("KOSPI", date_str)
        df_kosdaq = fetch_index_data("KOSDAQ", date_str)

        # 데이터가 하나라도 있으면 유효한 날짜로 간주
        if not df_kospi.empty or not df_kosdaq.empty:
            return df_kospi, df_kosdaq, date_str

        # 데이터가 없으면 하루 전으로 이동
        current_date -= timedelta(days=1)

    return pd.DataFrame(), pd.DataFrame(), None

def clean_value(val):
    """값을 float으로 변환하되, NaN/None 시 None 반환"""
    try:
        if val is None:
            return None
        f_val = float(val)
        if not np.isfinite(f_val):
            return None
        return f_val
    except:
        return None

def generate_full_timeline():
    """09:00부터 15:30까지 1분 단위 리스트 생성"""
    start = datetime.combine(datetime.today(), time(9, 0))
    end = datetime.combine(datetime.today(), time(15, 30))
    curr = start
    timeline = []
    while curr <= end:
        timeline.append(curr.strftime('%H:%M'))
        curr += timedelta(minutes=1)
    return timeline

def calculate_y_axis_bounds(values):
    """첫 번째 유효 데이터를 Y축 중앙(50%)에 위치시키도록 min, max 계산"""
    reference_val = None
    for v in values:
        if v is not None:
            reference_val = v
            break
    
    if reference_val is None:
        return None, None
    
    valid_values = [v for v in values if v is not None]
    max_val = max(valid_values)
    min_val = min(valid_values)
    
    diff_up = max_val - reference_val
    diff_down = reference_val - min_val
    margin = max(diff_up, diff_down)
    
    if margin == 0:
        margin = reference_val * 0.005
    else:
        margin = margin * 1.15
        
    return float(reference_val - margin), float(reference_val + margin)

def get_extrema_info(timeline, values):
    """최고점과 최저점의 시간과 값을 반환"""
    valid_data = [(t, v) for t, v in zip(timeline, values) if v is not None]
    if not valid_data:
        return None, None
    
    max_item = max(valid_data, key=lambda x: x[1])
    min_item = min(valid_data, key=lambda x: x[1])
    
    return max_item, min_item

@st.fragment(run_every=60)
def update_dashboard(selected_date):
    with st.spinner('데이터를 불러오고 있습니다...'):
        df_kospi, df_kosdaq, actual_date_str = get_valid_data(selected_date)

    if df_kospi.empty and df_kosdaq.empty:
        st.info("📌 선택한 날짜 및 이전 평일에 대한 주가 정보가 없습니다.")
        return

    # 날짜 표시 로직 개선
    display_msg = f"기준 날짜: {actual_date_str} (한국 시간)"
    st.write(display_msg)

    # 전체 타임라인 생성 및 데이터 병합
    full_timeline = generate_full_timeline()
    timeline_df = pd.DataFrame({'time_hm': full_timeline})

    def process_df(df, name):
        if df.empty: return pd.DataFrame(columns=['time_hm', name])
        df['time_hm'] = df['thistime'].apply(lambda x: f"{x[8:10]}:{x[10:12]}")
        return df.sort_values('thistime')[['time_hm', 'nowVal']].rename(columns={'nowVal': name})

    df_p_kospi = process_df(df_kospi, 'KOSPI')
    df_p_kosdaq = process_df(df_kosdaq, 'KOSDAQ')

    merged = pd.merge(timeline_df, df_p_kospi, on='time_hm', how='left')
    merged = pd.merge(merged, df_p_kosdaq, on='time_hm', how='left')

    # 순수 숫자 리스트
    kospi_nums = [clean_value(v) for v in merged['KOSPI']]
    kosdaq_nums = [clean_value(v) for v in merged['KOSDAQ']]

    # 최고/최저점 좌표 계산
    k_max_info, k_min_info = get_extrema_info(full_timeline, kospi_nums)
    q_max_info, q_min_info = get_extrema_info(full_timeline, kosdaq_nums)

    # Y축 범위 계산
    k_min_bound, k_max_bound = calculate_y_axis_bounds(kospi_nums)
    q_min_bound, q_max_bound = calculate_y_axis_bounds(kosdaq_nums)

    # 상단 지표 (Custom Metric)
    def render_custom_metric(label, value, change_val, change_rate, max_info=None, min_info=None, extra_info=None):
        try:
            val_num = float(str(change_val).replace(',', ''))
            is_up = val_num > 0
            is_zero = val_num == 0
        except:
            change_text = str(change_val).strip()
            is_up = not change_text.startswith('-')
            is_zero = change_text in {"0", "0.0", "+0", "-0", "-"}
        
        color = "#ef4444" if is_up else "#3b82f6"
        icon = "▲" if is_up else "▼"
        if is_zero:
            color = "#64748b"
            icon = "-"
        
        # Extrema HTML
        extrema_html = ""
        if max_info and min_info:
            extrema_html = f"""
            <div style="display: flex; justify-content: space-between; margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #e2e8f0; font-size: 0.8rem;">
                <div style="color: #64748b;">
                    <span style="color: #ef4444; font-weight: 600;">최고</span> {max_info[1]:,.2f} <span style="font-size: 0.75rem; opacity: 0.8;">({max_info[0]})</span>
                </div>
                <div style="color: #64748b;">
                    <span style="color: #3b82f6; font-weight: 600;">최저</span> {min_info[1]:,.2f} <span style="font-size: 0.75rem; opacity: 0.8;">({min_info[0]})</span>
                </div>
            </div>
            """

        delta_text = "-"
        if str(change_val).strip() not in {"", "-"}:
            if change_rate in (None, "", "-"):
                delta_text = f"{icon} {change_val}"
            else:
                delta_text = f"{icon} {change_val} ({change_rate}%)"

        extra_html = ""
        if extra_info:
            extra_html = f"""
            <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #e2e8f0; font-size: 0.8rem; color: #64748b;">
                {extra_info}
            </div>
            """

        st.markdown(f"""
            <div style="background-color: #f8fafc; padding: 1rem; border-radius: 12px; border: 1px solid #f1f5f9; margin-bottom: 1rem;">
                <div style="font-size: 0.85rem; font-weight: 600; color: #64748b; margin-bottom: 0.25rem;">{label}</div>
                <div style="font-size: 1.8rem; font-weight: 700; color: #0f172a;">{value}</div>
                <div style="font-size: 1rem; font-weight: 600; color: {color}; margin-top: 0.25rem;">
                    {delta_text}
                </div>
                {extrema_html}
                {extra_html}
            </div>
        """, unsafe_allow_html=True)

    kospi_night_row, kospi_night_msg, kospi_night_debug_logs = get_latest_kospi_night_futures()

    col1, col2, col3 = st.columns(3)
    with col1:
        if not df_kospi.empty:
            curr = df_kospi.sort_values('thistime', ascending=False).iloc[0]
            render_custom_metric("KOSPI 현재가", f"{float(curr['nowVal']):,.2f}", curr['changeVal'], curr['changeRate'], k_max_info, k_min_info)
    with col2:
        if not df_kosdaq.empty:
            curr = df_kosdaq.sort_values('thistime', ascending=False).iloc[0]
            render_custom_metric("KOSDAQ 현재가", f"{float(curr['nowVal']):,.2f}", curr['changeVal'], curr['changeRate'], q_max_info, q_min_info)
    with col3:
        if kospi_night_row:
            bas_dd_text = format_bas_dd(kospi_night_row.get("BAS_DD"))
            prod_nm = str(kospi_night_row.get("PROD_NM") or "-")
            mkt_nm = str(kospi_night_row.get("MKT_NM") or "-")
            extra = f"{bas_dd_text} | {prod_nm} | {mkt_nm}"
            change_rate = calculate_change_rate_from_close_and_delta(
                kospi_night_row.get("TDD_CLSPRC"),
                kospi_night_row.get("CMPPREVDD_PRC"),
            )
            render_custom_metric(
                "KOSPI 200 야간선물",
                format_metric_number(kospi_night_row.get("TDD_CLSPRC")),
                format_metric_number(kospi_night_row.get("CMPPREVDD_PRC")),
                change_rate,
                extra_info=extra,
            )
        else:
            render_custom_metric(
                "KOSPI 200 야간선물",
                "-",
                "-",
                None,
                extra_info=kospi_night_msg or "데이터를 가져올 수 없습니다.",
            )

    render_kospi_night_debug_logs(kospi_night_debug_logs)

    # pyecharts 차트 구성 (마커 제거 버전)
    line = (
        Line(init_opts=opts.InitOpts(height="500px", width="100%"))
        .add_xaxis(xaxis_data=full_timeline)
        .add_yaxis(
            series_name="KOSPI",
            y_axis=kospi_nums,
            yaxis_index=0,
            is_smooth=True,
            symbol="none",
            linestyle_opts=opts.LineStyleOpts(width=1.5, color="#3b82f6"),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="KOSDAQ",
            y_axis=kosdaq_nums,
            yaxis_index=1,
            is_smooth=True,
            symbol="none",
            linestyle_opts=opts.LineStyleOpts(width=1.5, color="#10b981"),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .extend_axis(
            yaxis=opts.AxisOpts(
                name="KOSDAQ",
                type_="value",
                min_=q_min_bound,
                max_=q_max_bound,
                position="right",
                is_scale=True,
                splitline_opts=opts.SplitLineOpts(is_show=False),
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="지수 실시간 추이",
                title_textstyle_opts=opts.TextStyleOpts(font_family="Inter", font_size=16, font_weight="bold")
            ),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="line"),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                boundary_gap=False,
                axislabel_opts=opts.LabelOpts(interval=29, font_family="Inter"), # 30분 단위 축 레이블 유지
            ),
            yaxis_opts=opts.AxisOpts(
                name="KOSPI",
                type_="value",
                min_=k_min_bound,
                max_=k_max_bound,
                is_scale=True,
                splitline_opts=opts.SplitLineOpts(is_show=True),
                axislabel_opts=opts.LabelOpts(font_family="Inter"),
            ),
            legend_opts=opts.LegendOpts(pos_top="5%", textstyle_opts=opts.TextStyleOpts(font_family="Inter")),
        )
    )
    
    # KOSPI 극점 및 라벨 (Index 0)
    if k_max_info and k_min_info:
        line.options["series"][0]["markPoint"] = {
            "data": [
                {"name": "최고", "coord": [k_max_info[0], k_max_info[1]], "itemStyle": {"color": "#ef4444"}, "label": {"formatter": f"최고\n{k_max_info[0]}\n{k_max_info[1]:,.2f}"}},
                {"name": "최저", "coord": [k_min_info[0], k_min_info[1]], "itemStyle": {"color": "#3b82f6"}, "label": {"formatter": f"최저\n{k_min_info[0]}\n{k_min_info[1]:,.2f}"}}
            ]
        }
    line.options["series"][0]["endLabel"] = {"show": True, "formatter": "KOSPI: {c}", "fontWeight": "bold", "color": "#3b82f6"}
    
    # KOSDAQ 극점 및 라벨 (Index 1)
    if q_max_info and q_min_info:
        line.options["series"][1]["markPoint"] = {
            "data": [
                {"name": "최고", "coord": [q_max_info[0], q_max_info[1]], "itemStyle": {"color": "#ef4444"}, "label": {"formatter": f"최고\n{q_max_info[0]}\n{q_max_info[1]:,.2f}"}},
                {"name": "최저", "coord": [q_min_info[0], q_min_info[1]], "itemStyle": {"color": "#3b82f6"}, "label": {"formatter": f"최저\n{q_min_info[0]}\n{q_min_info[1]:,.2f}"}}
            ]
        }
    line.options["series"][1]["endLabel"] = {"show": True, "formatter": "KOSDAQ: {c}", "fontWeight": "bold", "color": "#10b981"}
    
    line.options["animation"] = True
    line.options["animationDuration"] = 10000
    line.options["animationThreshold"] = 0
    line.options["series"][0]["labelLayout"] = {"moveOverlap": "shiftY"}
    line.options["series"][1]["labelLayout"] = {"moveOverlap": "shiftY"}

    st_pyecharts(line, height="500px")

def main():
    # Hero Section
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-title">Daily K-Stock</div>
        <div class="hero-subtitle">대한민국 주식 시장 트렌드에 대한 일일 인사이트 및 분석</div>
    </div>
    """, unsafe_allow_html=True)

    # 날짜 선택 기능 추가 (상단 배치)
    now_kst = datetime.now(KST_TZ)
    today = now_kst.date()
    countdown_context = get_market_countdown_context(now_kst)

    # 세션 상태 초기화
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = today

    col_date, col_btn, col_countdown, col_empty = st.columns([2, 1, 5, 2])
    
    with col_date:
        # date_input의 값을 session_state와 연동
        selected_date = st.date_input("📅 날짜 선택", value=st.session_state.selected_date, key="date_picker")
        # 직접 날짜를 바꾼 경우 session_state 업데이트
        if selected_date != st.session_state.selected_date:
            st.session_state.selected_date = selected_date
            st.rerun()

    with col_btn:
        if st.button("오늘", use_container_width=True):
            if st.session_state.selected_date != today:
                st.session_state.selected_date = today
                st.rerun()

    with col_countdown:
        st.markdown("<div style='height: 1.95rem;'></div>", unsafe_allow_html=True)
        render_market_countdown(countdown_context)

    update_dashboard(st.session_state.selected_date)

if __name__ == "__main__":
    main()
