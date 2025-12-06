# 모델 & 데이터 파이프라인

## BNK.ipynb 개요
- **목적:** 추천 시스템 전체 MLOps 파이프라인을 노트북 한 곳에서 실행
- **구성:** Step 0~9까지 연속 실행하며 합성 데이터 생성 → 모델 학습/평가 → 추론 데모 → 재학습 시뮬레이션까지 포함

## Step-by-Step
### Step 0. 환경 설정
- pandas, numpy, lightgbm, scikit-learn 등 필수 라이브러리 import
- 말굽고딕 폰트 등록 및 matplotlib 한글 깨짐 방지 설정
- 위경도 기반 거리 계산을 위한 Haversine 함수 정의

### Step 1. TB_MISSION 생성
- 부산 실존 위치 기반 23개 고정 미션 + 9개 카테고리(Food, Cafe, Tourist, Culture, Festival, Walk, Shopping, Self-Dev, Sports)
- 필수 필드: `mission_id`, `category`, `title`, `lat`, `lon`, `req_time_min`, `reward_amt`, `priority_weight`

### Step 2. 미션 우선도(Priority Weight)
- 운영 전략 반영: 0(1.0x) ~ 3(1.3x)
- 예) 지역 상권 1, 핵심 제휴 3
- 최종 점수: `FinalScore = P(model) × (1.0 + priority_weight × 0.1)`

### Step 3. TB_USER 생성
- 1,000명 부산 시민 프로필 (2024 인구 비율 반영)
- 속성: `user_id`, `age`, `gender`, `last_lat/lon`, `pref_tags`, `acceptance_rate`, `main_activity_zone`, `active_time_slot`

### Step 4. TB_USER_LOG 생성
- 10,000+ 합성 로그 생성
- Ground Truth 규칙: 거리/시간/날씨/취향/우선도/시간대 등 확률 가중치 조합
- 로그 label은 확률적 수락 여부

### Step 5. Feature Engineering (17개)
1. age
2. dist_m
3. dist_score = 1/(dist_m+100)
4. req_time_min
5. reward_amt
6. reward_efficiency = reward_amt/req_time_min
7. priority_weight
8. acceptance_rate
9. is_pref_match
10. is_active_time_match
11. is_outdoor_bad_weather
12. hour
13. day_of_week
14. gender_encoded
15. weather_encoded
16. time_slot_encoded
17. category_encoded

### Step 6. LightGBM 학습 (v1.0)
- Binary classification, objective `binary`, metric `auc`
- `n_estimators=200`, `learning_rate=0.05`, `max_depth=6`, `num_leaves=31`
- Train/Test 80/20 split, 중요도 시각화, Test AUC 약 0.85~0.90

### Step 7. Hybrid Filtering & Inference Demo
- 예시 유저(부산대 근처 25세 남성) 시나리오
- 모든 미션에 대해 `model_proba × priority_weight 보정`
- Top5 결과를 출력해 추천 품질 검증

### Step 8. MLOps Simulation
1. 신규 로그 500건 추가 수집 가정
2. TB_USER 누적 통계 업데이트 (`total_view_cnt`, `total_accept_cnt`, `acceptance_rate` 갱신)
3. v2.0 재학습 후 v1 vs v2 AUC 비교 → 지속적 개선 루프 확인

### Step 9. 모델/데이터 저장
- `model_v2.pkl`: 최종 LightGBM 모델을 pickle로 저장
- `missions.csv`: 미션 마스터 데이터를 CSV로 저장 → Serving에서 직접 사용

## missions.csv 가이드
- 컬럼: `mission_id, category, title, lat, lon, req_time_min, reward_amt, priority_weight, final_weight`
- 우선도에 따른 `final_weight`는 1.0~1.3
- 기존 카테고리 내 미션 추가는 CSV에 행만 추가하면 서버 재시작 시 자동 반영
- 새 카테고리 추가 시 `api_server.py`의 `category_mapping` 확장 + 모델 재학습 필요

```csv
mission_id,category,title,lat,lon,req_time_min,reward_amt,priority_weight,final_weight
M001,Food,자갈치시장 꼼장어 골목 방문,35.0968,129.0306,40,50,1,1.1
M005,Tourist,해운대 블루라인파크 해변열차 구경,35.1876,129.2068,10,100,2,1.2
M018,Self-Dev,부산은행 본점(BIFC) 금융센터 방문,35.1143,129.0476,60,300,3,1.3
```

## model_v2.pkl
- LightGBM binary classifier 직렬화 객체
- 17개 Feature 기반 학습, 10,000+ 로그 데이터 활용
- Load 예시:
```python
import pickle
with open('model_v2.pkl', 'rb') as f:
    model = pickle.load(f)
proba = model.predict_proba(X)[:, 1]
```

## 데이터 → 모델 재학습 절차
1. 운영 DB에서 추천 요청/피드백 로그 추출 (`docs/DATA_PIPELINE.md` 참고)
2. 합성 데이터와 merge, 중복 제거
3. Feature Engineering 파이프라인 재사용
4. 성능 비교 후 `model_v3.pkl`과 같이 버전 명명

이 문서는 모델링/데이터 생성과 관련된 모든 세부 정보를 다룹니다.
