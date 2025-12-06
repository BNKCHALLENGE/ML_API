# 데이터 수집 & 파이프라인 가이드

## 로그 수집 대상
추천 시스템 운영 시 Backend는 아래 두 가지 이벤트를 저장해야 합니다.
1. **추천 요청 로그** – `/recommend` 호출 시점의 컨텍스트 기록
2. **미션 피드백 로그** – 사용자가 각 미션을 수락/거절/무시할 때의 상호작용

---

## 추천 요청 로그 (`recommendation_requests`)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| log_id | BIGSERIAL PK | 로그 고유 ID |
| user_id | VARCHAR(50) | 사용자 ID |
| request_timestamp | TIMESTAMP | 요청 시각 |
| gender | VARCHAR(1) | "M" or "F" |
| age | INT | 나이 |
| user_lat / user_lon | DECIMAL | 사용자 위치 |
| current_weather | VARCHAR(20) | Sunny/Cloudy/Rainy/Snowy |
| current_day_of_week | INT | 0=월 ~ 6=일 |
| pref_tags | JSON | 선호 카테고리 배열 |
| acceptance_rate | DECIMAL(5,4) | 누적 수락률 |
| active_time_slot | VARCHAR(20) | Morning/Day/Evening/Night |
| response_count | INT | API가 반환한 미션 수 |

```sql
CREATE TABLE recommendation_requests (
    log_id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    request_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    gender VARCHAR(1) NOT NULL CHECK (gender IN ('M', 'F')),
    age INT NOT NULL CHECK (age BETWEEN 0 AND 100),
    user_lat DECIMAL(10,8) NOT NULL,
    user_lon DECIMAL(11,8) NOT NULL,
    current_weather VARCHAR(20) NOT NULL CHECK (current_weather IN ('Sunny','Cloudy','Rainy','Snowy')),
    current_day_of_week INT NOT NULL CHECK (current_day_of_week BETWEEN 0 AND 6),
    pref_tags JSON NOT NULL,
    acceptance_rate DECIMAL(5,4) NOT NULL CHECK (acceptance_rate BETWEEN 0 AND 1),
    active_time_slot VARCHAR(20) NOT NULL CHECK (active_time_slot IN ('Morning','Day','Evening','Night')),
    response_count INT NOT NULL,
    INDEX idx_user_timestamp (user_id, request_timestamp),
    INDEX idx_timestamp (request_timestamp)
);
```

### Python 저장 예시
```python
def save_recommendation_request(conn, user_context, response):
    query = """
    INSERT INTO recommendation_requests (
        user_id, request_timestamp, gender, age, user_lat, user_lon,
        current_weather, current_day_of_week, pref_tags, acceptance_rate,
        active_time_slot, response_count
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    RETURNING log_id
    """
    values = (
        user_context['user_id'], datetime.now(), user_context['gender'],
        user_context['age'], user_context['user_lat'], user_context['user_lon'],
        user_context['current_weather'], user_context['current_day_of_week'],
        json.dumps(user_context['pref_tags']), user_context['acceptance_rate'],
        user_context['active_time_slot'], response['total_missions']
    )
    cur = conn.cursor()
    cur.execute(query, values)
    log_id = cur.fetchone()[0]
    conn.commit()
    return log_id
```

---

## 미션 피드백 로그 (`mission_feedback`)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| feedback_id | BIGSERIAL PK | 피드백 고유 ID |
| log_id | BIGINT FK | 추천 요청 참조 |
| user_id | VARCHAR(50) | 사용자 ID |
| mission_id | INT | 미션 ID |
| mission_title | VARCHAR(200) | 미션 제목 |
| category | VARCHAR(50) | 카테고리 |
| distance_m | INT | 사용자-미션 거리 |
| priority_weight | INT | 0~3 |
| model_proba | DECIMAL(5,4) | 예측 확률 |
| final_score | DECIMAL(8,4) | Priority 적용 점수 |
| ranking | INT | 추천 순위 |
| is_accepted | BOOLEAN | 수락 여부 |
| feedback_timestamp | TIMESTAMP | 상호작용 시각 |
| interaction_type | VARCHAR(20) | click_accept/click_reject/ignore/complete |

