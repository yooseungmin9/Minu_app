import requests
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static

st.title("미세먼지 모니터링")

# 사이드바 - 지역 선택 기능
st.sidebar.header("🌍 지역 선택")

# 지역 옵션 정의
regions = {
    '서울': 'Seoul',
    '대구': 'Daegu', 
    '부산': 'Busan',
    '인천': 'Incheon',
    '광주': 'Gwangju',
    '대전': 'Daejeon',
    '울산': 'Ulsan',
    '경기': 'Gyeonggi',
    '강원': 'Gangwon',
    '충북': 'Chungbuk',
    '충남': 'Chungnam',
    '전북': 'Jeonbuk',
    '전남': 'Jeonnam',
    '경북': 'Gyeongbuk',
    '경남': 'Gyeongnam',
    '제주': 'Jeju',
    '세종': 'Sejong'
}

# 기본값을 대구로 설정
default_region = '대구'
selected_region = st.sidebar.selectbox(
    "지역을 선택하세요:",
    options=list(regions.keys()),
    index=list(regions.keys()).index(default_region)
)

# 선택된 지역에 따른 좌표 설정
region_coords = {
    '서울': [37.5665, 126.9780],
    '대구': [35.8667, 128.6000],
    '부산': [35.1796, 129.0756],
    '인천': [37.4563, 126.7052],
    '광주': [35.1595, 126.8526],
    '대전': [36.3504, 127.3845],
    '울산': [35.5384, 129.3114],
    '경기': [37.4138, 127.5183],
    '강원': [37.8228, 128.1555],
    '충북': [36.8, 127.7],
    '충남': [36.5, 126.8],
    '전북': [35.7, 127.1],
    '전남': [34.8, 126.9],
    '경북': [36.4, 128.9],
    '경남': [35.4, 128.3],
    '제주': [33.4996, 126.5312],
    '세종': [36.4800, 127.2890]
}

# 현재 선택된 지역 정보 표시
st.sidebar.info(f"📍 현재 선택: **{selected_region}**")

# 함수들 정의
@st.cache_data
def get_station_coordinates(region_name):
    station_url = "http://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getMsrstnList"
    station_params = {
        'addr': region_name,
        'pageNo': 1,
        'numOfRows': 100,
        'returnType': 'JSON',
        'serviceKey': 'L5PyqDviKAL0jSdGt5iPksot8IwBbYS7R27iyt6kKB0q6A+A2TS6Cn/cJ5CCsBWFPB/M+pgxnZwQiAhp9+TQ0A=='
    }
    
    try:
        response = requests.get(station_url, params=station_params)
        station_data = response.json()
        
        coords_dict = {}
        if 'response' in station_data and 'body' in station_data['response']:
            stations = station_data['response']['body']['items']
            for station in stations:
                if station.get('dmX') and station.get('dmY'):
                    coords_dict[station['stationName']] = [
                        float(station['dmY']),  # 위도
                        float(station['dmX'])   # 경도
                    ]
        return coords_dict
    except Exception as e:
        st.error(f"측정소 좌표 API 오류: {e}")
        return {}

def convert_coordinates(api_coords):
    converted_coords = {}
    for station_name, coords in api_coords.items():
        converted_coords[station_name] = [coords[1], coords[0]]  # [위도, 경도]로 순서 변경
    return converted_coords

def get_dust_data(region_name):
    url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"
    params = {
        'sidoName': region_name,
        'pageNo': 1,
        'numOfRows': 100,
        'returnType': 'JSON',
        'serviceKey': 'L5PyqDviKAL0jSdGt5iPksot8IwBbYS7R27iyt6kKB0q6A+A2TS6Cn/cJ5CCsBWFPB/M+pgxnZwQiAhp9+TQ0A==',
        'ver': '1.3'
    }
    
    try:
        response = requests.get(url, params=params)
        dust_data = response.json()
        
        if 'response' in dust_data and 'body' in dust_data['response']:
            items = dust_data['response']['body']['items']
            return pd.DataFrame(items)
        else:
            st.error(f"{region_name} 대기오염 데이터를 가져올 수 없습니다.")
            return None
    except Exception as e:
        st.error(f"대기오염 API 오류: {e}")
        return None

# 메인 화면
col1, col2 = st.columns(2)

# 세션 상태 초기화
if 'map_data' not in st.session_state:
    st.session_state.map_data = None
if 'current_region' not in st.session_state:
    st.session_state.current_region = None

