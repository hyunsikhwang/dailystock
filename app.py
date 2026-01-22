import streamlit as st
from streamlit_echarts import st_echarts
import requests
import pandas as pd
from datetime import datetime
import pytz

# 페이지 설정
st.set_page_config(page_title="KOSPI 지수 실시간 차트", layout="wide")

def get_today_str():
    """한국 시간 기준 오늘 날짜를 YYYYMMDD 형식으로 반환"""
    seoul_tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(seoul_tz)
    return now.strftime('%Y%m%d')

def fetch_kospi_data(today_str):
    """네이버 증권 API를 통해 KOSPI 데이터를 가져옴"""
    url = f"https://stock.naver.com/api/domestic/indexSise/time?koreaIndexType=KOSPI&thistime={today_str}&startIdx=0&pageSize=500"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return None

def main():
    st.title("📊 KOSPI 지수 실시간 시각화 (ECharts)")
    
    today_str = get_today_str()
    st.write(f"기준 날짜: {today_str}")

    with st.spinner('데이터를 불러오고 있습니다...'):
        data = fetch_kospi_data(today_str)

    if not data:
        st.info("📌 현재는 주가 정보가 없습니다. (휴장일이거나 데이터 로딩 실패)")
        return

    # 데이터 가공
    # API는 최신 데이터가 앞에 오는 경우가 많으므로 시간 순서대로 정렬 (YYYYMMDDHHMMSS)
    df = pd.DataFrame(data)
    df['thistime_dt'] = pd.to_datetime(df['thistime'], format='%Y%m%d%H%M%S')
    df = df.sort_values('thistime_dt')

    # X축 (시간), Y축 (지수)
    times = df['thistime'].apply(lambda x: f"{x[8:10]}:{x[10:12]}").tolist()
    values = df['nowVal'].astype(float).tolist()

    # ECharts 옵션 설정
    options = {
        "animation": True,
        "animationDuration": 20000,
        "animationEasing": "linear",
        "title": {"text": "KOSPI 분단위 지수"},
        "tooltip": {
            "trigger": "axis",
            "formatter": "{b} <br/> 지수: {c}"
        },
        "xAxis": {
            "type": "category",
            "data": times,
            "boundaryGap": False
        },
        "yAxis": {
            "type": "value",
            "scale": True,  # 지수 범위에 맞춰 Y축 최솟값 자동 조절
            "splitLine": {"show": True}
        },
        "series": [
            {
                "data": values,
                "type": "line",
                "smooth": True,
                "showSymbol": False,
                "areaStyle": {
                    "color": "rgba(0, 128, 255, 0.1)"
                },
                "lineStyle": {
                    "width": 2,
                    "color": "#5470c6"
                },
                "animationDuration": 20000, # 시리즈별 애니메이션 지속 시간 (20초)
                "animationEasing": "linear"    # 일정한 속도로 그려지도록 선형(linear) 적용
            }
        ],
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "3%",
            "containLabel": True
        }
    }

    # 차트 렌더링
    st_echarts(options=options, height="500px")
    
    # 상세 데이터 테이블 (선택사항)
    with st.expander("실시간 데이터 상세 보기"):
        st.dataframe(df[['thistime', 'nowVal', 'changeVal', 'changeRate', 'quant']].rename(columns={
            'thistime': '시간',
            'nowVal': '현재가',
            'changeVal': '변비',
            'changeRate': '등락률',
            'quant': '거래량'
        }), use_container_width=True)

if __name__ == "__main__":
    main()
