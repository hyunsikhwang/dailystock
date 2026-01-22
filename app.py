import streamlit as st
from streamlit_echarts import st_echarts, JsCode
import requests
import pandas as pd
from datetime import datetime
import pytz

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

    # Y축 데이터 (NaN을 Python None으로 확실하게 변환하여 JSON 에러 방지)
    # merged.where 대신 리스트 컴프리헨션 사용
    times = [f"{str(x)[8:10]}:{str(x)[10:12]}" for x in merged['thistime']]
    kospi_values = [float(v) if pd.notnull(v) else None for v in merged['KOSPI']]
    kosdaq_values = [float(v) if pd.notnull(v) else None for v in merged['KOSDAQ']]

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
    options = {
        "animation": True,
        "animationDuration": 20000,
        "animationEasing": "linear",
        "animationThreshold": 2000,
        "title": {"text": "실시간 지수 추이 (천천히 그리기)"},
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
                "animationDuration": 20000,
                "animationEasing": "linear",
                "animationDelay": JsCode("function (idx) { return idx * 50; }")
            },
            {
                "name": "KOSDAQ",
                "type": "line",
                "yAxisIndex": 1,
                "data": kosdaq_values,
                "smooth": True,
                "showSymbol": False,
                "lineStyle": {"width": 3, "color": "#91cc75"},
                "animationDuration": 20000,
                "animationEasing": "linear",
                "animationDelay": JsCode("function (idx) { return idx * 50; }")
            }
        ]
    }

    # 차트 렌더링
    st_echarts(options=options, height="600px", key="kospi_kosdaq_chart")

if __name__ == "__main__":
    main()