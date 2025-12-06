# BNK 로컬 챌린지 추천 시스템 - Overview

## 프로젝트 개요
- **목적:** 부산 지역 기반 O2O 플랫폼을 위한 LightGBM 추천 시스템 구축
- **핵심 기술:** LightGBM 모델 추론 + FastAPI REST API + Hybrid Filtering
- **데이터 자산:** 23개 지역 미션, 1,000명 사용자, 10,000+ 행동 로그(합성 + 운영 수집)
- **운영 포인트:** Cold Start 완화, Priority Weight로 비즈니스 전략 반영, MLOps 루프 시뮬레이션

## 문서 구성
이전의 단일 대형 문서를 주제별로 아래와 같이 분리했습니다.
1. `docs/PROJECT_OVERVIEW.md` (현재 문서) – 전체 개요 및 파일/워크플로 요약
2. `docs/MODEL_PIPELINE.md` – 데이터 생성, Feature Engineering, 모델 학습/버전 관리
3. `docs/API_AND_CLIENT.md` – FastAPI 서버, 엔드포인트, 테스트 클라이언트, Backend 연동 예시
4. `docs/DATA_PIPELINE.md` – 로그 스키마, 데이터 수집·추출·품질 관리, 재학습 전처리
5. `docs/OPERATIONS_AND_ROADMAP.md` – 운영 워크플로, 배포 전략, 기술/비즈니스 인사이트, 로드맵

각 문서는 `PROJECT_DOCUMENTATION.md`에서 링크로 접근할 수 있으며, 필요한 주제만 빠르게 살펴볼 수 있습니다.

## 핵심 파일 및 아티팩트
- `BNK.ipynb`: 전체 MLOps 파이프라인을 담은 모델 학습 노트북 (Step 0~9)
- `model_v2.pkl`: LightGBM binary classifier (17개 Feature, AUC ~0.85-0.90)
- `missions.csv`: 23개 부산 미션 마스터 데이터 (추가 미션 확장 가능)
- `api_server.py`: FastAPI 추천 서버 (POST /recommend, GET /missions 등)
- `test_client.py`: 시나리오 기반 API 검증/데모 클라이언트
- `requirements.txt`: FastAPI + 데이터/ML 라이브러리 의존성 목록
- `README.md`: 설치/실행 가이드, 빠른 시작 안내

## 전체 워크플로 개요
1. **데이터 & 모델 준비** – `BNK.ipynb`에서 합성 데이터 생성 → LightGBM 학습 → `model_v2.pkl`, `missions.csv` 산출
2. **서버 실행** – 가상환경 준비 → `uvicorn api_server:app --reload` → `/docs`에서 Swagger로 검증
3. **클라이언트 테스트** – `test_client.py` 시나리오 실행으로 추천 결과 확인
4. **Backend 연동** – `Request.py` 예시 코드로 추천 API 호출, Top-N/필터링 로직 구현
5. **데이터 수집 & 재학습** – 추천 요청/피드백 로그 저장 → DB에서 추출 → 노트북에서 재학습 → 모델 버전 관리

### Backend 연동 흐름 요약
1. Backend가 유저 프로필 + 현재 컨텍스트(위치/시간/날씨) 수집
2. FastAPI `/recommend` 호출 → 모든 미션에 대해 Feature 생성 & 모델 추론
3. Priority Weight를 적용한 final_score로 정렬 후 응답 반환
4. Backend는 Top5/카테고리/거리 등 비즈니스 로직으로 후처리해 UI 노출
5. 사용자 피드백(수락/거절)을 저장해 추후 재학습에 활용

이 Overview 문서는 나머지 세부 문서를 찾기 위한 관문 역할을 하며, 프로젝트 전반의 스냅샷을 제공합니다.
