import streamlit as st
from streamlit_echarts import st_echarts
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
        # 시간 정렬을 위해 datetime 변환
        df['dt'] = pd.to_datetime(df['thistime'], format='%Y%m%d%H%M%S')
        return df.sort_values('dt')
    except Exception as e:
        st.error(f"{index_type} 데이터를 가져오는 중 오류 발생: {e}")
        return pd.DataFrame()

def main():
    st.title("📊 KOSPI & KOSDAQ 실시간 지수 (애니메이션)")
    
    today_str = get_today_str()
    st.write(f"기준 날짜: {today_str} (한국 시간)")

    with st.spinner('데이터를 불러오고 있습니다...'):
        df_kospi = fetch_index_data("KOSPI", today_str)
        df_kosdaq = fetch_index_data("KOSDAQ", today_str)

    if df_kospi.empty and df_kosdaq.empty:
        st.info("📌 현재는 주가 정보가 없습니다. (휴장일이거나 데이터 로딩 실패)")
        return

    # 두 데이터프레임을 시간(thistime) 기준으로 병합 (시간축 동기화)
    # 한쪽만 있을 경우를 대비해 outer join
    merged = pd.merge(
        df_kospi[['thistime', 'nowVal']].rename(columns={'nowVal': 'KOSPI'}),
        df_kosdaq[['thistime', 'nowVal']].rename(columns={'nowVal': 'KOSDAQ'}),
        on='thistime',
        how='outer'
    ).sort_values('thistime')

    # X축: 시간 (HH:MM 형식)
    times = merged['thistime'].apply(lambda x: f"{str(x)[8:10]}:{str(x)[10:12]}").tolist()
    
    # Y축 데이터 (NaN은 null로 처리되어 ECharts에서 끊김 없이 표현됨)
    kospi_values = merged['KOSPI'].astype(float).tolist()
    kosdaq_values = merged['KOSDAQ'].astype(float).tolist()

    # ECharts 옵션 설정
    # 애니메이션 효과 극대화를 위해 포인트별 delay 함수 사용
    options = {
        "title": {"text": "실시간 지수 추이"},
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
                # 애니메이션 핵심 설정
                "animationDuration": 15000,
                "animationEasing": "linear",
                # 각 포인트가 그려지는 딜레이를 계산하여 '그려지는' 효과 생성
                "animationDelay": "function (idx) { return idx * 30; }"
            },
            {
                "name": "KOSDAQ",
                "type": "line",
                "yAxisIndex": 1, # KOSDAQ은 오른쪽 Y축 기준 (지수 폭이 다르므로)
                "data": kosdaq_values,
                "smooth": True,
                "showSymbol": False,
                "lineStyle": {"width": 3, "color": "#91cc75"},
                "animationDuration": 15000,
                "animationEasing": "linear",
                "animationDelay": "function (idx) { return idx * 30; }"
            }
        ]
    }

    # 차트 렌더링
    st_echarts(options=options, height="600px")
    
    # 하단 정보
    if not df_kospi.empty:
        curr_kospi = df_kospi.iloc[-1]
        st.metric("KOSPI 현재가", f"{float(curr_kospi['nowVal']):,.2f}", f"{curr_kospi['changeVal']} ({curr_kospi['changeRate']}%)")
    
    if not df_kosdaq.empty:
        curr_kosdaq = df_kosdaq.iloc[-1]
        st.metric("KOSDAQ 현재가", f"{float(curr_kosdaq['nowVal']):,.2f}", f"{curr_kosdaq['changeVal']} ({curr_kosdaq['changeRate']}%)", delta_color="normal")

if __name__ == "__main__":
    main()
