# 🚂 Railway 배포 가이드

## 📋 Railway 배포 완료 체크리스트

Railway 배포를 위한 필수 파일들이 추가되었습니다:

- ✅ `Procfile` - Railway 실행 명령어
- ✅ `runtime.txt` - Python 버전 명시
- ✅ `railway.json` - Railway 설정
- ✅ `requirements.txt` - Python 패키지 목록
- ✅ `api_server.py` - PORT 환경변수 지원 추가

---

## 🚀 Railway 배포 단계

### 1️⃣ GitHub에 변경사항 푸시

```bash
git add .
git commit -m "feat: Add Railway deployment configuration"
git push origin main
```

### 2️⃣ Railway 계정 생성 및 프로젝트 연결

1. **Railway 회원가입**
   - https://railway.app/ 접속
   - "Start a New Project" 클릭
   - GitHub 계정으로 로그인

2. **GitHub 저장소 연결**
   - "Deploy from GitHub repo" 선택
   - 본인의 BNK 저장소 선택
   - "Deploy Now" 클릭

### 3️⃣ 환경변수 설정 (없음)

이 프로젝트는 환경변수가 필요 없습니다. 모델과 미션 데이터가 저장소에 포함되어 있습니다.

### 4️⃣ 배포 확인

Railway가 자동으로:
1. Python 3.9 설치
2. `requirements.txt`에서 패키지 설치
3. `Procfile`의 명령어로 서버 실행
4. 공개 URL 자동 생성 (예: `https://your-app.up.railway.app`)

배포가 완료되면:
- ✅ Deployments 탭에서 "Success" 확인
- ✅ Settings → Generate Domain으로 공개 URL 생성
- ✅ `https://your-app.up.railway.app/docs` 접속하여 Swagger UI 확인

---

## 🌐 배포 후 테스트

### API 엔드포인트 확인

```bash
# Health Check
curl https://your-app.up.railway.app/health

# 미션 목록 조회
curl https://your-app.up.railway.app/missions

# 추천 요청 (POST)
curl -X POST https://your-app.up.railway.app/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "U0001",
    "age": 25,
    "gender": "M",
    "user_lat": 35.2318,
    "user_lon": 129.0824,
    "pref_tags": ["Food", "Cafe"],
    "acceptance_rate": 0.15,
    "active_time_slot": "Day",
    "current_day_of_week": 3,
    "current_weather": "Sunny"
  }'
```

### Python 클라이언트 테스트

```python
import requests

# Railway 배포 URL로 변경
API_URL = "https://your-app.up.railway.app"

response = requests.post(
    f"{API_URL}/recommend",
    json={
        "user_id": "U0001",
        "age": 25,
        "gender": "M",
        "user_lat": 35.2318,
        "user_lon": 129.0824,
        "pref_tags": ["Food", "Cafe"],
        "acceptance_rate": 0.15,
        "active_time_slot": "Day",
        "current_day_of_week": 3,
        "current_weather": "Sunny"
    }
)

print(response.json())
```

---

## 🔧 트러블슈팅

### ❌ Build Failed

**문제:** Python 버전 또는 패키지 설치 실패

**해결:**
1. `runtime.txt` 파일이 있는지 확인
2. `requirements.txt`에 모든 패키지가 명시되어 있는지 확인
3. Railway 로그에서 오류 메시지 확인

### ❌ Application Failed to Start

**문제:** 서버가 시작되지 않음

**해결:**
1. `Procfile`의 명령어가 올바른지 확인
2. `model_v2.pkl`, `missions.csv` 파일이 저장소에 포함되어 있는지 확인
3. Railway 로그에서 Python 오류 확인

### ❌ 404 Not Found

**문제:** API 엔드포인트를 찾을 수 없음

**해결:**
1. Railway에서 생성된 도메인 주소가 맞는지 확인
2. `/docs` 경로로 Swagger UI 접속 확인
3. CORS 설정이 올바른지 확인 (`api_server.py`의 `allow_origins`)

### ❌ 503 Service Unavailable

**문제:** 서버가 응답하지 않음

**해결:**
1. Railway 대시보드에서 Deployments 상태 확인
2. 로그에서 메모리/CPU 과부하 확인
3. 필요 시 플랜 업그레이드 (무료 플랜: 512MB RAM, 제한적)

---

## 💰 Railway 요금

- **Starter Plan (무료)**: 
  - $5 무료 크레딧/월
  - 512MB RAM
  - 1GB Disk
  - 이 프로젝트에 충분함

- **Developer Plan ($20/월)**:
  - $20 크레딧/월
  - 8GB RAM
  - 100GB Disk
  - Production용

---

## 📊 모니터링

Railway 대시보드에서 확인 가능:
- **Metrics**: CPU, RAM, Network 사용량
- **Logs**: 실시간 애플리케이션 로그
- **Deployments**: 배포 히스토리

---

## 🔄 재배포 (코드 변경 시)

코드를 수정하고 GitHub에 푸시하면 Railway가 **자동으로 재배포**합니다:

```bash
# 코드 수정 후
git add .
git commit -m "fix: Update recommendation algorithm"
git push origin main

# Railway가 자동으로 감지하여 재배포 시작
```

---

## 🌟 배포 완료 후 해야 할 일

1. ✅ Swagger UI 접속: `https://your-app.up.railway.app/docs`
2. ✅ Backend 팀에게 배포 URL 공유
3. ✅ `test_client.py`의 API_URL을 Railway URL로 변경
4. ✅ Frontend의 API 엔드포인트를 Railway URL로 업데이트
5. ✅ README.md에 배포 URL 추가

---

## 📝 주의사항

- **모델 파일 크기**: `model_v2.pkl`은 0.64MB로 문제없음
- **무료 플랜 제한**: 월 500시간 실행 시간 (충분함)
- **Cold Start**: 일정 시간 요청이 없으면 자동 슬립 → 다음 요청 시 5-10초 지연
- **HTTPS 자동**: Railway는 자동으로 HTTPS 제공

---

## 🎉 완료!

이제 전 세계 어디서든 `https://your-app.up.railway.app/recommend`로 API를 호출할 수 있습니다!

**다음 단계:**
- Backend 팀과 API 통합 테스트
- Production 데이터 수집 시작
- 모델 재학습 및 버전 업그레이드
