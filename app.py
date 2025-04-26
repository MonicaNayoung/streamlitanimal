import openai
import streamlit as st
import os
import re
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import plotly.graph_objects as go


# --- 설정 ---
st.set_page_config(page_title="퇴사연구소 | 떠남점검 연구소", page_icon="🧪", layout="centered")

# OpenAI API 키 설정
os.environ["OPENAI_API_KEY"] = st.secrets["API_KEY"]
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- 스타일 커스텀 ---
st.markdown("""
    <style>
    body { background-color: #f4f4f4; }
    .big-font {
        font-size: 30px !important;
        text-align: center;
        margin-bottom: 30px;
    }
    .start-button {
        display: flex;
        justify-content: center;
        margin-top: 20px;
    }
    .back-button {
        font-size: 14px;
        color: gray;
        cursor: pointer;
    }
    </style>
""", unsafe_allow_html=True)

# --- 초기 변수 설정 ---
if "history" not in st.session_state:
    st.session_state.history = []
if "current_question" not in st.session_state:
    st.session_state.current_question = "start"
if "risk_score" not in st.session_state:
    st.session_state.risk_score = None
if "full_analysis" not in st.session_state:
    st.session_state.full_analysis = ""
if "leave_type" not in st.session_state:
    st.session_state.leave_type = ""

# --- 질문 로드맵 ---
def next_question(answer, current):
    if current == "start":
        return "Q1"
    if current == "Q1":
        return "Q2" if answer == "yes" else "Q3"
    if current == "Q2":
        return "result"
    if current == "Q3":
        return "Q4" if answer == "yes" else "result"
    if current == "Q4":
        return "Q5" if answer == "yes" else "result"
    if current == "Q5":
        return "Q2" if answer == "yes" else "result"
    return "result"

questions = {
    "Q1": "🧪 **내가 원했던 것을 모두 얻어서** 퇴사를 고민하고 있다.",
    "Q2": "🧪 퇴사를 선택할 경우 아쉬울 만한 것들(새로운 경험, 지식, 보상 등)이 있다.",
    "Q3": "🧪 얻지 못한 것이 무엇인지, 그 원인을 알고 있다.",
    "Q4": "🧪 얻고 싶은 것과 이유를 동료/리더/HR에게 요청해본 적이 있다.",
    "Q5": "🧪 퇴사가 아닌 다른 방법을 모두 시도했다."
}

# --- 떠남 유형 진단 ---
def diagnose_leave_type(history):
    yes_count = sum(1 for _, a in history if a == "yes")
    no_count = sum(1 for _, a in history if a == "no")

    if yes_count >= 4:
        return "전략적 떠남"
    elif no_count >= 4:
        return "충동적 떠남"
    else:
        return "혼합형 떠남"

