# 운영 & 로드맵

## 개발 단계 워크플로
```
1. BNK.ipynb 실행
   - 커널 선택 후 Step 9까지 Run All
2. 산출물 확인
   - model_v2.pkl, missions.csv 생성
3. 가상환경 세팅
   - python -m venv venv && source venv/bin/activate
   - pip install -r requirements.txt
4. FastAPI 서버 실행
   - uvicorn api_server:app --reload
   - http://localhost:8000/docs에서 확인
5. test_client.py 실행
   - python test_client.py → 시나리오 검증
6. Backend 연동
   - Request.py 작성, 추천 결과 활용
```

## Backend 연동 흐름
1. Backend 서버가 DB/앱에서 사용자 정보와 실시간 컨텍스트 수집
2. `/recommend` 호출 → 모든 미션 Feature 생성 + LightGBM 예측
3. Priority Weight를 곱한 `final_score`로 정렬, rank 부여
4. Backend는 Top N/필터링/추가 비즈니스 로직 적용 후 UI 전달
5. 사용자의 수락/거절 이벤트를 로깅하여 재학습 데이터로 활용

## Production 배포 가이드
1. **컨테이너화** – 모델/미션 CSV 포함 Docker 이미지 생성
2. **환경변수** – `DATABASE_URL`, `WEATHER_API_KEY`, `MODEL_PATH` 등 주입
3. **로드 밸런싱** – Nginx 또는 AWS ALB로 서비스 다중화
4. **모니터링** – Prometheus + Grafana, 로그는 ELK Stack으로 수집
5. **CI/CD** – GitHub Actions 등으로 테스트 → 빌드 → 배포 자동화

## 기술 요약
- **추천 알고리즘:** Content-Based + Location-Based + Hybrid(Priority) + Contextual Bandits 개념 적용
- **머신러닝:** LightGBM Binary Classifier, AUC 지표, 모델 버전 관리(v1/v2)
- **백엔드:** FastAPI + Uvicorn, Pydantic 검증, REST JSON 응답
- **데이터:** 합성 Ground Truth + 실제 좌표/인구 분포, 운영 로그로 점진적 개선

## 비즈니스 인사이트
- Feature Importance Top5: 거리, 분당보상, 우선도, 취향 일치, 악천후 여부
- Priority Weight 전략:
  - 3(1.3x): BNK 핵심 제휴
  - 2(1.2x): 주요 관광/제휴 자산
  - 1(1.1x): 지역 상권/문화
  - 0(1.0x): 일반 미션
- Hybrid 접근으로 ML 확률 + 운영 전략을 동시에 반영해 해석 가능성을 확보

## 로드맵
- **단기 (1~2개월)**: 실제 유저 데이터 수집, Priority Weight A/B 테스트, 운영자 대시보드, 푸시 알림 연동
- **중기 (3~6개월)**: Collaborative Filtering 추가, 유저 클러스터링, 시계열 분석, 강화학습 탐색
- **장기 (6~12개월)**: Wide & Deep/NCF 등 DL, Kafka 기반 실시간 스트리밍, GNN, Multi-Armed Bandit 최적화

## 학습 포인트 & 참고 자료
- Cold Start는 합성 데이터와 Ground Truth 규칙으로 완화 → 운영 로그와 결합해 점진적 개선
- Priority Weight로 비즈니스 전략을 ML 스코어에 주입해 운영/데이터 팀 협업 용이
- Notebook(학습)과 API(서빙)를 분리하여 Production-ready 구조 달성

**참고:**
- 부산 GPS: Google Maps
- 인구 분포: 2024 부산광역시 통계청
- 미션 아이디어: 부산 관광 공식 사이트 등
- FastAPI / LightGBM / Pydantic 공식 문서 링크는 README 및 각 세부 문서에서 재참조 가능합니다.
