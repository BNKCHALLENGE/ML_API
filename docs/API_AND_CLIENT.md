# API 서버 & 클라이언트 가이드

## FastAPI 추천 서버 (`api_server.py`)
- **역할:** 실시간 추천 API 제공, `model_v2.pkl` + `missions.csv`를 로드하여 모든 미션을 순위화
- **주요 기술:** FastAPI, Pydantic v2, Uvicorn, pandas/numpy, LightGBM

### Pydantic 모델
```python
class UserContext(BaseModel):
    user_id: str
    age: int
    gender: str  # "M" | "F"
    last_lat: float
    last_lon: float
    pref_tags: List[str]
    acceptance_rate: float
    active_time_slot: str  # Morning/Day/Evening/Night
    current_hour: int
    current_day_of_week: int  # 0=월 ~ 6=일
    current_weather: str  # Sunny/Cloudy/Rainy/Snowy
```

```python
class MissionRecommendation(BaseModel):
    rank: int
    mission_id: str
    title: str
    category: str # 가능한 값: ["Food", "Cafe", "Tourist", "Culture", "Festival", "Walk", "Shopping", "Self-Dev", "Sports"]
    distance_m: float
    priority_weight: int
    model_proba: float
    final_score: float
```

```python
class RecommendationResponse(BaseModel):
    user_id: str
    timestamp: str
    total_missions: int
    recommendations: List[MissionRecommendation]
```

### 헬퍼 함수
- `haversine_distance()`: 사용자와 미션 간 거리를 미터 단위로 계산
- `categorize_time()`: 시(hour) → Morning/Day/Evening/Night로 변환

### Startup 이벤트
```python
@app.on_event("startup")
async def load_model_and_data():
    # model_v2.pkl과 missions.csv 로드
    # feature_cols = [...] 정의
```

### 엔드포인트
- **POST `/recommend`**: 모든 미션 Feature 생성 → LightGBM 추론 → Priority Weight로 final_score 계산 → 내림차순 정렬 후 rank 부여
- **GET `/missions`**: `missions.csv` 내용을 그대로 반환
- **GET `/health`**: 모델/데이터 로드 상태 확인
- **GET `/`**: 엔드포인트 및 API 정보 안내

### Swagger / 문서화
- `http://localhost:8000/docs`에서 대화형 문서 사용 가능 (모든 필드 설명 및 예시 포함)

### CORS 설정
- 기본값: `allow_origins=["*"]` (개발용), 운영 시에는 허용 도메인을 명시적으로 제한 필요

### 실행 방법
```bash
python api_server.py
# 혹은
uvicorn api_server:app --reload
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 미션 확장
- **기존 카테고리:** `missions.csv`에 행 추가 후 서버 재시작
- **새 카테고리:** CSV 추가 + `category_mapping` 확장 + 모델 재학습 필요

```python
category_mapping = {
    'Cafe': 0, 'Culture': 1, 'Festival': 2, 'Food': 3,
    'Self-Dev': 4, 'Shopping': 5, 'Sports': 6, 'Tourist': 7, 'Walk': 8,
    'Health': 9  # 예시
}
```

## 테스트 클라이언트 (`test_client.py`)
### RecommendationClient
```python
class RecommendationClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def health_check(self) -> bool:
        ...

    def get_recommendations(self, user_context: dict) -> dict:
        ...

    def get_top_n_recommendations(self, user_context: dict, n: int) -> List[dict]:
        ...
```

### 시나리오 예시
1. **부산대 근처 유저** – (35.23, 129.08), 25세 남성, 선호 Food/Cafe/Self-Dev, 수요일 14시 Sunny → 인근 Food/Cafe 미션이 상위 랭크
2. **해운대 동백섬 유저** – (35.1588, 129.1345), 28세 여성, Tourist/Walk/Culture 선호, 토요일 15시 Cloudy → 산책/관광 미션 상위

출력은 UI 친화적 ASCII 포맷으로 Top5를 표시하며 거리/우선도/확률/최종 점수를 함께 보여줍니다.

## Backend 연동 예시
```python
# Request.py
import requests
from datetime import datetime

class RecommendationAPI:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def get_recommendations(self, user_data, weather_api_key=None):
        now = datetime.now()
        payload = {
            "user_id": user_data['id'],
            "age": user_data['age'],
            "gender": user_data['gender'],
            "last_lat": user_data['current_gps']['lat'],
            "last_lon": user_data['current_gps']['lon'],
            "pref_tags": user_data['preference_tags'],
            "acceptance_rate": user_data['acceptance_rate'],
            "active_time_slot": user_data['active_time_slot'],
            "current_hour": now.hour,
            "current_day_of_week": now.weekday(),
            "current_weather": self._get_weather(user_data['current_gps'], weather_api_key)
        }
        res = requests.post(f"{self.base_url}/recommend", json=payload, timeout=5)
        res.raise_for_status()
        return res.json()

    def get_top_n(self, user_data, n=5):
        return self.get_recommendations(user_data)["recommendations"][:n]

    def _get_weather(self, gps, api_key):
        return "Sunny"
```

### Backend 활용 패턴
```python
top5 = response['recommendations'][:5]
food_only = [m for m in response['recommendations'] if m['category'] == 'Food']
within_3km = [m for m in response['recommendations'] if m['distance_m'] <= 3000]
priority_missions = [m for m in response['recommendations'] if m['priority_weight'] >= 2]
```

이 문서는 서버/클라이언트/연동 측면의 모든 정보를 제공합니다.
