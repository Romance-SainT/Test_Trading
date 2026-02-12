import streamlit as st
import requests
import time
import pandas as pd
import os
from datetime import datetime

# ==========================================
# [1] 페이지 기본 설정
# ==========================================
st.set_page_config(
    page_title="Crypto Master Sim",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# [2] 보안 설정
# ==========================================
MY_PASSWORD = "7777" 

if 'login_status' not in st.session_state:
    st.session_state['login_status'] = False

if not st.session_state['login_status']:
    st.title("🔒 Private Access")
    input_pw = st.text_input("비밀번호를 입력하세요 (Password)", type="password")
    
    if st.button("로그인 (Login)"):
        if input_pw == MY_PASSWORD:
            st.session_state['login_status'] = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다!")
    st.stop()

# ==========================================
# [3] 스타일 설정
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #1e272e; }
    .notranslate { transform: translateZ(0); -webkit-font-smoothing: antialiased; }
    .block-container { padding-top: 4rem; max_width: 100%; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #1e272e; }
    .stTabs [data-baseweb="tab"] { background-color: #2d3436; border-radius: 5px; color: white; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #00d2d3; color: black; font-weight: bold; }
    .stSelectbox label { color: white !important; text-align: center; width: 100%; }
    .main-title { font-family: 'Helvetica', sans-serif; font-weight: 800; color: #00d2d3; text-align: center; white-space: nowrap; margin: 10px 0; }
    .header-upbit { color: #f1c40f; font-weight: bold; text-align: center; }
    .header-binance { color: #f39c12; font-weight: bold; text-align: center; }
    .ob-container { font-family: 'Consolas', monospace; text-align: center; background-color: #1e272e; padding: 5px 0; flex-grow: 1; }
    .ob-row { display: flex; justify-content: center; align-items: center; line-height: 1.4; white-space: nowrap; }
    .current-box { margin: 15px 0; text-align: center; background-color: #25282d; border-top: 1px solid #444; border-bottom: 1px solid #444; padding: 15px 0; width: 100%; display: flex; flex-direction: column; justify-content: center; }
    .curr-main { font-weight: bold; color: white; letter-spacing: -1px; }
    .ask-text { color: #5DADE2; }
    .bid-text { color: #EC7063; }
    .price-col { width: 140px; text-align: right; }
    .qty-col { width: 110px; text-align: left; }
    .sep-col { width: 30px; text-align: center; color: #555; }
    @media (min-width: 601px) { .main-title { font-size: 2.5rem; } .ob-row { font-size: 1.2rem; } .curr-main { font-size: 2.5rem; } }
    @media (max-width: 600px) { .main-title { font-size: 1.5rem; } .ob-row { font-size: 0.8rem; } .price-col { width: 55%; } .qty-col { width: 40%; } .curr-main { font-size: 1.5rem; } }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# [4] 전역 변수
# ==========================================
COIN_MENU = {
    "BTC (비트코인)": "BTC", "ETH (이더리움)": "ETH", "XRP (리플)": "XRP",
    "SOL (솔라나)": "SOL", "DOGE (도지코인)": "DOGE", "SAND (샌드박스)": "SAND"
}
HISTORY_FILE = "trade_history.csv"

if 'balance' not in st.session_state:
    st.session_state['balance'] = 10000000 
if 'position' not in st.session_state:
    st.session_state['position'] = None 

# ==========================================
# [5] 데이터 수집 함수 (디버깅 강화 버전)
# ==========================================
def get_data(symbol):
    # 헤더 강화
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        # 1. 환율
        try:
            rate_res = requests.get("https://open.er-api.com/v6/latest/USD", headers=headers, timeout=5).json()
            rate = rate_res['rates']['KRW']
        except Exception as e:
            # 환율 에러나면 기본값 쓰고 넘어감 (에러 메시지 안 띄움)
            rate = 1450.0

        # 2. 업비트 API (타임아웃 5초로 증가)
        u_url = f"https://api.upbit.com/v1/ticker?markets=KRW-{symbol}"
        u_res = requests.get(u_url, headers=headers, timeout=5)
        
        if u_res.status_code != 200:
            return {"error": f"업비트 접속 실패 ({u_res.status_code})"}
            
        u_ticker = u_res.json()[0]
        
        u_ob_url = f"https://api.upbit.com/v1/orderbook?markets=KRW-{symbol}"
        u_ob = requests.get(u_ob_url, headers=headers, timeout=5).json()[0]['orderbook_units'][:5]
        
        # 3. 바이낸스 API (타임아웃 5초로 증가)
        b_ticker_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        b_res = requests.get(b_ticker_url, headers=headers, timeout=5)
        
        if b_res.status_code != 200:
            return {"error": f"바이낸스 접속 실패 ({b_res.status_code})"}
            
        b_ticker = b_res.json()
        
        b_ob_url = f"https://api.binance.com/api/v3/depth?symbol={symbol}USDT&limit=5"
        b_ob = requests.get(b_ob_url, headers=headers, timeout=5).json()

        return {
            'rate': rate,
            'u_p': u_ticker['trade_price'],
            'u_asks': sorted(u_ob, key=lambda x: x['ask_price'], reverse=True),
            'u_bids': u_ob,
            'b_p': float(b_ticker['price']),
            'b_asks': sorted(b_ob['asks'], key=lambda x: float(x[0]), reverse=True),
            'b_bids': b_ob['bids'],
            'premium': ((u_ticker['trade_price'] - (float(b_ticker['price']) * rate)) / (float(b_ticker['price']) * rate)) * 100
        }
    except Exception as e:
        # [중요] 어떤 에러인지 텍스트로 반환
        return {"error": str(e)}

# ==========================================
# [6] 파일 입출력
# ==========================================
def save_trade(trade_data):
    df = pd.DataFrame([trade_data])
    if not os.path.exists(HISTORY_FILE):
        df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

def load_trades():
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    return pd.DataFrame()

# ==========================================
# [7] UI 구성
# ==========================================
col_dum1, col_sel, col_dum2 = st.columns([1, 2, 1])
with col_sel:
    sel_coin = st.selectbox("코인 선택", list(COIN_MENU.keys()), label_visibility="collapsed")
sym = COIN_MENU[sel_coin]

st.markdown(f"<div class='main-title notranslate'>Target: {sel_coin}</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 실시간 시세 (Monitor)", "🎮 모의 투자 (Simulation)"])

with tab1:
    monitor_placeholder = st.empty()

with tab2:
    st.markdown("### 💼 투자 현황 (Portfolio Status)")
    portfolio_placeholder = st.empty() 
    st.divider()

    sim_controls = st.container()
    
    with sim_controls:
        if st.session_state['position'] is None:
            invest_amount = st.number_input("투자할 금액 (원화 KRW)", min_value=100000, max_value=int(st.session_state['balance']), value=1000000, step=100000, key="invest_input")
            
            if st.button("🚀 포지션 진입 (업비트 매수 + 바이낸스 숏 10배)", key="btn_buy"):
                current_data = get_data(sym)
                # 데이터가 있고 에러가 없을 때만 실행
                if current_data and 'error' not in current_data:
                    u_price = current_data['u_p']
                    b_price = current_data['b_p']
                    rate = current_data['rate']
                    
                    btc_qty = invest_amount / u_price
                    entry_kimp = current_data['premium']
                    
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
                    st.session_state['balance'] -= invest_amount
                    st.rerun()
                else:
                    st.error("데이터 통신 에러로 진입 실패! (잠시 후 다시 시도하세요)")
        
        else:
            pnl_placeholder = st.empty()
            
            if st.button("💰 포지션 종료 (수익실현/손절)", key="btn_sell"):
                current_data = get_data(sym)
                if current_data and 'error' not in current_data:
                    pos = st.session_state['position']
                    curr_u_price = current_data['u_p']
                    curr_b_price = current_data['b_p']
                    curr_rate = current_data['rate']
                    
                    pnl_upbit = (curr_u_price - pos['u_entry']) * pos['qty']
                    pnl_binance_krw = (pos['b_entry'] - curr_b_price) * pos['qty'] * curr_rate
                    total_pnl = pnl_upbit + pnl_binance_krw
                    pnl_percent = (total_pnl / pos['invest_krw']) * 100
                    
                    exit_kimp = current_data['premium']

                    st.session_state['balance'] += (pos['invest_krw'] + total_pnl)
                    
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
                    
                    st.session_state['position'] = None
                    st.success("거래 종료 성공!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("데이터 통신 에러로 종료 실패! (잠시 후 다시 시도하세요)")

    st.markdown("### 📜 상세 매매 기록")
    history_df = load_trades()
    if not history_df.empty:
        st.dataframe(history_df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("거래 기록 없음")


# ==========================================
# [8] 루프: 실시간 데이터 갱신
# ==========================================
while True:
    d = get_data(sym)
    
    # [수정] 데이터가 정상적으로 왔는지 확인
    if d and 'error' not in d:
        # --- [Tab 1] 시세 업데이트 ---
        with monitor_placeholder.container():
            p_color = "#ff6b6b" if d['premium'] >= 0 else "#54a0ff"
            st.markdown(f"""
            <div style='text-align:center; color:#bdc3c7; font-size:1.0rem; margin-bottom:15px;' class='notranslate'>
                환율(USD/KRW): <b>{d['rate']:,.1f}</b> | <span style='color:{p_color}; font-weight:bold;'>김치: {d['premium']:+.2f}%</span>
            </div>
            """, unsafe_allow_html=True)

            u_html = f"<div class='header-upbit'>Upbit</div><div style='color:#5DADE2; font-size:0.7rem; text-align:center;'>▼ Sell</div>"
            for it in d['u_asks']:
                u_html += f"<div class='ob-row'><span class='price-col ask-text'>{it['ask_price']:,.0f}</span><span class='sep-col'>|</span><span class='qty-col ask-text'>{it['ask_size']:.3f}</span></div>"
            u_html += f"<div class='current-box'><div class='curr-main'>₩{d['u_p']:,.0f}</div><div class='curr-sub' style='visibility:hidden'>(Spacer)</div></div>"
            u_html += f"<div style='color:#EC7063; font-size:0.7rem; text-align:center;'>▲ Buy</div>"
            for it in d['u_bids']:
                u_html += f"<div class='ob-row'><span class='price-col bid-text'>{it['bid_price']:,.0f}</span><span class='sep-col'>|</span><span class='qty-col bid-text'>{it['bid_size']:.3f}</span></div>"

            b_html = f"<div class='header-binance'>Binance</div><div style='color:#5DADE2; font-size:0.7rem; text-align:center;'>▼ Sell</div>"
            for it in d['b_asks']:
                b_html += f"<div class='ob-row'><span class='price-col ask-text'>{float(it[0]):,.2f}</span><span class='sep-col'>|</span><span class='qty-col ask-text'>{float(it[1]):.3f}</span></div>"
            b_html += f"<div class='current-box'><div class='curr-main'>${d['b_p']:,.2f}</div><div class='curr-sub'>(≈₩{d['b_p']*d['rate']:,.0f})</div></div>"
            b_html += f"<div style='color:#EC7063; font-size:0.7rem; text-align:center;'>▲ Buy</div>"
            for it in d['b_bids']:
                b_html += f"<div class='ob-row'><span class='price-col bid-text'>{float(it[0]):,.2f}</span><span class='sep-col'>|</span><span class='qty-col bid-text'>{float(it[1]):.3f}</span></div>"

            st.markdown(f"""
            <div style='display:flex; width:100%; align-items:stretch;' class='notranslate'>
                <div class='ob-container' style='flex:1;'>{u_html}</div>
                <div style='width:1px; background-color:#444;'></div>
                <div class='ob-container' style='flex:1;'>{b_html}</div>
            </div>
            """, unsafe_allow_html=True)

        # --- [Tab 2] 모의 투자 업데이트 ---
        with portfolio_placeholder.container():
            c1, c2 = st.columns(2)
            c1.metric("가상 원화 잔고", f"{st.session_state['balance']:,.0f} 원")
            status_text = "🟢 포지션 보유 중" if st.session_state['position'] else "⚪ 대기 중 (미보유)"
            c2.metric("투자 상태", status_text)

        if st.session_state['position']:
            with pnl_placeholder.container():
                pos = st.session_state['position']
                curr_u_price = d['u_p']
                curr_b_price = d['b_p']
                curr_rate = d['rate']
                
                pnl_upbit = (curr_u_price - pos['u_entry']) * pos['qty']
                pnl_binance_krw = (pos['b_entry'] - curr_b_price) * pos['qty'] * curr_rate
                total_pnl = pnl_upbit + pnl_binance_krw
                pnl_percent = (total_pnl / pos['invest_krw']) * 100
                
                st.markdown(f"**현재 모니터링 중인 코인:** {pos['symbol']}")
                m1, m2, m3 = st.columns(3)
                m1.metric("업비트 손익", f"{pnl_upbit:,.0f} 원")
                m2.metric("바이낸스 숏 손익", f"{pnl_binance_krw:,.0f} 원")
                m3.metric("🔥 합계 손익 (수익률)", f"{total_pnl:,.0f} 원", f"{pnl_percent:.2f}%")
                
                entry_kimp = pos['entry_kimp']
                st.info(f"진입 시 김프: {entry_kimp:.2f}%  👉  현재 김프: {d['premium']:.2f}%")
    
    # [수정] 에러가 발생했을 경우 화면에 표시
    elif d and 'error' in d:
        with monitor_placeholder.container():
            st.warning(f"데이터 수신 대기 중... (원인: {d['error']})")
            time.sleep(2) # 너무 빨리 깜빡거리지 않게 대기

    # 1초 대기
    time.sleep(1)