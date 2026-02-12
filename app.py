# [app.py 맨 윗부분에 이 코드를 추가하세요]
import streamlit as st

# ... (기존 import들) ...

# ==========================================
# [보안] 비밀번호 잠금 기능 (Simple Login)
# ==========================================
# 1. 비밀번호 설정 (원하는 걸로 바꾸세요)
MY_PASSWORD = "1110"

if 'login_status' not in st.session_state:
    st.session_state['login_status'] = False

if not st.session_state['login_status']:
    st.title("🔒 Private Access")
    input_pw = st.text_input("비밀번호를 입력하세요 (Password)", type="password")
    
    if st.button("로그인 (Login)"):
        if input_pw == MY_PASSWORD:
            st.session_state['login_status'] = True
            st.rerun() # 화면 새로고침해서 메인화면 보여줌
        else:
            st.error("비밀번호가 틀렸습니다!")
    
    st.stop() # 비밀번호 틀리면 여기서 코드 실행을 멈춤 (아래 내용 안 보여줌)
import streamlit as st  # 웹 앱 생성을 위한 라이브러리
import requests         # API 통신(업비트, 바이낸스, 환율 서버)을 위한 라이브러리
import time             # 1초 대기 등 시간 제어를 위해 사용
import pandas as pd     # 거래 내역(CSV)을 엑셀처럼 다루기 위해 사용
import os               # 파일 경로 확인 및 삭제/생성을 위해 사용
from datetime import datetime # 거래 시간 기록용

