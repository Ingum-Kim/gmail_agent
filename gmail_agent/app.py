"""
Gmail 이메일 자동 분류 및 답변 에이전트
Streamlit UI
"""
import streamlit as st
import os
from typing import Dict
from datetime import datetime

from utils.gmail_client import GmailClient
from utils.llm_handler import LLMHandler
from agents.email_classifier import EmailClassifier
from agents.priority_analyzer import PriorityAnalyzer
from agents.response_drafter import ResponseDrafter
from config.gmail_config import EMAIL_CATEGORIES, PRIORITY_LEVELS


# 페이지 설정
st.set_page_config(
    page_title="Gmail Agent",
    page_icon="📧",
    layout="wide"
)

# 제목
st.title("📧 Gmail 이메일 자동 분류 및 답변 에이전트")
st.markdown("---")

# 사이드바 - 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    # OpenAI 모델 선택
    model_name = st.selectbox(
        "OpenAI 모델",
        [
            "gpt-3.5-turbo",  # 빠르고 저렴 (권장)
            "gpt-4o-mini",  # 더 저렴한 GPT-4
            "gpt-4-turbo",  # 최고 품질
        ],
        help="💰 gpt-3.5-turbo 권장 (빠르고 저렴)"
    )
    
    # 이메일 개수 선택
    num_emails = st.slider(
        "가져올 이메일 개수",
        min_value=5,
        max_value=50,
        value=20,
        step=5,
        help="받은메일함에서 가져올 최신 이메일 개수"
    )


# 메인 컨텐츠
def main():
    """메인 앱 로직"""
    
    # 세션 상태 초기화
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'emails' not in st.session_state:
        st.session_state.emails = []
    if 'analyzed_emails' not in st.session_state:
        st.session_state.analyzed_emails = []
    
    # Gmail 연결 섹션
    st.header("1️⃣ Gmail 연결")
    
    if not st.session_state.authenticated:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info(
                "🔐 **첫 실행 시**: Google 계정 로그인 창이 열립니다.\n\n"
                "⚠️ '이 앱은 확인되지 않았습니다' 경고가 나오면:\n"
                "**고급 → Gmail Agent(안전하지 않음)로 이동**을 클릭하세요."
            )
        
        with col2:
            if st.button("🔗 Gmail 연결", type="primary", use_container_width=True):
                with st.spinner("Gmail API 인증 중..."):
                    try:
                        gmail_client = GmailClient()
                        gmail_client.authenticate()
                        st.session_state.gmail_client = gmail_client
                        st.session_state.authenticated = True
                        st.success("✅ Gmail 연결 성공!")
                        st.rerun()
                    except FileNotFoundError as e:
                        st.error(
                            f"❌ {str(e)}\n\n"
                            "📖 [Gmail API 설정 가이드](GMAIL_API_SETUP_GUIDE.md)를 참고하세요."
                        )
                    except Exception as e:
                        st.error(f"❌ 인증 오류: {str(e)}")
    
    else:
        st.success("✅ Gmail 계정 연결됨")
        
        if st.button("🔄 다시 연결"):
            st.session_state.authenticated = False
            st.session_state.emails = []
            st.session_state.analyzed_emails = []
            st.rerun()
    
    st.markdown("---")
    
    # 이메일 가져오기 섹션
    if st.session_state.authenticated:
        st.header("2️⃣ 이메일 가져오기 및 분석")
        
        if not st.session_state.emails:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.info(f"📬 받은메일함에서 최신 **{num_emails}개** 이메일을 가져와 분석합니다.")
            
            with col2:
                if st.button("📥 이메일 분석 시작", type="primary", use_container_width=True):
                    analyze_emails(num_emails, model_name)
        
        else:
            st.success(f"✅ {len(st.session_state.emails)}개 이메일 분석 완료!")
            
            if st.button("🔄 새로고침"):
                st.session_state.emails = []
                st.session_state.analyzed_emails = []
                st.rerun()
        
        st.markdown("---")
        
        # 분석 결과 표시
        if st.session_state.analyzed_emails:
            display_results()


def analyze_emails(num_emails: int, model_name: str):
    """이메일 가져오기 및 분석"""
    
    try:
        # LLM 핸들러 초기화
        with st.spinner("LLM 초기화 중..."):
            llm_handler = LLMHandler(model_name=model_name)
        
        # Agent 초기화
        with st.spinner("Agent 초기화 중..."):
            classifier = EmailClassifier(llm_handler)
            priority_analyzer = PriorityAnalyzer(llm_handler)
            response_drafter = ResponseDrafter(llm_handler)
        
        # 이메일 가져오기
        with st.spinner(f"📬 받은메일함에서 {num_emails}개 이메일 가져오는 중..."):
            gmail_client = st.session_state.gmail_client
            emails = gmail_client.get_emails(max_results=num_emails)
            
            if not emails:
                st.warning("받은메일함에 이메일이 없습니다.")
                return
            
            st.session_state.emails = emails
        
        # 분석 프로그레스
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 1단계: 분류
        status_text.text("🤖 EmailClassifier Agent 작동 중...")
        classified_emails = classifier.batch_classify(emails)
        progress_bar.progress(33)
        
        # 2단계: 우선순위 분석
        status_text.text("🤖 PriorityAnalyzer Agent 작동 중...")
        analyzed_emails = priority_analyzer.batch_analyze(classified_emails)
        progress_bar.progress(66)
        
        # 3단계: 답변 초안 생성
        status_text.text("🤖 ResponseDrafter Agent 작동 중...")
        final_emails = response_drafter.batch_draft(analyzed_emails)
        progress_bar.progress(100)
        
        # 우선순위에 따라 정렬
        sorted_emails = priority_analyzer.sort_by_priority(final_emails)
        
        st.session_state.analyzed_emails = sorted_emails
        
        status_text.text("✅ 분석 완료!")
        progress_bar.empty()
        
        st.rerun()
        
    except ValueError as e:
        st.error(f"❌ 설정 오류: {str(e)}")
        st.info("📝 `.env` 파일을 생성하고 `OPENAI_API_KEY`를 설정하세요.")
    except Exception as e:
        st.error(f"❌ 분석 오류: {str(e)}")


