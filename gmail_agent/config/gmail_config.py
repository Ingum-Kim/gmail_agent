"""
Gmail API Configuration
"""

# Gmail API 설정
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# OAuth 자격증명 파일 경로
CREDENTIALS_FILE = 'credentials.json'

# OAuth 토큰 저장 경로
TOKEN_FILE = 'token.json'

# 한 번에 가져올 최대 이메일 수
MAX_EMAILS = 50

# 이메일 카테고리 정의
EMAIL_CATEGORIES = {
    'urgent': {'label': '긴급', 'icon': '🔴', 'color': 'red'},
    'work': {'label': '업무문의', 'icon': '💼', 'color': 'blue'},
    'marketing': {'label': '마케팅', 'icon': '📢', 'color': 'orange'},
    'internal': {'label': '내부업무', 'icon': '🏢', 'color': 'green'},
    'spam': {'label': '스팸', 'icon': '🗑️', 'color': 'gray'}
}

# 우선순위 레벨
PRIORITY_LEVELS = {
    'high': {'label': '높음 (24시간 내)', 'icon': '🔴', 'value': 3},
    'medium': {'label': '중간 (3일 내)', 'icon': '🟡', 'value': 2},
    'low': {'label': '낮음 (여유)', 'icon': '🟢', 'value': 1}
}

