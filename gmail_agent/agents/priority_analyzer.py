"""
PriorityAnalyzer Agent
이메일의 우선순위 및 긴급도 판단
"""
import re
from typing import Dict, List
from utils.llm_handler import LLMHandler
from config.gmail_config import PRIORITY_LEVELS


class PriorityAnalyzer:
    """우선순위 분석 Agent"""
    
    def __init__(self, llm_handler: LLMHandler):
        """
        PriorityAnalyzer 초기화
        
        Args:
            llm_handler: LLM 핸들러 인스턴스
        """
        self.llm = llm_handler
    
    def analyze(self, email: Dict, classification: Dict) -> Dict:
        """
        이메일 우선순위 분석
        
        Args:
            email: 이메일 정보
            classification: EmailClassifier의 분류 결과
                
        Returns:
            우선순위 분석 결과
                - priority: 우선순위 (high/medium/low)
                - urgency_score: 긴급도 점수 (0-10)
                - factors: 판단 요인 리스트
        """
        print(f"  🤖 PriorityAnalyzer: {email['subject'][:50]}...")
        
        # LLM으로 상세 분석 (필수)
        priority, factors = self._analyze_with_llm(email, classification)
        
        # LLM 실패 시 에러 발생
        if not priority or priority not in PRIORITY_LEVELS:
            raise ValueError(
                f"LLM 우선순위 분석 실패: 유효하지 않은 우선순위 '{priority}'. "
                f"OpenAI API 키가 올바르게 설정되었는지 확인하세요."
            )
        
        # 긴급도 점수 계산
        urgency_score = self._calculate_urgency_score(email, priority)
        
        return {
            'priority': priority,
            'urgency_score': urgency_score,
            'factors': factors
        }
    
    def _analyze_with_llm(self, email: Dict, classification: Dict) -> tuple:
        """
        LLM을 사용한 우선순위 분석
        
        Args:
            email: 이메일 정보
            classification: 분류 결과
            
        Returns:
            (priority, factors)
        """
        body_preview = email['body'][:400] if len(email['body']) > 400 else email['body']
        category = classification.get('category', 'work')
        
        prompt = f"""다음 이메일의 우선순위를 분석하세요.

이메일 정보:
발신자: {email['from']}
제목: {email['subject']}
카테고리: {category}
본문 미리보기:
{body_preview}

우선순위 레벨 (하나만 선택):
- high: 24시간 내 답변 필요 (중요한 고객, 긴급 요청, 문제 발생 등)
- medium: 3일 내 답변 (일반 문의, 협업 요청 등)
- low: 여유 있게 처리 (마케팅, 정보 제공 등)

판단 기준:
1. 발신자의 중요도
2. 내용의 긴급성 (마감일, 문제 발생 등)
3. 감정 (불만, 불편 등)
4. 요청의 성격

다음 형식으로 답변하세요:
우선순위: [high/medium/low]
주요 요인: [판단 근거 1-2개, 쉼표로 구분]"""

        try:
            response = self.llm.generate(
                prompt,
                max_tokens=150,
                temperature=0.3,
                system_prompt="당신은 이메일 우선순위 분석 전문가입니다."
            )
            
            # 응답에서 우선순위와 요인 추출
            priority_match = re.search(r'우선순위\s*[:：]\s*(\w+)', response)
            factors_match = re.search(r'주요\s*요인\s*[:：]\s*(.+)', response)
            
            priority = priority_match.group(1).lower() if priority_match else None
            factors_text = factors_match.group(1).strip() if factors_match else ""
            
            # 요인을 리스트로 변환
            factors = [f.strip() for f in factors_text.split(',') if f.strip()]
            
            return priority, factors
            
        except Exception as e:
            error_msg = f"LLM 우선순위 분석 오류: {str(e)}"
            print(f"  ⚠️ {error_msg}")
            raise ValueError(error_msg) from e
    
    def _calculate_urgency_score(self, email: Dict, priority: str) -> int:
        """
        긴급도 점수 계산
        
        Args:
            email: 이메일 정보
            priority: 우선순위
            
        Returns:
            긴급도 점수 (0-10)
        """
        # 기본 점수
        base_scores = {
            'high': 8,
            'medium': 5,
            'low': 2
        }
        
        score = base_scores.get(priority, 5)
        
        # 키워드 기반 추가 점수
        subject_lower = email['subject'].lower()
        body_lower = email['body'].lower()
        
        urgent_keywords = {
            '긴급': 2,
            '즉시': 2,
            'urgent': 2,
            'asap': 2,
            '불만': 1,
            '환불': 1,
            '오류': 1,
            'error': 1,
            'bug': 1
        }
        
        for keyword, points in urgent_keywords.items():
            if keyword in subject_lower or keyword in body_lower:
                score += points
        
        # 최대 10점
        return min(score, 10)
    
    def batch_analyze(self, classified_emails: List[Dict]) -> List[Dict]:
        """
        여러 이메일의 우선순위를 한 번에 분석
        
        Args:
            classified_emails: 분류된 이메일 리스트
            
        Returns:
            우선순위 분석 결과 리스트
        """
        results = []
        
        for email in classified_emails:
            classification = email.get('classification', {})
            priority_analysis = self.analyze(email, classification)
            
            results.append({
                **email,
                'priority_analysis': priority_analysis
            })
        
        return results
    
    def get_priority_stats(self, analyzed_emails: List[Dict]) -> Dict:
        """
        우선순위별 통계
        
        Args:
            analyzed_emails: 우선순위 분석된 이메일 리스트
            
        Returns:
            우선순위별 개수
        """
        stats = {priority: 0 for priority in PRIORITY_LEVELS}
        
        for email in analyzed_emails:
            priority = email.get('priority_analysis', {}).get('priority', 'medium')
            if priority in stats:
                stats[priority] += 1
        
        return stats
    
    def sort_by_priority(self, analyzed_emails: List[Dict]) -> List[Dict]:
        """
        우선순위에 따라 이메일 정렬
        
        Args:
            analyzed_emails: 우선순위 분석된 이메일 리스트
            
        Returns:
            정렬된 이메일 리스트 (high → medium → low)
        """
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        
        return sorted(
            analyzed_emails,
            key=lambda x: (
                priority_order.get(
                    x.get('priority_analysis', {}).get('priority', 'medium'),
                    2
                ),
                x.get('priority_analysis', {}).get('urgency_score', 5)
            ),
            reverse=True
        )

