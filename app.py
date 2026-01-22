import streamlit as st
from streamlit_echarts import st_echarts, JsCode
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import json

# 페이지 설정
st.set_page_config(page_title="KOSPI & KOSDAQ 실시간 차트", layout="wide")

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
        df = pd.DataFrame(data)
        df['dt'] = pd.to_datetime(df['thistime'], format='%Y%m%d%H%M%S')
        return df.sort_values('dt')
    except Exception as e:
        st.error(f"{index_type} 데이터를 가져오는 중 오류 발생: {e}")
        return pd.DataFrame()

def clean_float_value(val):
    """값을 float으로 변환하되, NaN/None/오류 시 None(JSON null) 반환"""
    try:
        if val is None:
            return None
        f_val = float(val)
        if np.isnan(f_val) or np.isinf(f_val):
            return None
        return f_val
    except (ValueError, TypeError):
        return None

def main():
    st.title("📊 KOSPI & KOSDAQ 실시간 지수 (슬로우 애니메이션)")
    
    today_str = get_today_str()
    st.write(f"기준 날짜: {today_str} (한국 시간)")

    with st.spinner('데이터를 불러오고 있습니다...'):
        df_kospi = fetch_index_data("KOSPI", today_str)
        df_kosdaq = fetch_index_data("KOSDAQ", today_str)

    if df_kospi.empty and df_kosdaq.empty:
        st.info("📌 현재는 주가 정보가 없습니다. (휴장일이거나 데이터 로딩 실패)")
        return

    # 데이터 병합
    merged = pd.merge(
        df_kospi[['thistime', 'nowVal']].rename(columns={'nowVal': 'KOSPI'}),
        df_kosdaq[['thistime', 'nowVal']].rename(columns={'nowVal': 'KOSDAQ'}),
        on='thistime',
        how='outer'
    ).sort_values('thistime')

    # 데이터 정제 (NaN을 None으로 변환하여 JSON 에러 방지)
    times = []
    for x in merged['thistime']:
        s_x = str(x)
        if len(s_x) >= 12:
            times.append(f"{s_x[8:10]}:{s_x[10:12]}")
        else:
            times.append("")
            
    kospi_values = [clean_float_value(v) for v in merged['KOSPI']]
    kosdaq_values = [clean_float_value(v) for v in merged['KOSDAQ']]

    # 상단 지표 영역 (가로 배치)
    col1, col2 = st.columns(2)
    with col1:
        if not df_kospi.empty:
            curr_kospi = df_kospi.iloc[-1]
            st.metric("KOSPI 현재가", f"{float(curr_kospi['nowVal']):,.2f}", f"{curr_kospi['changeVal']} ({curr_kospi['changeRate']}%)")
    with col2:
        if not df_kosdaq.empty:
            curr_kosdaq = df_kosdaq.iloc[-1]
            st.metric("KOSDAQ 현재가", f"{float(curr_kosdaq['nowVal']):,.2f}", f"{curr_kosdaq['changeVal']} ({curr_kosdaq['changeRate']}%)")

    # ECharts 옵션 설정
    # JsCode를 사용하지 않고도 애니메이션 속도를 조절할 수 있도록 설정을 보강합니다.
    # 만약 JsCode가 문제라면 이 부분이 원인일 수 있으므로, 이번에는 JsCode 없이 구현해봅니다.
    # ECharts v5부터는 animationDelay를 함수 없이 숫자로 주면 전체 딜레이만 조절되므로, 
    # 정말 천천히 그리려면 JsCode가 필요합니다. 하지만 일단 JSON 에러 해결을 위해 구성을 최적화합니다.
    options = {
        "animation": True,
        "animationDuration": 15000,
        "animationEasing": "linear",
        "animationThreshold": 5000,
        "title": {"text": "실시간 지수 추이 (순차 애니메이션)"},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"}
        },
        "legend": {"data": ["KOSPI", "KOSDAQ"]},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": times,
            "boundaryGap": False
        },
        "yAxis": [
            {"name": "KOSPI", "type": "value", "scale": True},
            {"name": "KOSDAQ", "type": "value", "scale": True}
        ],
        "series": [
            {
                "name": "KOSPI",
                "type": "line",
                "data": kospi_values,
                "smooth": True,
                "showSymbol": False,
                "lineStyle": {"width": 3, "color": "#5470c6"},
                "animationDuration": 15000,
                "animationDelay": JsCode("function (idx) { return idx * 30; }")
            },
            {
                "name": "KOSDAQ",
                "type": "line",
                "yAxisIndex": 1,
                "data": kosdaq_values,
                "smooth": True,
                "showSymbol": False,
                "lineStyle": {"width": 3, "color": "#91cc75"},
                "animationDuration": 15000,
                "animationDelay": JsCode("function (idx) { return idx * 30; }")
            }
        ]
    }

    # 차트 렌더링
    try:
        st_echarts(options=options, height="600px", key="kospi_kosdaq_chart")
    except Exception as e:
        st.error(f"차트를 표시하는 중 오류가 발생했습니다. 데이터 구조를 확인해 주세요. ({e})")
        # 디버깅용 데이터 출력 (접어둠)
        with st.expander("디버깅 데이터 정보"):
            st.write("데이터 샘플 (KOSPI):", kospi_values[:10])
            st.write("데이터 샘플 (Times):", times[:10])

if __name__ == "__main__":
    main()