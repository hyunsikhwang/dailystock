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
st.set_page_config(page_title="KOSPI & KOSDAQ 실시간 지수 (pyecharts)", layout="wide")

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

def main():
    st.title("🏃‍♂️ KOSPI & KOSDAQ 실시간 지수 (pyecharts)")
    
    today_str = get_today_str()
    st.write(f"기준 날짜: {today_str} (한국 시간)")

    with st.spinner('데이터를 불러오고 있습니다...'):
        df_kospi = fetch_index_data("KOSPI", today_str)
        df_kosdaq = fetch_index_data("KOSDAQ", today_str)

    if df_kospi.empty and df_kosdaq.empty:
        st.info("📌 현재는 주가 정보가 없습니다. (휴장일이거나 데이터 로딩 실패)")
        return

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

    kospi_values = [clean_value(v) for v in merged['KOSPI']]
    kosdaq_values = [clean_value(v) for v in merged['KOSDAQ']]

    # Y축 범위 계산
    k_min, k_max = calculate_y_axis_bounds(kospi_values)
    q_min, q_max = calculate_y_axis_bounds(kosdaq_values)

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

    # pyecharts 차트 생성
    line = (
        Line(init_opts=opts.InitOpts(height="400px", width="100%"))
        .add_xaxis(xaxis_data=full_timeline)
        .add_yaxis(
            series_name="KOSPI",
            y_axis=kospi_values,
            yaxis_index=0,
            is_smooth=True,
            symbol="none",
            linestyle_opts=opts.LineStyleOpts(width=1.5, color="#3b82f6"),
            label_opts=opts.LabelOpts(is_show=False),
            # 최고/최저점 표시 추가
            markpoint_opts=opts.MarkPointOpts(
                data=[
                    opts.MarkPointItem(type_="max", name="최고점", itemstyle_opts=opts.ItemStyleOpts(color="#ef4444")),
                    opts.MarkPointItem(type_="min", name="최저점", itemstyle_opts=opts.ItemStyleOpts(color="#3b82f6")),
                ]
            ),
        )
        .add_yaxis(
            series_name="KOSDAQ",
            y_axis=kosdaq_values,
            yaxis_index=1,
            is_smooth=True,
            symbol="none",
            linestyle_opts=opts.LineStyleOpts(width=1.5, color="#10b981"),
            label_opts=opts.LabelOpts(is_show=False),
            # 최고/최저점 표시 추가
            markpoint_opts=opts.MarkPointOpts(
                data=[
                    opts.MarkPointItem(type_="max", name="최고점", itemstyle_opts=opts.ItemStyleOpts(color="#ef4444")),
                    opts.MarkPointItem(type_="min", name="최저점", itemstyle_opts=opts.ItemStyleOpts(color="#2563eb")),
                ]
            ),
        )
        .extend_axis(
            yaxis=opts.AxisOpts(
                name="KOSDAQ",
                type_="value",
                min_=q_min,
                max_=q_max,
                position="right",
                is_scale=True,
                splitline_opts=opts.SplitLineOpts(is_show=False),
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="지수 실시간 추이 (시작점 동기화)"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="line"),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                boundary_gap=False,
                axislabel_opts=opts.LabelOpts(interval=29), # 30분 단위
            ),
            yaxis_opts=opts.AxisOpts(
                name="KOSPI",
                type_="value",
                min_=k_min,
                max_=k_max,
                is_scale=True,
                splitline_opts=opts.SplitLineOpts(is_show=True),
            ),
            legend_opts=opts.LegendOpts(pos_top="5%"),
        )
    )
    
    # 원시 옵션을 통해 pyecharts에서 직접 지원하지 않는 속성 주입
    line.options["series"][0]["endLabel"] = {
        "show": True,
        "formatter": "KOSPI: {c}",
        "offset": [10, 0],
        "fontWeight": "bold",
        "color": "#3b82f6"
    }
    line.options["series"][1]["endLabel"] = {
        "show": True,
        "formatter": "KOSDAQ: {c}",
        "offset": [10, 0],
        "fontWeight": "bold",
        "color": "#10b981"
    }
    # 애니메이션 강제 적용 및 레이블 겹침 방지
    line.options["animation"] = True
    line.options["animationDuration"] = 10000
    line.options["animationThreshold"] = 0
    line.options["series"][0]["labelLayout"] = {"moveOverlap": "shiftY"}
    line.options["series"][1]["labelLayout"] = {"moveOverlap": "shiftY"}

    st_pyecharts(line, height="400px")

if __name__ == "__main__":
    main()