```sql
CREATE TABLE mission_feedback (
    feedback_id BIGSERIAL PRIMARY KEY,
    log_id BIGINT NOT NULL REFERENCES recommendation_requests(log_id),
    user_id VARCHAR(50) NOT NULL,
    mission_id INT NOT NULL,
    mission_title VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,
    distance_m INT NOT NULL,
    priority_weight INT NOT NULL CHECK (priority_weight BETWEEN 0 AND 3),
    model_proba DECIMAL(5,4) NOT NULL CHECK (model_proba BETWEEN 0 AND 1),
    final_score DECIMAL(8,4) NOT NULL,
    ranking INT NOT NULL,
    is_accepted BOOLEAN NOT NULL,
    feedback_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    interaction_type VARCHAR(20) NOT NULL CHECK (interaction_type IN ('click_accept','click_reject','ignore','complete')),
    INDEX idx_user_mission (user_id, mission_id),
    INDEX idx_log (log_id),
    INDEX idx_timestamp (feedback_timestamp),
    INDEX idx_accepted (is_accepted),
    CONSTRAINT unique_log_mission UNIQUE (log_id, mission_id)
);
```

### Python 저장 예시
```python
def save_mission_feedback(conn, log_id, user_id, mission, is_accepted, interaction_type):
    query = """
    INSERT INTO mission_feedback (
        log_id, user_id, mission_id, mission_title, category, distance_m,
        priority_weight, model_proba, final_score, ranking, is_accepted,
        feedback_timestamp, interaction_type
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    values = (
        log_id, user_id, mission['mission_id'], mission['title'], mission['category'],
        mission['distance_m'], mission['priority_weight'], mission['model_proba'],
        mission['final_score'], mission['ranking'], is_accepted, datetime.now(), interaction_type
    )
    cur = conn.cursor()
    cur.execute(query, values)
    conn.commit()
```

---

## 데이터 수집 워크플로
1. 사용자가 앱 "미션" 화면 진입 → Backend가 유저/컨텍스트 수집
2. `/recommend` 호출 → 응답 저장 (`response_count` 포함)
3. Frontend에 Top N 노출, rank 정보 유지
4. 사용자가 수락/거절 → `mission_feedback`에 기록 (log_id + ranking 조합)
5. 추가적으로 `interaction_type='ignore'` 등으로 장기 미노출 로그도 관리 가능

---

## 데이터 추출 & 재학습용 전처리
```python
def extract_training_data(conn, start_date, end_date):
    query = """
    SELECT 
        r.user_id, r.gender, r.age, r.user_lat, r.user_lon,
        r.current_weather, r.current_day_of_week, r.pref_tags,
        r.acceptance_rate, r.active_time_slot,
        f.mission_id, f.category, f.distance_m, f.priority_weight,
        f.is_accepted AS label
    FROM recommendation_requests r
    INNER JOIN mission_feedback f ON r.log_id = f.log_id
    WHERE r.request_timestamp BETWEEN %s AND %s
      AND f.interaction_type IN ('click_accept','click_reject')
    ORDER BY r.request_timestamp
    """
    df = pd.read_sql(query, conn, params=(start_date, end_date))
    df['pref_tags'] = df['pref_tags'].apply(json.loads)
    return df
```

### 재학습 파이프라인
1. `production_data = extract_training_data(...)`
2. `production_data['is_accepted'] = production_data['label']`
3. 합성 데이터와 concat 후 중복 제거 (`user_id`,`mission_id`,`gender`,`age`,`current_weather`,`current_day_of_week`)
4. Step 5 Feature Engineering과 동일한 로직 적용
5. 새 모델 학습 → AUC 비교 → 버전 태깅

---

## 품질 체크리스트
- NULL 값 없음 (필수 컬럼)
- 범위 검증: age 0~100, acceptance_rate 0~1, priority_weight 0~3
- 유효 열거형: gender, weather, active_time_slot, interaction_type
- pref_tags JSON 직렬화/역직렬화 확인
- 외래키 무결성: `mission_feedback.log_id`는 항상 존재해야 함
- `unique_log_mission` 제약으로 중복 피드백 방지

---

## 데이터 보관 정책
- **Hot (3개월)**: 메인 DB에 보관, 대시보드/실시간 분석용
- **Warm (3~12개월)**: 압축 또는 파티션 테이블로 관리, 재학습 시 로드
- **Cold (12개월+)**: S3/Cloud Storage에 아카이빙

---

## 재학습 대비 체크
- 기간별 추출 스크립트 자동화
- 로그 누락/지연 여부 모니터링
- `response_count` vs 실제 피드백 개수 비교해 사용자 반응률 계산
- ETL 완료 후 샘플링하여 Feature 값 검증

이 문서는 운영 데이터 플로우와 재학습 데이터 준비에 필요한 모든 세부 사항을 다룹니다.