with col1:
    # 지역이 변경되었거나 업데이트 버튼을 클릭했을 때
    if (st.button("🔄 지도 업데이트") or 
        st.session_state.current_region != selected_region):
        
        with st.spinner(f"{selected_region} 데이터를 불러오는 중..."):
            # 좌표 데이터 가져오기
            station_coords = get_station_coordinates(selected_region)
            converted_coords = convert_coordinates(station_coords)
            
            # 미세먼지 데이터 가져오기
            df = get_dust_data(selected_region)
            
            if df is not None and len(df) > 0:
                # 선택된 지역의 중심 좌표
                center_coords = region_coords.get(selected_region, [37.5665, 126.9780])
                
                # 지도 생성
                m = folium.Map(location=center_coords, zoom_start=11)
                
                # 측정시간 정보 추가
                latest_time = df.iloc[0].get('dataTime', '정보없음')
                title_html = f'''
                <h3 align="center" style="font-size:20px"><b>{selected_region} 미세먼지 현황</b></h3>
                <p align="center" style="font-size:14px; color:gray">측정시간: {latest_time}</p>
                '''
                m.get_root().html.add_child(folium.Element(title_html))
                
                # 측정소별 마커 추가
                valid_data_count = 0
                total_pm10 = 0
                
                for idx, row in df.iterrows():
                    try:
                        pm10_value = float(row['pm10Value']) if row['pm10Value'] not in ['-', ''] else 0
                        station_name = row['stationName']
                        data_time = row.get('dataTime', '정보없음')
                        
                        if pm10_value > 0:
                            total_pm10 += pm10_value
                            valid_data_count += 1
                        
                        # 색상 설정
                        if pm10_value > 80:
                            color = 'red'
                        elif pm10_value > 50:
                            color = 'orange'
                        elif pm10_value > 30:
                            color = 'green'
                        else:
                            color = 'blue'
                        
                        # 좌표 설정
                        coords = converted_coords.get(station_name, center_coords)
                        
                        # 팝업 HTML
                        popup_html = f"""
                        <div style="width: 200px;">
                            <h4><b>{station_name}</b></h4>
                            <p><b>미세먼지:</b> {pm10_value}㎍/㎥</p>
                            <p><b>측정시간:</b> {data_time}</p>
                        </div>
                        """
                        
                        folium.Marker(
                            location=coords,
                            popup=folium.Popup(popup_html, max_width=250),
                            tooltip=f"{station_name} 클릭하세요",
                            icon=folium.Icon(color=color)
                        ).add_to(m)
                        
                    except Exception as e:
                        st.warning(f"{station_name} 데이터 처리 오류: {e}")
                
                # 세션 상태에 저장
                st.session_state.map_data = {
                    'map': m,
                    'df': df,
                    'station_count': len(df),
                    'avg_pm10': total_pm10 / valid_data_count if valid_data_count > 0 else 0,
                    'latest_time': latest_time,
                    'region': selected_region
                }
                st.session_state.current_region = selected_region
                
                st.success(f"✅ {selected_region} 지도가 업데이트되었습니다! (총 {len(df)}개 측정소)")
            else:
                st.error(f"❌ {selected_region} 데이터를 가져오는데 실패했습니다.")

with col2:
    if st.session_state.map_data:
        avg_pm10 = st.session_state.map_data['avg_pm10']
        station_count = st.session_state.map_data['station_count']
        region = st.session_state.map_data['region']
        
        st.metric(f"{region} 평균 미세먼지", f"{avg_pm10:.1f} ㎍/㎥")
        st.metric("측정소 수", f"{station_count}개")
    else:
        st.metric("평균 미세먼지", "데이터 없음")
        st.metric("측정소 수", "0개")

# 지도 표시
st.subheader(f"📍 {selected_region} 실시간 미세먼지 지도")

if st.session_state.map_data:
    folium_static(st.session_state.map_data['map'], width=700, height=500)
    
    # 추가 정보 표시
    st.info(f"📅 최신 측정시간: {st.session_state.map_data['latest_time']}")
    
    # 범례
    st.markdown("""
    **🎨 색상 범례:**
    - 🔵 **파란색**: 좋음 (0-30㎍/㎥) 
    - 🟢 **초록색**: 보통 (31-50㎍/㎥) 나쁨 (51-80㎍/㎥)
    - 🟠 **주황색**: 나쁨 (51-80㎍/㎥) 매우나쁨 (81㎍/㎥ 이상)
    - 🔴 **빨간색**: 매우나쁨 (81㎍/㎥ 이상)
    """)
else:
    st.info(f"👆 '{selected_region}' 지역의 미세먼지 정보를 보려면 '지도 업데이트' 버튼을 클릭하세요!")