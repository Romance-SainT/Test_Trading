import streamlit as st
import requests
import time
import pandas as pd
import os
from datetime import datetime

# ==========================================
# [1] 페이지 설정
# ==========================================
st.set_page_config(
    page_title="Crypto Master Sim (Binance.US)",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# [2] 수수료 설정
# ==========================================
FEE_UPBIT = 0.0005  # 0.05%
FEE_FOREIGN = 0.001 # 0.1%

# ==========================================
# [3] 보안 설정
# ==========================================
MY_PASSWORD = "7777" 

if 'login_status' not in st.session_state:
    st.session_state['login_status'] = False

if not st.session_state['login_status']:
    st.title("🔒 Private Access")
    input_pw = st.text_input("비밀번호를 입력하세요 (Password)", type="password")
    if st.button("로그인"):
        if input_pw == MY_PASSWORD:
            st.session_state['login_status'] = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# ==========================================
# [4] 스타일 (CSS)
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
    
    .fee-info { font-size: 0.8rem; color: #95a5a6; text-align: center; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# [5] 전역 변수
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
# [6] 데이터 수집 (Binance.US)
# ==========================================
def get_data(symbol):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        try:
            rate_res = requests.get("https://open.er-api.com/v6/latest/USD", headers=headers, timeout=3).json()
            rate = rate_res['rates']['KRW']
        except:
            rate = 1450.0

        u_url = f"https://api.upbit.com/v1/ticker?markets=KRW-{symbol}"
        u_res = requests.get(u_url, headers=headers, timeout=3)
        if u_res.status_code != 200: return {"error": f"Upbit {u_res.status_code}"}
        u_ticker = u_res.json()[0]
        
        u_ob_url = f"https://api.upbit.com/v1/orderbook?markets=KRW-{symbol}"
        u_ob = requests.get(u_ob_url, headers=headers, timeout=3).json()[0]['orderbook_units'][:5]
        
        b_ticker_url = f"https://api.binance.us/api/v3/ticker/price?symbol={symbol}USDT"
        b_res = requests.get(b_ticker_url, headers=headers, timeout=3)
        if b_res.status_code != 200: return {"error": f"Binance US Error {b_res.status_code}"}
        b_ticker = b_res.json()
        
        b_ob_url = f"https://api.binance.us/api/v3/depth?symbol={symbol}USDT&limit=5"
        b_ob = requests.get(b_ob_url, headers=headers, timeout=3).json()

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
        return {"error": str(e)}

# ==========================================
# [7] 파일 입출력
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
# [8] UI 구성
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
    st.markdown(f"<div class='fee-info'>※ 수수료: 업비트 {FEE_UPBIT*100}% | 바이낸스(US) {FEE_FOREIGN*100}%</div>", unsafe_allow_html=True)
    
    portfolio_placeholder = st.empty() 
    st.divider()

    sim_controls = st.container()
    
    with sim_controls:
        # A. 진입
        if st.session_state['position'] is None:
            invest_amount = st.number_input("투자할 금액 (원화 KRW)", min_value=100000, max_value=int(st.session_state['balance']), value=1000000, step=100000, key="invest_input")
            
            if st.button("🚀 포지션 진입 (업비트 매수 + 바이낸스 숏)", key="btn_buy"):
                data = get_data(sym)
                if data and 'error' not in data:
                    u_price = data['u_p']
                    b_price = data['b_p']
                    rate = data['rate']
                    
                    btc_qty = invest_amount / u_price
                    entry_fee = (invest_amount * FEE_UPBIT) + (b_price * btc_qty * rate * FEE_FOREIGN)
                    
                    st.session_state['position'] = {
                        'symbol': sym,
                        'entry_time': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'invest_krw': invest_amount,
                        'u_entry': u_price,
                        'b_entry': b_price,
                        'qty': btc_qty,
                        'rate_entry': rate,
                        'entry_kimp': data['premium'],
                        'entry_fee': entry_fee
                    }
                    st.session_state['balance'] -= invest_amount
                    st.rerun()
                else:
                    st.error("데이터 수신 오류!")

        # B. 청산
        else:
            pnl_placeholder = st.empty()
            
            if st.button("💰 포지션 종료 (정산하기)", key="btn_sell"):
                data = get_data(sym)
                if data and 'error' not in data:
                    pos = st.session_state['position']
                    curr_u_price = data['u_p']
                    curr_b_price = data['b_p']
                    curr_rate = data['rate']
                    
                    pnl_upbit = (curr_u_price - pos['u_entry']) * pos['qty']
                    pnl_foreign = (pos['b_entry'] - curr_b_price) * pos['qty'] * curr_rate
                    gross_total = pnl_upbit + pnl_foreign
                    
                    exit_fee = (curr_u_price * pos['qty'] * FEE_UPBIT) + (curr_b_price * pos['qty'] * curr_rate * FEE_FOREIGN)
                    total_fee = pos['entry_fee'] + exit_fee
                    
                    net_pnl = gross_total - total_fee
                    roi = (net_pnl / pos['invest_krw']) * 100
                    
                    st.session_state['balance'] += (pos['invest_krw'] + net_pnl)
                    
                    save_trade({
                        "Time": datetime.now().strftime("%m-%d %H:%M"),
                        "Coin": pos['symbol'],
                        "Invest": int(pos['invest_krw']),
                        "Upbit PNL": int(pnl_upbit),
                        "Binance PNL": int(pnl_foreign),
                        "Fees": int(total_fee),
                        "Net PNL": int(net_pnl),
                        "ROI": f"{roi:.2f}%"
                    })
                    
                    st.session_state['position'] = None
                    st.success(f"거래 종료! 순수익: {int(net_pnl):,}원")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("데이터 수신 오류!")

    st.markdown("### 📜 상세 매매 기록")
    history_df = load_trades()
    if not history_df.empty:
        st.dataframe(history_df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("거래 기록 없음")


# ==========================================
# [9] 루프
# ==========================================
while True:
    d = get_data(sym)
    
    if d and 'error' not in d:
        with monitor_placeholder.container():
            p_color = "#ff6b6b" if d['premium'] >= 0 else "#54a0ff"
            st.markdown(f"""
            <div style='text-align:center; color:#bdc3c7; font-size:1.0rem; margin-bottom:15px;' class='notranslate'>
                USD/KRW: <b>{d['rate']:,.1f}</b> | <span style='color:{p_color}; font-weight:bold;'>Kimchi: {d['premium']:+.2f}%</span>
            </div>
            """, unsafe_allow_html=True)

            u_html = f"<div class='header-upbit'>Upbit</div><div style='color:#5DADE2; font-size:0.7rem; text-align:center;'>▼ Sell</div>"
            for it in d['u_asks']:
                u_html += f"<div class='ob-row'><span class='price-col ask-text'>{it['ask_price']:,.0f}</span><span class='sep-col'>|</span><span class='qty-col ask-text'>{it['ask_size']:.3f}</span></div>"
            u_html += f"<div class='current-box'><div class='curr-main'>₩{d['u_p']:,.0f}</div><div class='curr-sub' style='visibility:hidden'>(Spacer)</div></div>"
            u_html += f"<div style='color:#EC7063; font-size:0.7rem; text-align:center;'>▲ Buy</div>"
            for it in d['u_bids']:
                u_html += f"<div class='ob-row'><span class='price-col bid-text'>{it['bid_price']:,.0f}</span><span class='sep-col'>|</span><span class='qty-col bid-text'>{it['bid_size']:.3f}</span></div>"

            b_html = f"<div class='header-binance'>Binance(US)</div><div style='color:#5DADE2; font-size:0.7rem; text-align:center;'>▼ Sell</div>"
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

        with portfolio_placeholder.container():
            c1, c2 = st.columns(2)
            c1.metric("가상 원화 잔고", f"{st.session_state['balance']:,.0f} 원")
            c2.metric("투자 상태", "🟢 보유 중" if st.session_state['position'] else "⚪ 대기 중")

        if st.session_state['position']:
            with pnl_placeholder.container():
                pos = st.session_state['position']
                curr_u_price = d['u_p']
                curr_b_price = d['b_p']
                curr_rate = d['rate']
                
                # 1. 차익 계산
                pnl_upbit = (curr_u_price - pos['u_entry']) * pos['qty']
                pnl_foreign = (pos['b_entry'] - curr_b_price) * pos['qty'] * curr_rate
                
                # 2. 수익률(ROI) 계산 (컬러 표시용)
                roi_upbit = (pnl_upbit / pos['invest_krw']) * 100
                roi_foreign = (pnl_foreign / pos['invest_krw']) * 100
                
                # 3. 수수료 및 최종
                est_exit_fee = (curr_u_price * pos['qty'] * FEE_UPBIT) + (curr_b_price * pos['qty'] * curr_rate * FEE_FOREIGN)
                total_fee = pos['entry_fee'] + est_exit_fee
                net_pnl = (pnl_upbit + pnl_foreign) - total_fee
                net_roi = (net_pnl / pos['invest_krw']) * 100
                
                st.markdown(f"**현재 코인:** {pos['symbol']} (Binance US)")
                
                # [복구된 기능] 3번째 인자에 delta(%)를 넣어서 초록/빨강 표시
                m1, m2, m3 = st.columns(3)
                m1.metric("업비트 차익", f"{int(pnl_upbit):,} 원", f"{roi_upbit:.2f}%")
                m2.metric("바이낸스 숏 차익", f"{int(pnl_foreign):,} 원", f"{roi_foreign:.2f}%")
                m3.metric("예상 수수료", f"-{int(total_fee):,} 원")
                
                st.divider()
                
                # 최종 결과는 metric으로 통합해서 보여줌 (delta로 수익률 표시)
                st.metric("최종 순수익 (Net Profit)", f"{int(net_pnl):,} 원", f"{net_roi:.2f}%")
                
                st.info(f"진입 김프: {pos['entry_kimp']:.2f}%  👉  현재 김프: {d['premium']:.2f}%")
    
    elif d and 'error' in d:
        with monitor_placeholder.container():
            st.warning(f"데이터 수신 대기 중... ({d['error']})")
            time.sleep(2)

    time.sleep(1)