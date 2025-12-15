"""
Gmail API Client
OAuth 인증 및 이메일 가져오기
"""
import os
import pickle
import base64
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup
import re

from config.gmail_config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE, MAX_EMAILS


class GmailClient:
    """Gmail API 클라이언트"""
    
    def __init__(self):
        """GmailClient 초기화"""
        self.service = None
        self.creds = None
    
    def authenticate(self) -> bool:
        """
        Gmail API 인증
        
        Returns:
            인증 성공 여부
        """
        try:
            # 토큰 파일이 있으면 로드
            if os.path.exists(TOKEN_FILE):
                self.creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            
            # 유효한 자격증명이 없으면
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    # 토큰 갱신
                    self.creds.refresh(Request())
                else:
                    # 새로운 OAuth 플로우 시작
                    if not os.path.exists(CREDENTIALS_FILE):
                        raise FileNotFoundError(
                            f"{CREDENTIALS_FILE} 파일이 없습니다. "
                            "Gmail API 설정 가이드를 참고하세요."
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_FILE, SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                
                # 토큰 저장
                with open(TOKEN_FILE, 'w') as token:
                    token.write(self.creds.to_json())
            
            # Gmail 서비스 생성
            self.service = build('gmail', 'v1', credentials=self.creds)
            return True
            
        except FileNotFoundError as e:
            print(f"파일 오류: {str(e)}")
            raise e
        except Exception as e:
            print(f"인증 오류: {str(e)}")
            raise e
    
    def get_emails(self, max_results: int = 20) -> List[Dict]:
        """
        받은메일함에서 이메일 가져오기
        
        Args:
            max_results: 가져올 이메일 개수 (최대 MAX_EMAILS)
            
        Returns:
            이메일 리스트
        """
        if not self.service:
            raise ValueError("먼저 authenticate()를 호출하세요.")
        
        max_results = min(max_results, MAX_EMAILS)
        
        try:
            # 받은메일함 메시지 ID 목록 가져오기
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                labelIds=['INBOX']
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return []
            
            # 각 메시지 상세 정보 가져오기
            emails = []
            for msg in messages:
                email_data = self._get_email_detail(msg['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except HttpError as error:
            print(f'Gmail API 오류: {error}')
            raise error
    
    def _get_email_detail(self, msg_id: str) -> Optional[Dict]:
        """
        이메일 상세 정보 가져오기
        
        Args:
            msg_id: 메시지 ID
            
        Returns:
            이메일 정보 딕셔너리
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            
            # 헤더에서 필요한 정보 추출
            subject = self._get_header(headers, 'Subject')
            sender = self._get_header(headers, 'From')
            date = self._get_header(headers, 'Date')
            
            # 본문 추출
            body = self._get_email_body(message['payload'])
            
            return {
                'id': msg_id,
                'subject': subject,
                'from': sender,
                'date': date,
                'body': body,
                'snippet': message.get('snippet', '')
            }
            
        except Exception as e:
            print(f'이메일 상세 정보 가져오기 오류 ({msg_id}): {str(e)}')
            return None
    
    def _get_header(self, headers: List[Dict], name: str) -> str:
        """
        헤더에서 특정 필드 값 추출
        
        Args:
            headers: 헤더 리스트
            name: 필드 이름
            
        Returns:
            필드 값
        """
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return ''
    
    def _get_email_body(self, payload: Dict) -> str:
        """
        이메일 본문 추출
        
        Args:
            payload: 메시지 페이로드
            
        Returns:
            본문 텍스트
        """
        body = ''
        
        # multipart 메시지 처리
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        html = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                        body = self._html_to_text(html)
                        break
        else:
            # 단일 파트 메시지
            if 'data' in payload['body']:
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                
                if payload['mimeType'] == 'text/html':
                    body = self._html_to_text(body)
        
        return body.strip()
    
    def _html_to_text(self, html: str) -> str:
        """
        HTML을 텍스트로 변환
        
        Args:
            html: HTML 문자열
            
        Returns:
            텍스트
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            # 스크립트와 스타일 태그 제거
            for script in soup(["script", "style"]):
                script.decompose()
            # 텍스트 추출
            text = soup.get_text()
            # 여러 공백을 하나로
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            return text
        except Exception as e:
            print(f"HTML 파싱 오류: {str(e)}")
            return html
    
    def get_sender_email(self, from_field: str) -> str:
        """
        From 필드에서 이메일 주소만 추출
        
        Args:
            from_field: From 헤더 값 (예: "John Doe <john@example.com>")
            
        Returns:
            이메일 주소
        """
        match = re.search(r'<(.+?)>', from_field)
        if match:
            return match.group(1)
        return from_field
    
    def get_sender_name(self, from_field: str) -> str:
        """
        From 필드에서 이름만 추출
        
        Args:
            from_field: From 헤더 값
            
        Returns:
            발신자 이름
        """
        match = re.search(r'^([^<]+)', from_field)
        if match:
            return match.group(1).strip().strip('"')
        return self.get_sender_email(from_field)

