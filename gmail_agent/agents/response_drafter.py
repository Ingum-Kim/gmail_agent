"""
ResponseDrafter Agent
이메일 답변 초안 생성
"""
from typing import Dict, List, Optional
from utils.llm_handler import LLMHandler


class ResponseDrafter:
    """답변 초안 생성 Agent"""
    
    def __init__(self, llm_handler: LLMHandler):
        """
        ResponseDrafter 초기화
        
        Args:
            llm_handler: LLM 핸들러 인스턴스
        """
        self.llm = llm_handler
    
    def draft_response(
        self,
        email: Dict,
        classification: Dict,
        priority_analysis: Dict
    ) -> Dict:
        """
        이메일 답변 초안 생성
        
        Args:
            email: 이메일 정보
            classification: 분류 결과
            priority_analysis: 우선순위 분석 결과
                
        Returns:
            답변 초안 결과
                - draft: 답변 초안 텍스트
                - tone: 사용한 톤 (formal/friendly)
                - suggested_subject: 제안 제목
                - should_respond: 답변 필요 여부
        """
        print(f"  🤖 ResponseDrafter: {email['subject'][:50]}...")
        
        category = classification.get('category', 'work')
        priority = priority_analysis.get('priority', 'medium')
        
        # 스팸/마케팅은 답변 불필요
        if category in ['spam', 'marketing']:
            return {
                'draft': None,
                'tone': None,
                'suggested_subject': None,
                'should_respond': False,
                'reason': '답변이 필요하지 않은 이메일입니다.'
            }
        
        # 적절한 톤 선택
        tone = self._select_tone(category, priority)
        
        # LLM으로 답변 초안 생성 (필수)
        draft = self._generate_draft_with_llm(email, classification, priority_analysis, tone)
        
        # LLM 실패 시 이미 에러가 발생했을 것임
        if not draft:
            raise ValueError(
                "LLM 답변 생성 실패. OpenAI API 키가 올바르게 설정되었는지 확인하세요."
            )
        
        # 제목 생성
        suggested_subject = f"Re: {email['subject']}"
        
        return {
            'draft': draft,
            'tone': tone,
            'suggested_subject': suggested_subject,
            'should_respond': True,
            'reason': '답변 초안이 생성되었습니다.'
        }
    
    def _select_tone(self, category: str, priority: str) -> str:
        """
        적절한 답변 톤 선택
        
        Args:
            category: 이메일 카테고리
            priority: 우선순위
            
        Returns:
            톤 (formal/friendly)
        """
        # 긴급하거나 업무 관련은 공식적으로
        if category == 'urgent' or priority == 'high':
            return 'formal'
        
        # 내부 업무는 친근하게
        if category == 'internal':
            return 'friendly'
        
        # 기본값: 공식적
        return 'formal'
    
    def _generate_draft_with_llm(
        self,
        email: Dict,
        classification: Dict,
        priority_analysis: Dict,
        tone: str
    ) -> str:
        """
        LLM을 사용한 답변 초안 생성
        
        Args:
            email: 이메일 정보
            classification: 분류 결과
            priority_analysis: 우선순위 분석
            tone: 톤
            
        Returns:
            답변 초안 텍스트
        """
        body_preview = email['body'][:600] if len(email['body']) > 600 else email['body']
        category = classification.get('category', 'work')
        priority = priority_analysis.get('priority', 'medium')
        
        # 톤에 따른 스타일 가이드
        tone_guide = {
            'formal': "공식적이고 정중한 톤으로 작성하세요. '안녕하세요', '감사합니다' 등 격식 있는 표현을 사용하세요.",
            'friendly': "친근하고 편안한 톤으로 작성하세요. 하지만 여전히 전문적이어야 합니다."
        }
        
        prompt = f"""다음 이메일에 대한 답변 초안을 작성하세요.

받은 이메일:
발신자: {email['from']}
제목: {email['subject']}
본문:
{body_preview}

이메일 정보:
- 카테고리: {category}
- 우선순위: {priority}
- 톤: {tone_guide.get(tone, tone_guide['formal'])}

답변 작성 가이드:
1. 인사말로 시작
2. 이메일 내용을 이해했음을 표현
3. 핵심 질문이나 요청에 답변
4. 추가 정보가 필요하면 요청
5. 정중한 마무리

한국어로 3-5문단 정도로 작성하세요.
서명은 포함하지 마세요.

답변 초안:"""

        try:
            draft = self.llm.generate(
                prompt,
                max_tokens=500,
                temperature=0.7,
                system_prompt="당신은 전문적인 이메일 작성 도우미입니다. 자연스럽고 적절한 답변을 작성하세요."
            )
            
            return draft.strip()
            
        except Exception as e:
            error_msg = f"LLM 답변 생성 오류: {str(e)}"
            print(f"  ⚠️ {error_msg}")
            raise ValueError(error_msg) from e
    
    def batch_draft(self, analyzed_emails: List[Dict]) -> List[Dict]:
        """
        여러 이메일의 답변 초안을 한 번에 생성
        
        Args:
            analyzed_emails: 우선순위 분석된 이메일 리스트
            
        Returns:
            답변 초안 포함 이메일 리스트
        """
        results = []
        
        for email in analyzed_emails:
            classification = email.get('classification', {})
            priority_analysis = email.get('priority_analysis', {})
            
            response_draft = self.draft_response(email, classification, priority_analysis)
            
            results.append({
                **email,
                'response_draft': response_draft
            })
        
        return results
    
    def get_response_stats(self, drafted_emails: List[Dict]) -> Dict:
        """
        답변 필요 여부 통계
        
        Args:
            drafted_emails: 답변 초안 생성된 이메일 리스트
            
        Returns:
            통계 정보
        """
        total = len(drafted_emails)
        need_response = sum(
            1 for email in drafted_emails
            if email.get('response_draft', {}).get('should_respond', False)
        )
        no_response = total - need_response
        
        return {
            'total': total,
            'need_response': need_response,
            'no_response': no_response,
            'response_rate': round(need_response / total * 100, 1) if total > 0 else 0
        }
    
    def refine_draft(
        self,
        original_draft: str,
        user_feedback: str
    ) -> str:
        """
        사용자 피드백 기반 답변 초안 개선
        
        Args:
            original_draft: 원본 답변 초안
            user_feedback: 사용자 피드백
            
        Returns:
            개선된 답변 초안
        """
        prompt = f"""다음 답변 초안을 사용자 피드백에 따라 개선하세요.

원본 답변:
{original_draft}

사용자 피드백:
{user_feedback}

개선된 답변을 작성하세요:"""

        try:
            refined = self.llm.generate(
                prompt,
                max_tokens=500,
                temperature=0.7
            )
            
            return refined.strip()
            
        except Exception as e:
            print(f"  ⚠️ 답변 개선 오류: {str(e)}")
            return original_draft

