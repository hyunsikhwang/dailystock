import streamlit as st
from streamlit_echarts import st_echarts
import requests
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import pytz

# 페이지 설정
st.set_page_config(page_title="KOSPI & KOSDAQ 실시간 지수", layout="wide")

def get_today_str():
    """한국 시간 기준 오늘 날짜를 YYYYMMDD 형식으로 반환"""
    seoul_tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(seoul_tz)
    return now.strftime('%Y%m%d')

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
    # 최초로 등장하는 유효 데이터 찾기
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
    
    # 기준점(첫 데이터)으로부터 가장 먼 변동폭 계산 (대칭 범위 확보를 위함)
    diff_up = max_val - reference_val
    diff_down = reference_val - min_val
    
    # 더 큰 변동폭을 기준으로 상하 대칭 마진 설정
    margin = max(diff_up, diff_down)
    
    # 변동이 아예 없는 경우를 대비한 최소 마진 (0.5%)
    if margin == 0:
        margin = reference_val * 0.005
    else:
        margin = margin * 1.15 # 15% 여유 공간 추가
        
    return reference_val - margin, reference_val + margin

def main():
    st.title("🏃‍♂️ KOSPI & KOSDAQ 실시간 지수")
    
    today_str = get_today_str()
    st.write(f"기준 날짜: {today_str} (한국 시간)")

    with st.spinner('데이터를 불러오고 있습니다...'):
        df_kospi = fetch_index_data("KOSPI", today_str)
        df_kosdaq = fetch_index_data("KOSDAQ", today_str)

    if df_kospi.empty and df_kosdaq.empty:
        st.info("📌 현재는 주가 정보가 없습니다. (휴장일이거나 데이터 로딩 실패)")
        return

    # 전체 타임라인 생성 (09:00 ~ 15:30)
    full_timeline = generate_full_timeline()
    timeline_df = pd.DataFrame({'time_hm': full_timeline})

    # 데이터 가공
    def process_df(df, name):
        if df.empty: return pd.DataFrame(columns=['time_hm', name])
        # MMSS 부분만 추출하여 HH:MM 형식으로 변환
        df['time_hm'] = df['thistime'].apply(lambda x: f"{x[8:10]}:{x[10:12]}")
        # API는 최신순이므로 전처리를 위해 시간 순 정렬
        df_sorted = df.sort_values('thistime')
        return df_sorted[['time_hm', 'nowVal']].rename(columns={'nowVal': name})

    df_p_kospi = process_df(df_kospi, 'KOSPI')
    df_p_kosdaq = process_df(df_kosdaq, 'KOSDAQ')

    # 병합
    merged = pd.merge(timeline_df, df_p_kospi, on='time_hm', how='left')
    merged = pd.merge(merged, df_p_kosdaq, on='time_hm', how='left')

    kospi_values = [clean_value(v) for v in merged['KOSPI']]
    kosdaq_values = [clean_value(v) for v in merged['KOSDAQ']]

    # Y축 범위 계산 (첫 데이터 지점 동기화)
    k_min, k_max = calculate_y_axis_bounds(kospi_values)
    q_min, q_max = calculate_y_axis_bounds(kosdaq_values)

    # 상단 지표 영역 (가로 배치)
    col1, col2 = st.columns(2)
    with col1:
        if not df_kospi.empty:
            curr = df_kospi.iloc[0]
            st.metric("KOSPI 현재가", f"{float(curr['nowVal']):,.2f}", f"{curr['changeVal']} ({curr['changeRate']}%)")
    with col2:
        if not df_kosdaq.empty:
            curr = df_kosdaq.iloc[0]
            st.metric("KOSDAQ 현재가", f"{float(curr['nowVal']):,.2f}", f"{curr['changeVal']} ({curr['changeRate']}%)")

    # ECharts 옵션 설정
    options = {
        "animation": True,
        "animationDuration": 10000,
        "animationThreshold": 2000,
        "title": {"text": "지수 실시간 추이 (시작점 동기화)"},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "line"}
        },
        "legend": {"data": ["KOSPI", "KOSDAQ"]},
        "grid": {
            "left": "3%",
            "right": "12%", 
            "bottom": "5%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": full_timeline,
            "boundaryGap": False,
            "axisLabel": {
                "interval": 29, 
                "formatter": "{value}"
            }
        },
        "yAxis": [
            {
                "name": "KOSPI", 
                "type": "value", 
                "min": k_min, 
                "max": k_max,
                "splitLine": {"show": True}
            },
            {
                "name": "KOSDAQ", 
                "type": "value", 
                "min": q_min, 
                "max": q_max,
                "yAxisIndex": 1,
                "splitLine": {"show": False}
            }
        ],
        "series": [
            {
                "name": "KOSPI",
                "type": "line",
                "data": kospi_values,
                "smooth": True,
                "showSymbol": False,
                "lineStyle": {"width": 1.5, "color": "#3b82f6"},
                "endLabel": {
                    "show": True,
                    "formatter": "KOSPI: {c}",
                    "offset": [10, 0],
                    "fontWeight": "bold",
                    "color": "#3b82f6"
                },
                "emphasis": {"focus": "series"}
            },
            {
                "name": "KOSDAQ",
                "type": "line",
                "yAxisIndex": 1,
                "data": kosdaq_values,
                "smooth": True,
                "showSymbol": False,
                "lineStyle": {"width": 1.5, "color": "#10b981"},
                "endLabel": {
                    "show": True,
                    "formatter": "KOSDAQ: {c}",
                    "offset": [10, 0],
                    "fontWeight": "bold",
                    "color": "#10b981"
                },
                "emphasis": {"focus": "series"}
            }
        ]
    }

    # 차트 렌더링
    st_echarts(options=options, height="400px", key="kospi_kosdaq_synced_v3")

if __name__ == "__main__":
    main()