def display_results():
    """분석 결과 표시"""
    
    st.header("3️⃣ 분석 결과")
    
    emails = st.session_state.analyzed_emails
    
    # 통계 정보
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📧 총 이메일", len(emails))
    
    with col2:
        high_priority = sum(
            1 for email in emails
            if email.get('priority_analysis', {}).get('priority') == 'high'
        )
        st.metric("🔴 긴급", high_priority)
    
    with col3:
        need_response = sum(
            1 for email in emails
            if email.get('response_draft', {}).get('should_respond', False)
        )
        st.metric("✍️ 답변 필요", need_response)
    
    with col4:
        spam_count = sum(
            1 for email in emails
            if email.get('classification', {}).get('category') == 'spam'
        )
        st.metric("🗑️ 스팸", spam_count)
    
    st.markdown("---")
    
    # 필터
    st.subheader("🔍 필터")
    
    col1, col2 = st.columns(2)
    
    with col1:
        category_filter = st.multiselect(
            "카테고리",
            options=list(EMAIL_CATEGORIES.keys()),
            default=list(EMAIL_CATEGORIES.keys()),
            format_func=lambda x: f"{EMAIL_CATEGORIES[x]['icon']} {EMAIL_CATEGORIES[x]['label']}"
        )
    
    with col2:
        priority_filter = st.multiselect(
            "우선순위",
            options=list(PRIORITY_LEVELS.keys()),
            default=list(PRIORITY_LEVELS.keys()),
            format_func=lambda x: f"{PRIORITY_LEVELS[x]['icon']} {PRIORITY_LEVELS[x]['label']}"
        )
    
    # 필터링된 이메일
    filtered_emails = [
        email for email in emails
        if email.get('classification', {}).get('category', 'work') in category_filter
        and email.get('priority_analysis', {}).get('priority', 'medium') in priority_filter
    ]
    
    st.info(f"📊 **{len(filtered_emails)}개** 이메일 표시 중")
    
    # 이메일 카드
    for idx, email in enumerate(filtered_emails):
        display_email_card(email, idx)


def display_email_card(email: Dict, idx: int):
    """이메일 카드 표시"""
    
    classification = email.get('classification', {})
    priority_analysis = email.get('priority_analysis', {})
    response_draft = email.get('response_draft', {})
    
    category = classification.get('category', 'work')
    priority = priority_analysis.get('priority', 'medium')
    
    category_info = EMAIL_CATEGORIES.get(category, EMAIL_CATEGORIES['work'])
    priority_info = PRIORITY_LEVELS.get(priority, PRIORITY_LEVELS['medium'])
    
    # 카드 헤더
    with st.expander(
        f"{category_info['icon']} {priority_info['icon']} **{email['subject']}** "
        f"_(발신: {email['from'][:30]}...)_",
        expanded=(idx < 3)  # 처음 3개만 펼쳐서 표시
    ):
        # 메타 정보
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.caption(f"**카테고리**: {category_info['label']}")
        
        with col2:
            st.caption(f"**우선순위**: {priority_info['label']}")
        
        with col3:
            urgency_score = priority_analysis.get('urgency_score', 5)
            st.caption(f"**긴급도**: {urgency_score}/10")
        
        st.markdown("---")
        
        # 이메일 내용
        st.markdown("### 📨 이메일 내용")
        
        with st.container():
            st.text(f"발신자: {email['from']}")
            st.text(f"날짜: {email.get('date', 'N/A')}")
            st.markdown(f"**제목**: {email['subject']}")
            
            with st.expander("본문 보기"):
                st.text(email['body'][:1000] + "..." if len(email['body']) > 1000 else email['body'])
        
        # 답변 초안
        if response_draft.get('should_respond', False):
            st.markdown("---")
            st.markdown("### ✍️ 답변 초안")
            
            draft_text = response_draft.get('draft', '')
            
            st.text_area(
                "답변 내용",
                value=draft_text,
                height=200,
                key=f"draft_{idx}",
                help="이 텍스트를 복사하여 Gmail에서 답장할 수 있습니다."
            )
            
            col1, col2 = st.columns([1, 4])
            
            with col1:
                if st.button("📋 복사", key=f"copy_{idx}"):
                    st.success("✅ 복사되었습니다!")
                    # 실제 클립보드 복사는 JavaScript 필요
            
            with col2:
                st.caption(f"톤: {response_draft.get('tone', 'formal')}")
        
        else:
            st.info(f"ℹ️ {response_draft.get('reason', '답변이 필요하지 않습니다.')}")


if __name__ == "__main__":
    main()