# ==========================================
# [1] 페이지 기본 설정
# ==========================================
# 웹 브라우저 탭의 제목과 레이아웃(Wide 모드)을 설정합니다.
# initial_sidebar_state="collapsed"는 모바일에서 사이드바가 거슬리지 않게 숨기는 설정입니다.
st.set_page_config(
    page_title="Crypto Master Sim",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# [2] CSS 스타일링 (디자인 커스터마이징)
# ==========================================
# Streamlit의 기본 디자인을 덮어쓰고, PC/모바일 반응형 레이아웃을 구현하는 핵심 코드입니다.
st.markdown("""
    <style>
    /* 전체 배경색을 어두운 네이비(#1e272e)로 설정하여 눈을 편안하게 함 */
    .stApp { background-color: #1e272e; }
    
    /* [중요] 구글 번역기가 숫자를 멋대로 바꾸지 못하게 막는 클래스 */
    .notranslate { transform: translateZ(0); -webkit-font-smoothing: antialiased; }
    
    /* 상단 여백 설정: 콤보박스가 잘리지 않도록 4rem 정도 띄움 */
    .block-container {
        padding-top: 4rem; 
        max_width: 100%;
    }

    /* 탭(Tab) 디자인 커스터마이징 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #1e272e;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #2d3436; /* 탭 기본 배경색 */
        border-radius: 5px;
        color: white;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00d2d3; /* 선택된 탭 강조색 (민트색) */
        color: black;
        font-weight: bold;
    }

    /* 콤보박스(Selectbox) 라벨을 흰색으로 변경 및 중앙 정렬 */
    .stSelectbox label { color: white !important; text-align: center; width: 100%; }

    /* 메인 타이틀 폰트 및 스타일 */
    .main-title {
        font-family: 'Helvetica', sans-serif;
        font-weight: 800;
        color: #00d2d3;
        text-align: center;
        white-space: nowrap; /* 줄바꿈 방지 */
        margin: 10px 0;
    }
    
    /* 호가창(Orderbook) 관련 스타일 */
    .header-upbit { color: #f1c40f; font-weight: bold; text-align: center; }   /* 업비트: 노랑 */
    .header-binance { color: #f39c12; font-weight: bold; text-align: center; } /* 바이낸스: 오렌지 */
    
    .ob-container { 
        font-family: 'Consolas', monospace; /* 숫자 간격이 일정한 고정폭 폰트 사용 */
        text-align: center; 
        background-color: #1e272e; 
        padding: 5px 0; 
        flex-grow: 1; 
    }
    .ob-row { 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        line-height: 1.4; 
        white-space: nowrap; /* 숫자가 길어도 줄바꿈 안 되게 강제 */
    }
    
    /* 현재가 표시 박스 (중앙) */
    .current-box { 
        margin: 15px 0; 
        text-align: center; 
        background-color: #25282d; /* 배경을 살짝 밝게 하여 구분감 줌 */
        border-top: 1px solid #444; 
        border-bottom: 1px solid #444; 
        padding: 15px 0; 
        width: 100%; 
        display: flex; 
        flex-direction: column; 
        justify-content: center; 
    }
    .curr-main { font-weight: bold; color: white; letter-spacing: -1px; }
    
    /* 텍스트 색상 정의 */
    .ask-text { color: #5DADE2; } /* 매도: 파랑 */
    .bid-text { color: #EC7063; } /* 매수: 빨강 */
    
    /* 호가창 컬럼 너비 고정 (숫자 위치 정렬을 위해) */
    .price-col { width: 140px; text-align: right; }
    .qty-col { width: 110px; text-align: left; }
    .sep-col { width: 30px; text-align: center; color: #555; }

    /* [반응형] 화면 크기에 따라 폰트 크기 자동 조절 */
    @media (min-width: 601px) { /* PC 화면 */
        .main-title { font-size: 2.5rem; }
        .ob-row { font-size: 1.2rem; }
        .curr-main { font-size: 2.5rem; }
    }
    @media (max-width: 600px) { /* 모바일 화면 */
        .main-title { font-size: 1.5rem; }
        .ob-row { font-size: 0.8rem; }
        .price-col { width: 55%; }
        .qty-col { width: 40%; }
        .curr-main { font-size: 1.5rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# [3] 전역 변수 및 세션 초기화
# ==========================================
# 코인 목록 정의 (표시 이름 : API 심볼)
COIN_MENU = {
    "BTC (비트코인)": "BTC", "ETH (이더리움)": "ETH", "XRP (리플)": "XRP",
    "SOL (솔라나)": "SOL", "DOGE (도지코인)": "DOGE", "SAND (샌드박스)": "SAND"
}
HISTORY_FILE = "trade_history.csv" # 매매 기록을 저장할 파일명

# Streamlit은 화면이 갱신될 때마다 변수가 초기화되므로,
# 값을 계속 기억해야 하는 '잔고'와 '포지션'은 session_state에 저장합니다.
if 'balance' not in st.session_state:
    st.session_state['balance'] = 10000000 # 초기 가상 자산: 1,000만원
if 'position' not in st.session_state:
    st.session_state['position'] = None # 현재 보유 중인 포지션 없음

# ==========================================
# [4] 데이터 수집 함수 (API)
# ==========================================
def get_data(symbol):
    """
    환율, 업비트, 바이낸스 API를 호출하여 최신 데이터를 가져오는 함수입니다.
    """
    try:
        # 1. 환율 정보 가져오기 (API 오류 시 1450원으로 고정)
        try:
            rate_res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=1).json()
            rate = rate_res['rates']['KRW']
        except:
            rate = 1450.0

        # 2. 업비트 API 호출 (현재가 + 호가창)
        u_ticker = requests.get(f"https://api.upbit.com/v1/ticker?markets=KRW-{symbol}").json()[0]
        u_ob = requests.get(f"https://api.upbit.com/v1/orderbook?markets=KRW-{symbol}").json()[0]['orderbook_units'][:5]
        
        # 3. 바이낸스 API 호출 (현재가 + 호가창)
        b_ticker = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT").json()
        b_ob = requests.get(f"https://api.binance.com/api/v3/depth?symbol={symbol}USDT&limit=5").json()

        # 4. 데이터 정리 및 김치 프리미엄 계산
        return {
            'rate': rate,
            'u_p': u_ticker['trade_price'],
            # 매도(Ask)는 가격이 높은 순서대로 정렬해야 호가창 위쪽에 옴
            'u_asks': sorted(u_ob, key=lambda x: x['ask_price'], reverse=True),
            'u_bids': u_ob,
            'b_p': float(b_ticker['price']),
            'b_asks': sorted(b_ob['asks'], key=lambda x: float(x[0]), reverse=True),
            'b_bids': b_ob['bids'],
            # 김프 계산 공식: ((업비트가 - 해외환산가) / 해외환산가) * 100
            'premium': ((u_ticker['trade_price'] - (float(b_ticker['price']) * rate)) / (float(b_ticker['price']) * rate)) * 100
        }
    except:
        return None # 에러 발생 시 None 반환

# ==========================================
# [5] 파일 입출력 함수
# ==========================================
def save_trade(trade_data):
    """매매가 종료되었을 때 결과를 CSV 파일에 저장합니다."""
    df = pd.DataFrame([trade_data])
    if not os.path.exists(HISTORY_FILE):
        # 파일이 없으면 헤더(제목) 포함해서 생성
        df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else:
        # 파일이 있으면 내용만 추가 (mode='a')
        df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

def load_trades():
    """저장된 매매 기록을 불러옵니다."""
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    return pd.DataFrame() # 파일 없으면 빈 데이터프레임 반환

# ==========================================
# [6] 메인 UI 구성 (입력 위젯 배치)
# ==========================================

# 1. 상단 코인 선택 콤보박스 (중앙 정렬을 위해 3단 컬럼 사용)
col_dum1, col_sel, col_dum2 = st.columns([1, 2, 1])
with col_sel:
    sel_coin = st.selectbox("코인 선택", list(COIN_MENU.keys()), label_visibility="collapsed")
sym = COIN_MENU[sel_coin]

# 선택된 코인 이름 크게 표시
st.markdown(f"<div class='main-title notranslate'>Target: {sel_coin}</div>", unsafe_allow_html=True)

# 2. 탭 구성 (모니터링 탭 / 모의투자 탭)
tab1, tab2 = st.tabs(["📊 실시간 시세 (Monitor)", "🎮 모의 투자 (Simulation)"])

# --- [Tab 1] 실시간 시세 영역 (내용은 루프 안에서 채움) ---
with tab1:
    monitor_placeholder = st.empty() # 나중에 내용을 계속 갈아끼우기 위한 빈 공간 예약

# --- [Tab 2] 모의 투자 영역 ---
with tab2:
    st.markdown("### 💼 투자 현황 (Portfolio Status)")
    
    # 상단 잔고 표시용 공간 예약
    portfolio_placeholder = st.empty() 
    st.divider()

    # 매매 버튼 및 입력창 (주의: 무한루프 밖에서 선언해야 에러가 안 남)
    sim_controls = st.container()
    
    with sim_controls:
        # [상황 A] 포지션이 없을 때 -> '진입' 화면 표시
        if st.session_state['position'] is None:
            invest_amount = st.number_input("투자할 금액 (원화 KRW)", min_value=100000, max_value=int(st.session_state['balance']), value=1000000, step=100000, key="invest_input")
            
            if st.button("🚀 포지션 진입 (업비트 매수 + 바이낸스 숏 10배)", key="btn_buy"):
                # 버튼을 누른 순간의 최신 데이터 가져오기
                current_data = get_data(sym)
                if current_data:
                    u_price = current_data['u_p']
                    b_price = current_data['b_p']
                    rate = current_data['rate']
                    
                    # 투자금에 맞춰 업비트 매수 수량 계산
                    btc_qty = invest_amount / u_price
                    
                    # 진입 시점의 김치 프리미엄 저장 (나중에 비교용)
                    entry_kimp = current_data['premium']
                    
                    # 세션에 포지션 정보 저장 (로그인 정보처럼 유지됨)
                    st.session_state['position'] = {
                        'symbol': sym,
                        'entry_time': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'invest_krw': invest_amount,
                        'u_entry': u_price,
                        'b_entry': b_price,
                        'qty': btc_qty,
                        'rate_entry': rate,
                        'entry_kimp': entry_kimp
                    }
                    st.session_state['balance'] -= invest_amount # 잔고 차감
                    st.rerun() # 화면 즉시 새로고침하여 상태 반영
        
        # [상황 B] 포지션이 있을 때 -> '청산' 화면 표시
        else:
            pnl_placeholder = st.empty() # 실시간 수익률 표시 공간
            
            if st.button("💰 포지션 종료 (수익실현/손절)", key="btn_sell"):
                current_data = get_data(sym)
                if current_data:
                    pos = st.session_state['position']
                    curr_u_price = current_data['u_p']
                    curr_b_price = current_data['b_p']
                    curr_rate = current_data['rate']
                    
                    # 수익금 계산 로직
                    # 1. 업비트(현물): (현재가 - 진입가) * 수량
                    pnl_upbit = (curr_u_price - pos['u_entry']) * pos['qty']
                    # 2. 바이낸스(숏): (진입가 - 현재가) * 수량 * 환율 
                    # (숏은 가격이 떨어져야 이득이므로 진입가에서 현재가를 뺌)
                    pnl_binance_krw = (pos['b_entry'] - curr_b_price) * pos['qty'] * curr_rate
                    
                    total_pnl = pnl_upbit + pnl_binance_krw
                    pnl_percent = (total_pnl / pos['invest_krw']) * 100
                    
                    # 종료 시점 김프
                    exit_kimp = current_data['premium']

                    # 잔고에 원금 + 수익금 합산
                    st.session_state['balance'] += (pos['invest_krw'] + total_pnl)
                    
                    # 거래 기록 저장 (사용자가 요청한 상세 항목 포함)
                    save_trade({
                        "Time (시간)": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Coin (코인)": pos['symbol'],
                        "Qty (수량)": f"{pos['qty']:.6f}",
                        "Invest (투자금)": int(pos['invest_krw']),
                        "Entry Kimp (진입 김프)": f"{pos['entry_kimp']:.2f}%",
                        "Exit Kimp (종료 김프)": f"{exit_kimp:.2f}%",
                        "U.Entry (업 진입)": int(pos['u_entry']),
                        "U.Exit (업 종료)": int(curr_u_price),
                        "B.Entry (바 진입)": f"${pos['b_entry']:.2f}",
                        "B.Exit (바 종료)": f"${curr_b_price:.2f}",
                        "U.PNL (업 손익)": int(pnl_upbit),
                        "B.PNL (바 손익)": int(pnl_binance_krw),
                        "Total PNL (총 손익)": int(total_pnl),
                        "ROI (수익률)": f"{pnl_percent:.2f}%"
                    })
                    
                    st.session_state['position'] = None # 포지션 초기화
                    st.success("거래가 종료되었습니다! 상세 내역이 저장되었습니다.")
                    time.sleep(1)
                    st.rerun() # 화면 새로고침

    # 하단 거래 내역 표시
    st.markdown("### 📜 상세 매매 기록 (Detailed Trade History)")
    history_df = load_trades()
    if not history_df.empty:
        # 최신 거래가 위로 오도록 정렬하여 표시
        st.dataframe(history_df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("아직 완료된 거래 기록이 없습니다.")


# ==========================================
# [7] 무한 루프 (실시간 데이터 갱신 및 표시)
# ==========================================
while True:
    d = get_data(sym) # 데이터 가져오기
    
    if d:
        # --- [Tab 1] 실시간 시세 화면 업데이트 ---
        with monitor_placeholder.container():
            # 김프가 양수면 빨강, 음수면 파랑 색상 지정
            p_color = "#ff6b6b" if d['premium'] >= 0 else "#54a0ff"
            
            # 상단 정보바 출력
            st.markdown(f"""
            <div style='text-align:center; color:#bdc3c7; font-size:1.0rem; margin-bottom:15px;' class='notranslate'>
                환율(USD/KRW): <b>{d['rate']:,.1f}</b> | <span style='color:{p_color}; font-weight:bold;'>김치 프리미엄: {d['premium']:+.2f}%</span>
            </div>
            """, unsafe_allow_html=True)

            # 1. 업비트 호가창 HTML 생성
            u_html = f"<div class='header-upbit'>Upbit (업비트)</div><div style='color:#5DADE2; font-size:0.7rem; text-align:center;'>▼ 매도(Ask)</div>"
            for it in d['u_asks']:
                u_html += f"<div class='ob-row'><span class='price-col ask-text'>{it['ask_price']:,.0f}</span><span class='sep-col'>|</span><span class='qty-col ask-text'>{it['ask_size']:.3f}</span></div>"
            
            # [Spacer Hack] 바이낸스 환산가 줄 때문에 생기는 높이 차이를 맞추기 위해, 업비트에도 투명한 글씨를 넣어 높이를 맞춤
            u_html += f"<div class='current-box'><div class='curr-main'>₩{d['u_p']:,.0f}</div><div class='curr-sub' style='visibility:hidden'>(Spacer)</div></div>"
            
            u_html += f"<div style='color:#EC7063; font-size:0.7rem; text-align:center;'>▲ 매수(Bid)</div>"
            for it in d['u_bids']:
                u_html += f"<div class='ob-row'><span class='price-col bid-text'>{it['bid_price']:,.0f}</span><span class='sep-col'>|</span><span class='qty-col bid-text'>{it['bid_size']:.3f}</span></div>"

            # 2. 바이낸스 호가창 HTML 생성
            b_html = f"<div class='header-binance'>Binance (바이낸스)</div><div style='color:#5DADE2; font-size:0.7rem; text-align:center;'>▼ 매도(Ask)</div>"
            for it in d['b_asks']:
                b_html += f"<div class='ob-row'><span class='price-col ask-text'>{float(it[0]):,.2f}</span><span class='sep-col'>|</span><span class='qty-col ask-text'>{float(it[1]):.3f}</span></div>"
            
            # 바이낸스 현재가 밑에는 원화 환산 가격 표시
            b_html += f"<div class='current-box'><div class='curr-main'>${d['b_p']:,.2f}</div><div class='curr-sub'>(≈₩{d['b_p']*d['rate']:,.0f})</div></div>"
            
            b_html += f"<div style='color:#EC7063; font-size:0.7rem; text-align:center;'>▲ 매수(Bid)</div>"
            for it in d['b_bids']:
                b_html += f"<div class='ob-row'><span class='price-col bid-text'>{float(it[0]):,.2f}</span><span class='sep-col'>|</span><span class='qty-col bid-text'>{float(it[1]):.3f}</span></div>"

            # 3. Flexbox로 좌우 배치 출력
            st.markdown(f"""
            <div style='display:flex; width:100%; align-items:stretch;' class='notranslate'>
                <div class='ob-container' style='flex:1;'>{u_html}</div>
                <div style='width:1px; background-color:#444;'></div>
                <div class='ob-container' style='flex:1;'>{b_html}</div>
            </div>
            """, unsafe_allow_html=True)

        # --- [Tab 2] 모의 투자 실시간 손익 업데이트 ---
        with portfolio_placeholder.container():
            c1, c2 = st.columns(2)
            c1.metric("가상 원화 잔고", f"{st.session_state['balance']:,.0f} 원")
            status_text = "🟢 포지션 보유 중" if st.session_state['position'] else "⚪ 대기 중 (미보유)"
            c2.metric("투자 상태", status_text)

        # 포지션이 있을 경우에만 실시간 손익 계산해서 표시
        if st.session_state['position']:
            with pnl_placeholder.container():
                pos = st.session_state['position']
                curr_u_price = d['u_p']
                curr_b_price = d['b_p']
                curr_rate = d['rate']
                
                # 실시간 손익 계산
                pnl_upbit = (curr_u_price - pos['u_entry']) * pos['qty']
                pnl_binance_krw = (pos['b_entry'] - curr_b_price) * pos['qty'] * curr_rate
                total_pnl = pnl_upbit + pnl_binance_krw
                pnl_percent = (total_pnl / pos['invest_krw']) * 100
                
                # 대시보드 출력
                st.markdown(f"**현재 모니터링 중인 코인:** {pos['symbol']}")
                m1, m2, m3 = st.columns(3)
                m1.metric("업비트 손익", f"{pnl_upbit:,.0f} 원")
                m2.metric("바이낸스 숏 손익", f"{pnl_binance_krw:,.0f} 원")
                m3.metric("🔥 합계 손익 (수익률)", f"{total_pnl:,.0f} 원", f"{pnl_percent:.2f}%")
                
                # 김프 변화 정보 표시 (진입 당시 vs 현재)
                entry_kimp = pos['entry_kimp']
                st.info(f"진입 시 김프: {entry_kimp:.2f}%  👉  현재 김프: {d['premium']:.2f}%")

    # 서버 부하 방지 및 API 호출 제한을 위해 1초 대기
    time.sleep(1)