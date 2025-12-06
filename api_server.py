"""
BNK 로컬 챌린지 추천 API 서버
FastAPI 기반 REST API

실행 방법:
    python api_server.py
    또는
    uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import numpy as np
import pickle
import uvicorn
from datetime import datetime

# FastAPI 앱 초기화
app = FastAPI(
    title="BNK 로컬 챌린지 추천 API",
    description="LightGBM 기반 미션 추천 시스템",
    version="1.0.0"
)

# CORS 설정 (Frontend와 연동 시 필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 데이터 모델 정의 (Request/Response) =====

class UserContext(BaseModel):
    """
    유저 정보 및 현재 컨텍스트
    
    추천 요청 시 필요한 모든 유저 정보와 상황 정보를 포함합니다.
    """
    user_id: str  # 유저 고유 ID (예: "U0001", "user_abc123")
    
    age: int  # 나이 (범위: 20~60, 금융 앱 주 사용층)
    
    gender: str  # 성별 (가능한 값: "M" | "F")
    
    last_lat: float  # 유저의 현재 GPS 위도 (예: 35.1588, 범위: 35.0~35.3 부산 지역)
    
    last_lon: float  # 유저의 현재 GPS 경도 (예: 129.1345, 범위: 128.9~129.3 부산 지역)
    
    pref_tags: List[str]  
    # 유저 선호 카테고리 리스트 (3~5개 권장)
    # 가능한 값: ["Food", "Cafe", "Tourist", "Culture", "Festival", "Walk", "Shopping", "Self-Dev", "Sports"]
    # 예시: ["Food", "Cafe", "Self-Dev"]
    
    acceptance_rate: float  
    # 유저의 누적 미션 수락률 (범위: 0.0~1.0)
    # 예: 0.15 = 15% 수락률
    # 신규 유저의 경우 0.1~0.2 권장
    
    active_time_slot: str  
    # 유저의 주 활동 시간대 (가능한 값: "Morning" | "Day" | "Evening" | "Night")
    # - "Morning": 06:00~11:59
    # - "Day": 12:00~17:59
    # - "Evening": 18:00~21:59
    # - "Night": 22:00~05:59
    
    # === 현재 상황 컨텍스트 ===
    current_hour: int  
    # 현재 시각 (범위: 0~23, 24시간 형식)
    # 예: 14 = 오후 2시
    
    current_day_of_week: int  
    # 요일 (범위: 0~6)
    # 0=월요일, 1=화요일, 2=수요일, 3=목요일, 4=금요일, 5=토요일, 6=일요일
    
    current_weather: str  
    # 현재 날씨 (가능한 값: "Sunny" | "Cloudy" | "Rainy" | "Snowy")
    # 실외 미션(Tourist, Walk, Sports, Festival)은 날씨에 민감

class MissionRecommendation(BaseModel):
    """
    추천 결과 (단일 미션)
    
    각 미션에 대한 추천 점수 및 메타데이터를 포함합니다.
    """
    mission_id: str  
    # 미션 고유 ID (형식: "M001"~"M023")
    
    title: str  
    # 미션 제목 (한글, 예: "부산대 앞 토스트 골목 간식타임")
    
    category: str  
    # 미션 카테고리 (가능한 값: "Food" | "Cafe" | "Tourist" | "Culture" | "Festival" | "Walk" | "Shopping" | "Self-Dev" | "Sports")
    
    distance_m: float  
    # 유저 현재 위치에서 미션 위치까지의 GPS 거리 (단위: 미터)
    # 예: 245.3 = 245.3m
    
    priority_weight: int  
    # 운영자가 설정한 우선도 가중치 (범위: 0~3)
    # 0=일반(1.0x), 1=약간중요(1.1x), 2=중요(1.2x), 3=매우중요(1.3x)
    
    model_proba: float  
    # LightGBM 모델이 예측한 수락 확률 (범위: 0.0~1.0)
    # 예: 0.785 = 78.5% 수락 확률
    
    final_score: float  
    # 최종 추천 점수 (계산식: model_proba × (1.0 + priority_weight × 0.1))
    # 이 값을 기준으로 내림차순 정렬됨
    # 예: 0.8635 = 0.785 × 1.1
    
    rank: int  
    # 추천 순위 (1~23, 1위가 최우선 추천)

class RecommendationResponse(BaseModel):
    """
    추천 API 응답
    
    전체 추천 결과를 담는 래퍼 객체입니다.
    """
    user_id: str  
    # 요청한 유저의 ID (요청 시 전달한 user_id와 동일)
    
    timestamp: str  
    # 추천 생성 시각 (ISO 8601 형식, 예: "2025-12-05T14:30:45")
    
    total_missions: int  
    # 추천된 미션 총 개수 (항상 23개)
    
    recommendations: List[MissionRecommendation]  
    # 추천 미션 리스트 (rank 1~23 순서대로 정렬됨)
    # 배열 길이: 23개 (모든 미션 포함)

# ===== 글로벌 변수 (모델 및 데이터 로드) =====

model = None
df_mission = None
feature_cols = None

def haversine_distance(lat1, lon1, lat2, lon2):
    """GPS 거리 계산 (미터)"""
    R = 6371000
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    
    a = np.sin(delta_phi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    
    return R * c

def categorize_time(hour):
    """시간대 범주화"""
    if 6 <= hour < 12:
        return 'Morning'
    elif 12 <= hour < 18:
        return 'Day'
    elif 18 <= hour < 22:
        return 'Evening'
    else:
        return 'Night'

@app.on_event("startup")
async def load_model_and_data():
    """서버 시작 시 모델 및 미션 데이터 로드"""
    global model, df_mission, feature_cols
    
    try:
        # 모델 로드 (pickle 파일)
        with open('model_v2.pkl', 'rb') as f:
            model = pickle.load(f)
        print("✅ 모델 로드 완료: model_v2.pkl")
        
        # 미션 데이터 로드 (CSV 파일)
        df_mission = pd.read_csv('missions.csv')
        print(f"✅ 미션 데이터 로드 완료: {len(df_mission)}개 미션")
        
        # Feature 컬럼 정의
        feature_cols = [
            'age', 'dist_m', 'dist_score', 'req_time_min', 'reward_amt', 
            'reward_efficiency', 'priority_weight', 'acceptance_rate',
            'is_pref_match', 'is_active_time_match', 'is_outdoor_bad_weather',
            'hour', 'day_of_week', 'gender_encoded', 'weather_encoded', 
            'time_slot_encoded', 'category_encoded'
        ]
        
        print("="*60)
        print("🚀 BNK 로컬 챌린지 추천 API 서버 시작!")
        print(f"📡 API 문서: http://localhost:8000/docs")
        print("="*60)
        
    except Exception as e:
        print(f"❌ 서버 시작 실패: {e}")
        raise

# ===== API 엔드포인트 =====

@app.get("/")
async def root():
    """
    ## API 루트 엔드포인트
    
    API 서버의 기본 정보와 사용 가능한 엔드포인트 목록을 반환합니다.
    
    ### Response
    
    - `service` (string): 서비스 이름
    - `status` (string): 서버 상태
    - `version` (string): API 버전
    - `endpoints` (object): 사용 가능한 엔드포인트
      - `docs` (string): Swagger UI 문서 경로
      - `recommend` (string): 추천 API 경로
      - `missions` (string): 미션 목록 API 경로
    
    ### Example Response
    
    ```json
    {
      "service": "BNK 로컬 챌린지 추천 API",
      "status": "running",
      "version": "1.0.0",
      "endpoints": {
        "docs": "/docs",
        "recommend": "/recommend (POST)",
        "missions": "/missions (GET)"
      }
    }
    ```
    """
    return {
        "service": "BNK 로컬 챌린지 추천 API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "recommend": "/recommend (POST)",
            "missions": "/missions (GET)"
        }
    }

@app.post("/recommend", response_model=RecommendationResponse)
async def recommend_missions(user_context: UserContext):
    """
    ## 미션 추천 API
    
    유저 정보와 현재 상황(위치, 시간, 날씨)을 기반으로 23개 미션의 추천 점수를 계산하여 순위를 반환합니다.
    
    ### Request Body: UserContext
    
    **필수 필드:**
    - `user_id` (string): 유저 고유 ID (예: "U0001", "user_abc123")
    - `age` (integer): 나이 (20~60)
    - `gender` (string): 성별, **"M"** 또는 **"F"**
    - `last_lat` (float): 현재 GPS 위도 (35.0~35.3, 부산 지역)
    - `last_lon` (float): 현재 GPS 경도 (128.9~129.3, 부산 지역)
    - `pref_tags` (array[string]): 선호 카테고리 리스트 (3~5개 권장)
      - 가능한 값: `["Food", "Cafe", "Tourist", "Culture", "Festival", "Walk", "Shopping", "Self-Dev", "Sports"]`
      - 예시: `["Food", "Cafe", "Self-Dev"]`
    - `acceptance_rate` (float): 유저 누적 수락률 (0.0~1.0, 신규 유저는 0.1~0.2 권장)
    - `active_time_slot` (string): 주 활동 시간대
      - **"Morning"** (06:00~11:59)
      - **"Day"** (12:00~17:59)
      - **"Evening"** (18:00~21:59)
      - **"Night"** (22:00~05:59)
    
    **현재 상황 필드:**
    - `current_hour` (integer): 현재 시각 (0~23, 24시간 형식)
    - `current_day_of_week` (integer): 요일 (0=월요일, 1=화요일, 2=수요일, 3=목요일, 4=금요일, 5=토요일, 6=일요일)
    - `current_weather` (string): 날씨
      - **"Sunny"** (맑음)
      - **"Cloudy"** (흐림)
      - **"Rainy"** (비)
      - **"Snowy"** (눈)
    
    ### Response: RecommendationResponse
    
    - `user_id` (string): 요청한 유저 ID
    - `timestamp` (string): 추천 생성 시각 (ISO 8601 형식)
    - `total_missions` (integer): 추천 미션 개수 (항상 23)
    - `recommendations` (array): 추천 미션 리스트 (rank 1~23 순서)
      - `mission_id` (string): 미션 ID (M001~M023)
      - `title` (string): 미션 제목 (한글)
      - `category` (string): 카테고리 (Food, Cafe, Tourist, Culture, Festival, Walk, Shopping, Self-Dev, Sports)
      - `distance_m` (float): GPS 거리 (미터)
      - `priority_weight` (integer): 우선도 (0=일반, 1=약간중요, 2=중요, 3=매우중요)
      - `model_proba` (float): 모델 예측 확률 (0.0~1.0)
      - `final_score` (float): 최종 점수 (model_proba × (1.0 + priority_weight × 0.1))
      - `rank` (integer): 추천 순위 (1~23)
    
    ### 알고리즘
    
    1. **거리 기반 필터링**: Haversine 공식으로 GPS 거리 계산
    2. **ML 예측**: LightGBM 모델로 수락 확률 예측 (17개 Feature)
    3. **Hybrid Filtering**: `model_proba × priority_boost` (비즈니스 우선도 반영)
    4. **정렬**: final_score 내림차순
    
    ### Example Request
    
    ```json
    {
      "user_id": "U0001",
      "age": 25,
      "gender": "M",
      "last_lat": 35.23,
      "last_lon": 129.08,
      "pref_tags": ["Food", "Cafe", "Self-Dev"],
      "acceptance_rate": 0.15,
      "active_time_slot": "Day",
      "current_hour": 14,
      "current_day_of_week": 2,
      "current_weather": "Sunny"
    }
    ```
    
    ### Example Response
    
    ```json
    {
      "user_id": "U0001",
      "timestamp": "2025-12-05T14:30:45",
      "total_missions": 23,
      "recommendations": [
        {
          "rank": 1,
          "mission_id": "M002",
          "title": "부산대 앞 토스트 골목 간식타임",
          "category": "Food",
          "distance_m": 245.3,
          "priority_weight": 0,
          "model_proba": 0.785,
          "final_score": 0.785
        },
        {
          "rank": 2,
          "mission_id": "M003",
          "title": "전포 카페거리 힙한 카페 찾기",
          "category": "Cafe",
          "distance_m": 1234.5,
          "priority_weight": 0,
          "model_proba": 0.652,
          "final_score": 0.652
        }
        // ... (총 23개 미션)
      ]
    }
    ```
    
    ### Backend 활용 예시
    
    **Top 5만 표시:**
    ```python
    top_5 = response['recommendations'][:5]
    ```
    
    **Top 10만 표시:**
    ```python
    top_10 = response['recommendations'][:10]
    ```
    
    **특정 카테고리만 필터링 (Food 미션만):**
    ```python
    food_missions = [m for m in response['recommendations'] if m['category'] == 'Food']
    ```
    
    **거리 기반 필터링 (3km 이내만):**
    ```python
    nearby = [m for m in response['recommendations'] if m['distance_m'] <= 3000]
    ```
    
    **높은 우선도 미션만 (priority_weight >= 2):**
    ```python
    priority_missions = [m for m in response['recommendations'] if m['priority_weight'] >= 2]
    ```
    
    **모델 예측 확률 70% 이상만:**
    ```python
    high_confidence = [m for m in response['recommendations'] if m['model_proba'] >= 0.7]
    ```
    
    ### 참고사항
    
    - 응답에는 **항상 23개 미션 전체**가 포함됩니다
    - `rank` 필드는 1~23 순서로 정렬되어 있습니다
    - Backend에서 필요한 만큼만 슬라이싱하여 사용하세요
    - 추가 필터링은 Backend 로직에서 자유롭게 구현 가능합니다
    """
    
    if model is None or df_mission is None:
        raise HTTPException(status_code=500, detail="모델 또는 데이터가 로드되지 않았습니다.")
    
    # 카테고리 인코딩 매핑 (학습 시 사용한 순서와 동일해야 함)
    category_mapping = {
        'Cafe': 0, 'Culture': 1, 'Festival': 2, 'Food': 3,
        'Self-Dev': 4, 'Shopping': 5, 'Sports': 6, 'Tourist': 7, 'Walk': 8
    }
    
    recommendation_results = []
    
    # 모든 미션에 대해 추천 점수 계산
    for _, mission in df_mission.iterrows():
        # 1. 거리 계산
        dist_m = haversine_distance(
            user_context.last_lat, user_context.last_lon,
            mission['lat'], mission['lon']
        )
        dist_score = 1 / (dist_m + 100)
        
        # 2. 보상 효율성
        reward_efficiency = mission['reward_amt'] / mission['req_time_min']
        
        # 3. 취향 일치
        is_pref_match = 1 if mission['category'] in user_context.pref_tags else 0
        
        # 4. 시간대 매칭
        time_slot = categorize_time(user_context.current_hour)
        is_active_time_match = 1 if time_slot == user_context.active_time_slot else 0
        
        # 5. 날씨-카테고리 상호작용
        outdoor_categories = ['Tourist', 'Walk', 'Sports', 'Festival']
        is_outdoor_bad_weather = 1 if (
            mission['category'] in outdoor_categories and 
            user_context.current_weather in ['Rainy', 'Snowy']
        ) else 0
        
        # 6. 범주형 변수 인코딩
        gender_encoded = 0 if user_context.gender == 'M' else 1
        weather_encoded = {'Sunny': 0, 'Cloudy': 1, 'Rainy': 2, 'Snowy': 3}[user_context.current_weather]
        time_slot_encoded = {'Morning': 0, 'Day': 1, 'Evening': 2, 'Night': 3}[time_slot]
        category_encoded = category_mapping.get(mission['category'], 0)
        
        # 7. Feature 벡터 구성
        features = pd.DataFrame([{
            'age': user_context.age,
            'dist_m': dist_m,
            'dist_score': dist_score,
            'req_time_min': mission['req_time_min'],
            'reward_amt': mission['reward_amt'],
            'reward_efficiency': reward_efficiency,
            'priority_weight': mission['priority_weight'],
            'acceptance_rate': user_context.acceptance_rate,
            'is_pref_match': is_pref_match,
            'is_active_time_match': is_active_time_match,
            'is_outdoor_bad_weather': is_outdoor_bad_weather,
            'hour': user_context.current_hour,
            'day_of_week': user_context.current_day_of_week,
            'gender_encoded': gender_encoded,
            'weather_encoded': weather_encoded,
            'time_slot_encoded': time_slot_encoded,
            'category_encoded': category_encoded
        }])
        
        # 8. 모델 예측
        pred_proba = model.predict_proba(features[feature_cols])[:, 1][0]
        
        # 9. Hybrid Filtering: 비즈니스 우선도 반영
        priority_boost = 1.0 + mission['priority_weight'] * 0.1
        final_score = pred_proba * priority_boost
        
        recommendation_results.append({
            'mission_id': mission['mission_id'],
            'title': mission['title'],
            'category': mission['category'],
            'distance_m': round(dist_m, 1),
            'priority_weight': int(mission['priority_weight']),
            'model_proba': round(float(pred_proba), 4),
            'final_score': round(float(final_score), 4)
        })
    
    # 최종 점수 기준 정렬
    sorted_results = sorted(recommendation_results, key=lambda x: x['final_score'], reverse=True)
    
    # 랭킹 부여
    for rank, result in enumerate(sorted_results, start=1):
        result['rank'] = rank
    
    # 응답 반환
    return RecommendationResponse(
        user_id=user_context.user_id,
        timestamp=datetime.now().isoformat(),
        total_missions=len(sorted_results),
        recommendations=sorted_results
    )

@app.get("/missions")
async def get_all_missions():
    """
    ## 미션 목록 조회 API
    
    등록된 전체 23개 미션의 상세 정보를 반환합니다.
    
    ### Response
    
    - `total` (integer): 미션 총 개수 (23)
    - `missions` (array): 미션 리스트
      - `mission_id` (string): 미션 ID (M001~M023)
      - `category` (string): 카테고리
        - 가능한 값: `Food`, `Cafe`, `Tourist`, `Culture`, `Festival`, `Walk`, `Shopping`, `Self-Dev`, `Sports`
      - `title` (string): 미션 제목 (한글)
      - `lat` (float): GPS 위도
      - `lon` (float): GPS 경도
      - `req_time_min` (integer): 소요 시간 (분)
      - `reward_amt` (integer): 보상 금액 (원)
      - `priority_weight` (integer): 우선도 (0~3)
      - `final_weight` (float): 계산된 가중치 (1.0~1.3)
    
    ### Example Response
    
    ```json
    {
      "total": 23,
      "missions": [
        {
          "mission_id": "M001",
          "category": "Food",
          "title": "자갈치시장 꼼장어 골목 방문",
          "lat": 35.0968,
          "lon": 129.0306,
          "req_time_min": 40,
          "reward_amt": 50,
          "priority_weight": 1,
          "final_weight": 1.1
        }
      ]
    }
    ```
    """
    if df_mission is None:
        raise HTTPException(status_code=500, detail="미션 데이터가 로드되지 않았습니다.")
    
    return {
        "total": len(df_mission),
        "missions": df_mission.to_dict(orient='records')
    }

@app.get("/health")
async def health_check():
    """
    ## 서버 상태 체크 API
    
    API 서버의 헬스 상태와 로드된 모델/데이터 정보를 반환합니다.
    
    ### Response
    
    - `status` (string): 서버 상태 ("healthy" | "unhealthy")
    - `model_loaded` (boolean): 모델 로드 여부
    - `missions_loaded` (boolean): 미션 데이터 로드 여부
    - `mission_count` (integer): 로드된 미션 개수
    
    ### Example Response
    
    ```json
    {
      "status": "healthy",
      "model_loaded": true,
      "missions_loaded": true,
      "mission_count": 23
    }
    ```
    """
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "missions_loaded": df_mission is not None,
        "mission_count": len(df_mission) if df_mission is not None else 0
    }

# ===== 서버 실행 =====

if __name__ == "__main__":
    import os
    # Railway는 PORT 환경변수로 포트를 지정함
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
