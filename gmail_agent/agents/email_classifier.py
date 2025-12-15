"""
EmailClassifier Agent
이메일을 카테고리별로 분류
"""
import json
import re
from typing import Dict, List
from utils.llm_handler import LLMHandler
from config.gmail_config import EMAIL_CATEGORIES


class EmailClassifier:
    """이메일 분류 Agent"""
    
    def __init__(self, llm_handler: LLMHandler):
        """
        EmailClassifier 초기화
        
        Args:
            llm_handler: LLM 핸들러 인스턴스
        """
        self.llm = llm_handler
    
    def classify(self, email: Dict) -> Dict:
        """
        이메일 분류
        
        Args:
            email: 이메일 정보
                - subject: 제목
                - from: 발신자
                - body: 본문
                - snippet: 요약
                
        Returns:
            분류 결과
                - category: 카테고리 (urgent/work/marketing/internal/spam)
                - confidence: 확신도 (0-1)
                - reason: 분류 근거
        """
        print(f"  🤖 EmailClassifier: {email['subject'][:50]}...")
        
        # LLM으로 분류 (필수)
        category, reason = self._classify_with_llm(email)
        
        # LLM 실패 시 에러 발생
        if not category or category not in EMAIL_CATEGORIES:
            raise ValueError(
                f"LLM 분류 실패: 유효하지 않은 카테고리 '{category}'. "
                f"OpenAI API 키가 올바르게 설정되었는지 확인하세요."
            )
        
        return {
            'category': category,
            'confidence': 0.85,  # 임의 값 (실제로는 LLM 응답에서 추출 가능)
            'reason': reason
        }
    
    def _classify_with_llm(self, email: Dict) -> tuple:
        """
        LLM을 사용한 이메일 분류
        
        Args:
            email: 이메일 정보
            
        Returns:
            (category, reason)
        """
        # 본문이 너무 길면 잘라내기
        body_preview = email['body'][:500] if len(email['body']) > 500 else email['body']
        
        prompt = f"""다음 이메일을 분류하세요.

이메일 정보:
발신자: {email['from']}
제목: {email['subject']}
본문 미리보기:
{body_preview}

카테고리 (하나만 선택):
1. urgent: 긴급하게 답변이 필요한 이메일 (고객 불만, 중요한 요청 등)
2. work: 일반 업무 문의 (기술 지원, 질문, 협업 요청 등)
3. marketing: 마케팅/홍보 이메일 (광고, 뉴스레터, 프로모션 등)
4. internal: 내부 업무 이메일 (팀 공지, 회의 안내 등)
5. spam: 스팸/불필요한 이메일

다음 형식으로 답변하세요:
카테고리: [urgent/work/marketing/internal/spam]
이유: [분류 근거를 한 문장으로]"""

        try:
            response = self.llm.generate(
                prompt,
                max_tokens=150,
                temperature=0.3,
                system_prompt="당신은 이메일 분류 전문가입니다. 정확하고 간결하게 답변하세요."
            )
            
            # 응답에서 카테고리와 이유 추출
            category_match = re.search(r'카테고리\s*[:：]\s*(\w+)', response)
            reason_match = re.search(r'이유\s*[:：]\s*(.+)', response)
            
            category = category_match.group(1) if category_match else None
            reason = reason_match.group(1).strip() if reason_match else "LLM 분류 결과"
            
            # 카테고리 정규화
            category = category.lower() if category else None
            
            return category, reason
            
        except Exception as e:
            error_msg = f"LLM 분류 오류: {str(e)}"
            print(f"  ⚠️ {error_msg}")
            raise ValueError(error_msg) from e
    
    def batch_classify(self, emails: List[Dict]) -> List[Dict]:
        """
        여러 이메일을 한 번에 분류
        
        Args:
            emails: 이메일 리스트
            
        Returns:
            분류 결과 리스트
        """
        results = []
        
        for email in emails:
            classification = self.classify(email)
            results.append({
                **email,
                'classification': classification
            })
        
        return results
    
    def get_category_stats(self, classified_emails: List[Dict]) -> Dict:
        """
        카테고리별 통계
        
        Args:
            classified_emails: 분류된 이메일 리스트
            
        Returns:
            카테고리별 개수
        """
        stats = {category: 0 for category in EMAIL_CATEGORIES}
        
        for email in classified_emails:
            category = email.get('classification', {}).get('category', 'work')
            if category in stats:
                stats[category] += 1
        
        return stats

