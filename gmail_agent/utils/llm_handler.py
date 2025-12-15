"""
LLM Handler for OpenAI API
"""
import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class LLMHandler:
    """OpenAI API를 사용한 LLM 핸들러"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """
        LLMHandler 초기화
        
        Args:
            model_name: 사용할 OpenAI 모델 이름
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY가 설정되지 않았습니다. "
                ".env 파일을 확인하세요."
            )
        
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        LLM으로 텍스트 생성
        
        Args:
            prompt: 사용자 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 생성 온도 (0-1)
            system_prompt: 시스템 프롬프트 (선택사항)
            
        Returns:
            생성된 텍스트
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"LLM 생성 오류: {str(e)}")
            raise e
    
    def generate_with_examples(
        self,
        prompt: str,
        examples: list,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        """
        예시를 포함한 Few-shot 프롬프팅
        
        Args:
            prompt: 사용자 프롬프트
            examples: [(사용자 입력, 어시스턴트 출력), ...] 형식의 예시 리스트
            max_tokens: 최대 토큰 수
            temperature: 생성 온도
            
        Returns:
            생성된 텍스트
        """
        messages = []
        
        # 예시 추가
        for user_example, assistant_example in examples:
            messages.append({"role": "user", "content": user_example})
            messages.append({"role": "assistant", "content": assistant_example})
        
        # 실제 쿼리 추가
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"LLM 생성 오류: {str(e)}")
            raise e

