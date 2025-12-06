"""
BNK 로컬 챌린지 추천 API 클라이언트
Backend에서 API를 호출하는 예제 코드
"""

import requests
from typing import Dict, List, Optional
import json

class RecommendationClient:
    """BNK 로컬 챌린지 추천 API 클라이언트"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
    
    def get_recommendations(self, user_data: Dict) -> List[Dict]:
        """
        유저 정보를 기반으로 미션 추천 받기
        
        Parameters:
        - user_data: 유저 정보 및 현재 컨텍스트 (dict)
        
        Returns:
        - recommendations: 추천 미션 리스트 (rank 순 정렬)
        """
        
        endpoint = f"{self.api_url}/recommend"
        
        try:
            response = requests.post(
                endpoint,
                json=user_data,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            response.raise_for_status()  # HTTP 에러 체크
            
            result = response.json()
            return result['recommendations']
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API 호출 실패: {e}")
            return []
    
    def get_top_n_recommendations(self, user_data: Dict, top_n: int = 5) -> List[Dict]:
        """
        상위 N개 추천 미션만 반환
        
        Parameters:
        - user_data: 유저 정보
        - top_n: 반환할 추천 개수 (기본 5개)
        
        Returns:
        - top recommendations: 상위 N개 미션
        """
        
        recommendations = self.get_recommendations(user_data)
        return recommendations[:top_n]
    
    def get_all_missions(self) -> List[Dict]:
        """모든 미션 목록 조회"""
        try:
            response = requests.get(f"{self.api_url}/missions", timeout=3)
            response.raise_for_status()
            return response.json()['missions']
        except:
            return []
    
    def health_check(self) -> bool:
        """API 서버 상태 확인"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=3)
            return response.status_code == 200
        except:
            return False


# ===== 사용 예시 =====

if __name__ == "__main__":
    print("="*80)
    print("🚀 BNK 로컬 챌린지 추천 API 클라이언트 테스트")
    print("="*80)
    
    # 클라이언트 초기화
    client = RecommendationClient(api_url="http://localhost:8000")
    
    # 서버 상태 확인
    print("\n1️⃣ 서버 상태 확인 중...")
    if not client.health_check():
        print("❌ API 서버가 응답하지 않습니다.")
        print("💡 먼저 다음 명령어로 서버를 실행하세요:")
        print("   python api_server.py")
        exit(1)
    
    print("✅ API 서버 연결 성공\n")
    
    # 테스트 시나리오 1: 부산대 근처 유저
    print("="*80)
    print("📍 시나리오 1: 부산대 근처 25세 남성")
    print("="*80)
    
    user_context_1 = {
        "user_id": "U0001",
        "age": 25,
        "gender": "M",
        "last_lat": 35.23,  # 부산대 근처
        "last_lon": 129.08,
        "pref_tags": ["Food", "Cafe", "Self-Dev"],
        "acceptance_rate": 0.15,
        "active_time_slot": "Day",
        "current_hour": 14,  # 오후 2시
        "current_day_of_week": 2,  # 수요일
        "current_weather": "Sunny"
    }
    
    top_5_1 = client.get_top_n_recommendations(user_context_1, top_n=5)
    
    print(f"\n유저: {user_context_1['user_id']} (나이 {user_context_1['age']}, {user_context_1['gender']})")
    print(f"현재 위치: ({user_context_1['last_lat']}, {user_context_1['last_lon']})")
    print(f"선호 카테고리: {', '.join(user_context_1['pref_tags'])}")
    print(f"시간: {user_context_1['current_hour']}시, 날씨: {user_context_1['current_weather']}")
    
    print("\n🏆 Top 5 추천 미션:")
    print("-"*80)
    
    for mission in top_5_1:
        print(f"\n{mission['rank']}위. {mission['title']}")
        print(f"  📍 카테고리: {mission['category']}")
        print(f"  📏 거리: {mission['distance_m']:.0f}m")
        print(f"  ⭐ 추천 점수: {mission['final_score']:.4f}")
        print(f"  🎯 모델 예측: {mission['model_proba']:.2%}")
        print(f"  💎 우선도: {mission['priority_weight']}")
    
    # 테스트 시나리오 2: 해운대 근처 유저
    print("\n" + "="*80)
    print("📍 시나리오 2: 해운대 근처 28세 여성 (저녁 시간)")
    print("="*80)
    
    user_context_2 = {
        "user_id": "U0042",
        "age": 28,
        "gender": "F",
        "last_lat": 35.1588,  # 해운대 동백섬 근처
        "last_lon": 129.1345,
        "pref_tags": ["Tourist", "Cafe", "Walk"],
        "acceptance_rate": 0.22,
        "active_time_slot": "Evening",
        "current_hour": 18,  # 오후 6시
        "current_day_of_week": 5,  # 토요일
        "current_weather": "Sunny"
    }
    
    top_5_2 = client.get_top_n_recommendations(user_context_2, top_n=5)
    
    print(f"\n유저: {user_context_2['user_id']} (나이 {user_context_2['age']}, {user_context_2['gender']})")
    print(f"현재 위치: ({user_context_2['last_lat']}, {user_context_2['last_lon']})")
    print(f"선호 카테고리: {', '.join(user_context_2['pref_tags'])}")
    print(f"시간: {user_context_2['current_hour']}시, 날씨: {user_context_2['current_weather']}")
    
    print("\n🏆 Top 5 추천 미션:")
    print("-"*80)
    
    for mission in top_5_2:
        print(f"\n{mission['rank']}위. {mission['title']}")
        print(f"  📍 카테고리: {mission['category']}")
        print(f"  📏 거리: {mission['distance_m']:.0f}m")
        print(f"  ⭐ 추천 점수: {mission['final_score']:.4f}")
        print(f"  🎯 모델 예측: {mission['model_proba']:.2%}")
        print(f"  💎 우선도: {mission['priority_weight']}")
    
    print("\n" + "="*80)
    print("✅ 테스트 완료!")
    print("="*80)
    
    print("\n💡 Backend 통합 방법:")
    print("""
    # Django/Flask에서 사용
    client = RecommendationClient(api_url="http://localhost:8000")
    recommendations = client.get_top_n_recommendations(user_data, top_n=10)
    
    # 또는 직접 requests 사용
    response = requests.post(
        "http://localhost:8000/recommend",
        json=user_data
    )
    recommendations = response.json()['recommendations']
    """)
