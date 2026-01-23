import streamlit as st
from pyecharts import options as opts
from pyecharts.charts import Line
from streamlit_echarts import st_pyecharts
import requests
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import pytz

# 페이지 설정
st.set_page_config(page_title="KOSPI & KOSDAQ 실시간 지수", layout="wide")

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
    if actual_date_str != selected_date.strftime('%Y%m%d'):
         st.warning(f"선택한 날짜 ({selected_date})에 데이터가 없어, 가장 최근 데이터가 있는 날짜 ({actual_date_str})로 조회합니다.")
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

    # 상단 지표
    col1, col2 = st.columns(2)
    with col1:
        if not df_kospi.empty:
            curr = df_kospi.sort_values('thistime', ascending=False).iloc[0]
            st.metric("KOSPI 현재가", f"{float(curr['nowVal']):,.2f}", f"{curr['changeVal']} ({curr['changeRate']}%)")
    with col2:
        if not df_kosdaq.empty:
            curr = df_kosdaq.sort_values('thistime', ascending=False).iloc[0]
            st.metric("KOSDAQ 현재가", f"{float(curr['nowVal']):,.2f}", f"{curr['changeVal']} ({curr['changeRate']}%)")

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
            title_opts=opts.TitleOpts(title="지수 실시간 추이"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="line"),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                boundary_gap=False,
                axislabel_opts=opts.LabelOpts(interval=29), # 30분 단위 축 레이블 유지
            ),
            yaxis_opts=opts.AxisOpts(
                name="KOSPI",
                type_="value",
                min_=k_min_bound,
                max_=k_max_bound,
                is_scale=True,
                splitline_opts=opts.SplitLineOpts(is_show=True),
            ),
            legend_opts=opts.LegendOpts(pos_top="5%"),
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
                {"name": "최저", "coord": [q_min_info[0], q_min_info[1]], "itemStyle": {"color": "#10b981"}, "label": {"formatter": f"최저\n{q_min_info[0]}\n{q_min_info[1]:,.2f}"}}
            ]
        }
    line.options["series"][1]["endLabel"] = {"show": True, "formatter": "KOSDAQ: {c}", "fontWeight": "bold", "color": "#10b981"}
    
    line.options["animation"] = True
    line.options["animationDuration"] = 10000
    line.options["animationThreshold"] = 0
    line.options["series"][0]["labelLayout"] = {"moveOverlap": "shiftY"}
    line.options["series"][1]["labelLayout"] = {"moveOverlap": "shiftY"}

    st_pyecharts(line, height="300px")

def main():
    st.title("🏃‍♂️ KOSPI & KOSDAQ 실시간 지수")

    # 날짜 선택 기능 추가
    seoul_tz = pytz.timezone('Asia/Seoul')
    today = datetime.now(seoul_tz).date()

    selected_date = st.date_input("날짜 선택", today)

    update_dashboard(selected_date)

if __name__ == "__main__":
    main()