# --- ChatGPT 결과 생성 부분 ---
def generate_result(history):
    context = "다음은 너의 퇴사 고민 프로세스 기록이야.\n"
    for q, a in history:
        context += f"Q: {questions.get(q, '')}\nA: {a}\n"

    prompt = context + """
너는 단호하고 냉정하지만 유쾌한 말투로, 이 사용자가 퇴사를 해야 하는지, 잔류해야 하는지를 분석해줘. 

단, 결과는 반드시 다음 형식으로 작성해야 해:

1. '퇴사하는 게 좋겠어' 또는 '무슨 퇴사야. 계속 다녀봐' 중에서 결론을 내려.
2. 결론을 제일 위에 Bold(굵게) + 약간 큰 글씨 크기로 표시해.
3. 그 다음에 자세한 이유를 단호하고 유쾌한 톤으로 설명해.
4. 앞으로 어떤 액션 플랜을 취하면 좋을지 조언해줘.
5. 퇴사를 하는 것이 현재 상황에 얼마나 적합한지를 "떠남적합성 지수"라는 이름으로 명칭하고 10점 만점으로 숫자로 매겨줘 (예: 떠남적합성 지수 7/10).
6. 떠남적합성 지수와 너가 1번에서 내린 결론은 분석 결과의 제일 서두에 Bold(굵게) + 분석 내용에서 쓴 글씨 크기보다 조금 더 큰 글씨체로 표기해줘.
7. 분석 결과 마지막에는 항상 분석 결과에 따라 추가적으로 이용할 수 있는 이 프로그램 내에 텅장 연구소(재정 상황을 바탕으로 퇴사 가능여부를 판단해주는 서비스)나 직무분석 연구소(현재 올라와있는 채용 공고들을 알려주는 서비스) 등을 이용하도록 추천하는 내용 한 줄씩 넣어줘.

'너'를 주어로 자연스럽게 조언해줘. 기분 상하지 않게, 하지만 현실을 직시하게 해야 해.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# --- 퇴사 위험도 점수 추출 ---
def extract_score(text):
    match = re.search(r'(\d{1,2})\/10', text)
    if match:
        return int(match.group(1))
    return None

# --- 떠남적합성 지수 시각화 ---
from streamlit_echarts import st_echarts

def plot_risk_score(score):
    option = {
        "series": [
            {
                "type": "liquidFill",
                "data": [score / 10],  # 0~1 사이 값
                "radius": "80%",
                "center": ["50%", "50%"],
                "backgroundStyle": {
                    "borderColor": "#156ACF",
                    "borderWidth": 5,
                    "color": "transparent"
                },
                "outline": {
                    "show": True,
                    "borderDistance": 8,
                    "itemStyle": {
                        "borderWidth": 5,
                        "borderColor": "#92D2F5",
                        "shadowBlur": 10,
                        "shadowColor": "rgba(0, 0, 0, 0.25)"
                    }
                },
                "label": {
                    "formatter": f"{score}/10",
                    "fontSize": 28,
                    "color": "#156ACF"
                },
                "itemStyle": {
                    "opacity": 0.7,
                    "shadowBlur": 0
                },
                "amplitude": 5,  # 물결 높낮이
                "waveAnimation": True,  # 물결 애니메이션
                "color": ["#FF6961"],  # 물 색깔
            }
        ]
    }

    st_echarts(options=option, height="300px")


# --- 메인 화면 ---
if st.session_state.current_question == "start":
    st.markdown("<div class='big-font'>🚀 충동이 아닌, 전략적 퇴사를 위한 셀프 로드맵</div>", unsafe_allow_html=True)
    st.markdown("""
    🧪 **떠남점검 연구소에 온 걸 환영해.**  
    여기는 퇴사를 '충동'이 아니라 '전략'으로 바꾸는 방법을 연구하는 곳이야. 때로는 단순한 감정이 아닌, 더 깊은 이유가 퇴사 고민 뒤에 숨어 있기도 하니까.  
    이 검사는 너의 고민을 과학적으로 풀어내고, 가장 합리적인 결론을 찾아주기 위해 만들어졌어.  
    주저하지 말고 한 번 시작해봐. 떠나느냐, 남느냐, 내가 똑똑하게 판단해줄게. 대신 솔직하게 참여해야 해.
    """)
    with st.container():
        col = st.columns(3)[1]  # 가운데 열
        with col:
            if st.button("🧪 시작하기"):
                st.session_state.current_question = "Q1"
                st.session_state.history = []
                st.rerun()
    st.stop()

# --- 이전 문항으로 돌아가기 ---
if st.session_state.current_question not in ["start", "result"]:
    if st.session_state.history:
        if st.button("⬅ 이전 문항으로 돌아가기", key="back", help="이전 질문으로 돌아갑니다."):
            last = st.session_state.history.pop()
            st.session_state.current_question = last[0]
            st.rerun()

# --- 질문 화면 ---
if st.session_state.current_question != "result":
    question_text = questions.get(st.session_state.current_question, "질문 없음")
    st.markdown(f"### {question_text}")

    st.markdown("<br>", unsafe_allow_html=True)  # 질문과 버튼 사이에 공간 추가

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Yes", key="yes"):
            st.session_state.history.append((st.session_state.current_question, "yes"))
            st.session_state.current_question = next_question("yes", st.session_state.current_question)
            st.rerun()

    with col2:
        if st.button("❌ No", key="no"):
            st.session_state.history.append((st.session_state.current_question, "no"))
            st.session_state.current_question = next_question("no", st.session_state.current_question)
            st.rerun()

if st.session_state.history:
    st.markdown("---")
    st.markdown("### 🧠 지금까지의 답변")
    for q, a in st.session_state.history:
        q_text = questions.get(q, "")
        st.write(f"**{q_text}** → {a.upper()}")

# --- 결과 화면 ---
if st.session_state.current_question == "result":
    st.session_state.leave_type = diagnose_leave_type(st.session_state.history)
    st.markdown(f"### 🧪 나의 떠남 유형: **{st.session_state.leave_type}**")
    st.markdown("---")

    result = generate_result(st.session_state.history)
    st.session_state.full_analysis = result
    st.markdown("### 📝 분석 결과")
    st.write(result)

    # 떠남적합성 지수 추출 및 시각화
    score = extract_score(result)
    if score is not None:
        st.session_state.risk_score = score
        plot_risk_score(score)

    st.markdown("---")
    if st.button("🔄 다시 검사하기"):
        st.session_state.current_question = "Q1"
        st.session_state.history = []
        st.session_state.risk_score = None
        st.session_state.leave_type = ""
        st.rerun()
