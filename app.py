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
    page_title="Crypto Master Sim (Final v2)",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# [2] 설정
# ==========================================
FEE_UPBIT = 0.0005 
FEE_FOREIGN = 0.001 
HISTORY_FILE = "trade_history.csv" 

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
# [4] 스타일
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #1e272e; }
    .notranslate { transform: translateZ(0); -webkit-font-smoothing: antialiased; }
    .block-container { padding-top: 4rem; max_width: 100%; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #1e272e; }
    .stTabs [data-baseweb="tab"] { background-color: #2d3436; border-radius: 5px; color: white; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #00d2d3; color: black; font-weight: bold; }
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

if 'balance' not in st.session_state:
    st.session_state['balance'] = 10000000 
if 'position' not in st.session_state:
    st.session_state['position'] = None 
if 'last_log_time' not in st.session_state:
    st.session_state['last_log_time'] = 0

# ==========================================
# [6] 데이터 수집
# ==========================================
def get_data(symbol):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        try:
            rate_res = requests.get("https://open.er-api.com/v6/latest/USD", headers=headers, timeout=2).json()
            rate = rate_res['rates']['KRW']
        except:
            rate = 1450.0

        u_url = f"https://api.upbit.com/v1/ticker?markets=KRW-{symbol}"
        u_res = requests.get(u_url, headers=headers, timeout=2)
        if u_res.status_code != 200: return {"error": f"Upbit {u_res.status_code}"}
        u_ticker = u_res.json()[0]
        
        u_ob_url = f"https://api.upbit.com/v1/orderbook?markets=KRW-{symbol}"
        u_ob = requests.get(u_ob_url, headers=headers, timeout=2).json()[0]['orderbook_units'][:5]
        
        b_ticker_url = f"https://api.binance.us/api/v3/ticker/price?symbol={symbol}USDT"
        b_res = requests.get(b_ticker_url, headers=headers, timeout=2)
        if b_res.status_code != 200: return {"error": f"Binance US {b_res.status_code}"}
        b_ticker = b_res.json()
        
        b_ob_url = f"https://api.binance.us/api/v3/depth?symbol={symbol}USDT&limit=5"
        b_ob = requests.get(b_ob_url, headers=headers, timeout=2).json()

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
# [7] 유틸리티 함수 (여기서 정의)
# ==========================================

def apply_color(val):
    val_str = str(val)
    if '🔺' in val_str: 
        return 'color: #ff4b4b; font-weight: bold;' 
    elif '🔻' in val_str: 
        return 'color: #1e90ff; font-weight: bold;' 
    return 'color: #bdc3c7;'

def format_with_change(val, change, is_currency=True, currency_symbol=""):
    if pd.isna(change) or change == 0:
        chg_str = "-"
    elif change > 0:
        chg_str = f"🔺{change:,.0f}" if is_currency else f"🔺{change:,.2f}"
    else:
        chg_str = f"🔻{abs(change):,.0f}" if is_currency else f"🔻{abs(change):,.2f}"
    
    val_str = f"{val:,.0f}" if is_currency else f"{val:,.2f}"
    return f"{currency_symbol}{val_str} ({chg_str})"

def process_log_for_display(df):
    mapping = {
        'Time': '시간', 'Upbit_Price': '업비트(KRW)', 'Binance_Price': '바이낸스($)',
        'Premium(%)': '김프(%)', 'Net_PNL': '순수익(원)', 'ROI(%)': '수익률(%)', 'Status': '상태'
    }
    df = df.rename(columns=mapping)
    
    required = ['시간', '업비트(KRW)', '바이낸스($)', '김프(%)', '순수익(원)', '수익률(%)']
    if not all(col in df.columns for col in required):
        return df 

    df['업_변동'] = df['업비트(KRW)'].diff().fillna(0)
    df['바_변동'] = df['바이낸스($)'].diff().fillna(0)
    df['수익_변동'] = df['순수익(원)'].diff().fillna(0)

    display_df = pd.DataFrame()
    display_df['시간'] = df['시간']
    display_df['업비트 (변동)'] = [format_with_change(v, d, True, "₩") for v, d in zip(df['업비트(KRW)'], df['업_변동'])]
    display_df['바이낸스 (변동)'] = [format_with_change(v, d, True, "$") for v, d in zip(df['바이낸스($)'], df['바_변동'])]
    display_df['김프(%)'] = df['김프(%)']
    display_df['순수익 (변동)'] = [format_with_change(v, d, True, "₩") for v, d in zip(df['순수익(원)'], df['수익_변동'])]
    display_df['수익률(%)'] = df['수익률(%)'].apply(lambda x: f"{x:.2f}%")
    
    return display_df

# [수정된 함수] 요약본 저장 시 모든 필드 포함
def save_trade_summary(trade_data):
    # 이제 모든 컬럼을 한글 키로 매핑해서 저장
    kor_data = {
        "시간": trade_data.get("Time"),
        "코인": trade_data.get("Coin"),
        "수량": trade_data.get("Qty"),
        "업진입": trade_data.get("U.Entry"),
        "업청산": trade_data.get("U.Exit"),
        "바진입": trade_data.get("B.Entry"),
        "바청산": trade_data.get("B.Exit"),
        "수수료": trade_data.get("Fees"),
        "순수익(원)": trade_data.get("Net PNL"),
        "수익률(%)": trade_data.get("ROI"),
        "로그파일": trade_data.get("Log File")
    }
    df = pd.DataFrame([kor_data])
    if not os.path.exists(HISTORY_FILE):
        df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else:
        # 기존 파일과 컬럼 개수가 안 맞아도 일단 append (header=False)
        # 하지만 사용자가 '초기화'를 한번 해주는게 가장 깔끔함
        df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

def load_trade_summary():
    if os.path.exists(HISTORY_FILE):
        try: return pd.read_csv(HISTORY_FILE)
        except: return pd.DataFrame()
    return pd.DataFrame()

def save_position_log(filename, log_data):
    df = pd.DataFrame([log_data])
    if not os.path.exists(filename):
        df.to_csv(filename, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(filename, mode='a', header=False, index=False, encoding='utf-8-sig')

def get_log_files():
    files = [f for f in os.listdir() if f.startswith('log_') and f.endswith('.csv')]
    files.sort(reverse=True)
    return files

# ==========================================
# [8] UI 구성
# ==========================================
col_dum1, col_sel, col_dum2 = st.columns([1, 2, 1])
with col_sel:
    sel_coin = st.selectbox("코인 선택", list(COIN_MENU.keys()), label_visibility="collapsed")
sym = COIN_MENU[sel_coin]

st.markdown(f"<div class='main-title notranslate'>Target: {sel_coin}</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 실시간 시세 (Monitor)", "🎮 모의 투자 (Simulation)", "📂 로그 파일 분석 (Viewer)"])

with tab1:
    monitor_placeholder = st.empty()

with tab2:
    st.markdown("### 💼 투자 현황 (Portfolio Status)")
    st.markdown(f"<div class='fee-info'>※ 레버리지: 10배 | 수수료: 업비트 {FEE_UPBIT*100}% | 바이낸스 {FEE_FOREIGN*100}%</div>", unsafe_allow_html=True)
    
    portfolio_placeholder = st.empty() 
    st.divider()
    
    st.markdown("#### 📝 실시간 1분 기록 (Real-time Log)")
    live_log_placeholder = st.empty()

    sim_controls = st.container()
    
    with sim_controls:
        # A. 진입
        if st.session_state['position'] is None:
            invest_amount = st.number_input("투자할 총 금액 (KRW)", min_value=100000, max_value=int(st.session_state['balance']), value=1000000, step=100000, key="invest_input")
            upbit_alloc = invest_amount * (10 / 11)
            
            if st.button(f"🚀 10배 풀시드 진입 (기록 시작)", key="btn_buy"):
                data = get_data(sym)
                if data and 'error' not in data:
                    u_price = data['u_p']
                    b_price = data['b_p']
                    rate = data['rate']
                    
                    btc_qty = upbit_alloc / u_price
                    entry_fee_u = upbit_alloc * FEE_UPBIT
                    entry_fee_b = b_price * btc_qty * rate * FEE_FOREIGN
                    
                    log_filename = f"log_{sym}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    
                    st.session_state['position'] = {
                        'symbol': sym,
                        'entry_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'invest_krw': invest_amount,
                        'u_entry': u_price,
                        'b_entry': b_price,
                        'qty': btc_qty,
                        'rate_entry': rate,
                        'entry_kimp': data['premium'],
                        'entry_fee_u': entry_fee_u,
                        'entry_fee_b': entry_fee_b,
                        'log_filename': log_filename,
                        'log_count': 0
                    }
                    st.session_state['balance'] -= invest_amount
                    st.session_state['last_log_time'] = time.time()
                    
                    st.success(f"포지션 진입! '{log_filename}' 기록 중...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("데이터 수신 오류!")

        # B. 청산
        else:
            pnl_placeholder = st.empty()
            
            if st.button("💰 포지션 종료 (저장)", key="btn_sell"):
                data = get_data(sym)
                if data and 'error' not in data:
                    pos = st.session_state['position']
                    curr_u_price = data['u_p']
                    curr_b_price = data['b_p']
                    curr_rate = data['rate']
                    
                    gross_u = (curr_u_price - pos['u_entry']) * pos['qty']
                    gross_b = (pos['b_entry'] - curr_b_price) * pos['qty'] * curr_rate
                    
                    exit_fee_u = curr_u_price * pos['qty'] * FEE_UPBIT
                    exit_fee_b = curr_b_price * pos['qty'] * curr_rate * FEE_FOREIGN
                    total_fee = pos['entry_fee_u'] + pos['entry_fee_b'] + exit_fee_u + exit_fee_b
                    
                    net_pnl = (gross_u + gross_b) - total_fee
                    roi = (net_pnl / pos['invest_krw']) * 100
                    
                    st.session_state['balance'] += (pos['invest_krw'] + net_pnl)
                    
                    # [수정] 모든 필드를 다 넘겨줍니다.
                    save_trade_summary({
                        "Time": datetime.now().strftime("%m-%d %H:%M"),
                        "Coin": pos['symbol'],
                        "Qty": f"{pos['qty']:.6f}",
                        "U.Entry": int(pos['u_entry']),
                        "U.Exit": int(curr_u_price),
                        "B.Entry": f"${pos['b_entry']:.2f}",
                        "B.Exit": f"${curr_b_price:.2f}",
                        "Fees": int(total_fee),
                        "Net PNL": int(net_pnl),
                        "ROI": f"{roi:.2f}%",
                        "Log File": pos['log_filename']
                    })
                    
                    # 종료 로그
                    save_position_log(pos['log_filename'], {
                        "시간": datetime.now().strftime("%H:%M:%S"),
                        "업비트(KRW)": curr_u_price,
                        "바이낸스($)": curr_b_price,
                        "김프(%)": data['premium'],
                        "순수익(원)": int(net_pnl),
                        "수익률(%)": round(roi, 2),
                        "상태": "종료"
                    })
                    
                    st.session_state['position'] = None
                    st.success(f"거래 종료! 로그 파일: {pos['log_filename']}")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("데이터 수신 오류!")

    st.markdown("### 📜 전체 매매 요약 (Summary)")
    
    # [NEW] 기록 초기화 버튼 (꼬인 파일 삭제용)
    if st.button("🗑️ 기록 초기화 (파일 꼬였을 때 누르세요)"):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
            st.success("기록 파일이 초기화되었습니다. 새로고침 됩니다.")
            time.sleep(1)
            st.rerun()

    history_df = load_trade_summary()
    if not history_df.empty:
        st.dataframe(history_df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("거래 기록 없음")

# --- [Tab 3] 로그 파일 뷰어 ---
with tab3:
    st.markdown("### 📂 개별 포지션 상세 분석 (Log Viewer)")
    
    log_files = get_log_files()
    
    if log_files:
        selected_file = st.selectbox("분석할 로그 파일을 선택하세요:", log_files)
        
        if selected_file:
            st.divider()
            try:
                df_log = pd.read_csv(selected_file)
                
                if not df_log.empty:
                    # 함수 호출
                    df_display = process_log_for_display(df_log)
                    
                    if '순수익(원)' in df_log.columns or 'Net_PNL' in df_log.columns:
                        # 호환성 체크
                        pnl_col = '순수익(원)' if '순수익(원)' in df_log.columns else 'Net_PNL'
                        
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.line_chart(df_log, x='시간' if '시간' in df_log.columns else 'Time', y=pnl_col, height=250)
                        with c2:
                            last_row = df_log.iloc[-1]
                            # 안전하게 값 가져오기
                            last_pnl = last_row.get('순수익(원)') or last_row.get('Net_PNL')
                            last_roi = last_row.get('수익률(%)') or last_row.get('ROI(%)')
                            
                            st.metric("최종 순수익", f"{int(last_pnl):,} 원")
                            st.metric("최종 수익률", f"{last_roi}%")

                    st.markdown("#### 📋 1분 단위 상세 변동 내역")
                    st.dataframe(
                        df_display.sort_index(ascending=False).style.map(apply_color, subset=['업비트 (변동)', '바이낸스 (변동)', '순수익 (변동)']),
                        use_container_width=True,
                        height=500
                    )
                    
                    st.download_button(
                        label="💾 엑셀용 CSV 다운로드",
                        data=df_log.to_csv(index=False).encode('utf-8-sig'),
                        file_name=selected_file,
                        mime='text/csv',
                    )
                else:
                    st.warning("파일이 비어있습니다.")
            except Exception as e:
                st.error(f"파일 오류: {e}")
    else:
        st.info("저장된 로그 파일이 없습니다.")


# ==========================================
# [9] 루프
# ==========================================
while True:
    d = get_data(sym)
    
    if d and 'error' not in d:
        p_color = "red" if d['premium'] >= 0 else "blue"
        p_delta = "normal" if d['premium'] >= 0 else "inverse"

        if st.session_state['position'] is not None:
            current_ts = time.time()
            if current_ts - st.session_state['last_log_time'] >= 60:
                pos = st.session_state['position']
                
                gross_u = (d['u_p'] - pos['u_entry']) * pos['qty']
                gross_b = (pos['b_entry'] - d['b_p']) * pos['qty'] * d['rate']
                est_fee = (d['u_p'] * pos['qty'] * FEE_UPBIT) + (d['b_p'] * pos['qty'] * d['rate'] * FEE_FOREIGN)
                cur_net_pnl = (gross_u + gross_b) - (pos['entry_fee_u'] + pos['entry_fee_b'] + est_fee)
                cur_roi = (cur_net_pnl / pos['invest_krw']) * 100
                
                save_position_log(pos['log_filename'], {
                    "시간": datetime.now().strftime("%H:%M:%S"),
                    "업비트(KRW)": d['u_p'],
                    "바이낸스($)": d['b_p'],
                    "김프(%)": round(d['premium'], 2),
                    "순수익(원)": int(cur_net_pnl),
                    "수익률(%)": round(cur_roi, 2),
                    "상태": "보유중"
                })
                
                st.session_state['position']['log_count'] += 1
                st.session_state['last_log_time'] = current_ts

        # UI 업데이트
        with monitor_placeholder.container():
            st.markdown(f"""
            <div style='text-align:center; color:#bdc3c7; font-size:1.0rem; margin-bottom:15px;' class='notranslate'>
                USD/KRW: <b>{d['rate']:,.1f}</b> | <span style='color:{p_color}; font-weight:bold;'>Kimchi: {d['premium']:+.2f}%</span>
            </div>
            """, unsafe_allow_html=True)
            
            u_html = f"<div class='header-upbit'>Upbit</div><div style='color:#5DADE2; font-size:0.7rem; text-align:center;'>▼ Sell</div>"
            for it in d['u_asks']:
                u_html += f"<div class='ob-row'><span class='price-col ask-text'>{it['ask_price']:,.0f}</span><span class='sep-col'>|</span><span class='qty-col ask-text'>{it['ask_size']:.3f}</span></div>"
            u_html += f"<div class='current-box'><div class='curr-main'>₩{d['u_p']:,.0f}</div></div>"
            u_html += f"<div style='color:#EC7063; font-size:0.7rem; text-align:center;'>▲ Buy</div>"
            for it in d['u_bids']:
                u_html += f"<div class='ob-row'><span class='price-col bid-text'>{it['bid_price']:,.0f}</span><span class='sep-col'>|</span><span class='qty-col bid-text'>{it['bid_size']:.3f}</span></div>"

            b_html = f"<div class='header-binance'>Binance(US)</div><div style='color:#5DADE2; font-size:0.7rem; text-align:center;'>▼ Sell</div>"
            for it in d['b_asks']:
                b_html += f"<div class='ob-row'><span class='price-col ask-text'>{float(it[0]):,.2f}</span><span class='sep-col'>|</span><span class='qty-col ask-text'>{float(it[1]):.3f}</span></div>"
            b_html += f"<div class='current-box'><div class='curr-main'>${d['b_p']:,.2f}</div></div>"
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
            pos = st.session_state['position']
            
            # [실시간 1분 기록 테이블]
            with live_log_placeholder.container():
                if os.path.exists(pos['log_filename']):
                    try:
                        df_log = pd.read_csv(pos['log_filename'])
                        if not df_log.empty:
                            df_display = process_log_for_display(df_log)
                            st.caption(f"📡 기록 중: {pos['log_filename']} (총 {len(df_log)}분)")
                            st.dataframe(
                                df_display.tail(5).sort_index(ascending=False).style.map(apply_color, subset=['업비트 (변동)', '바이낸스 (변동)', '순수익 (변동)']),
                                use_container_width=True
                            )
                    except: pass

            with pnl_placeholder.container():
                gross_u = (d['u_p'] - pos['u_entry']) * pos['qty']
                gross_b = (pos['b_entry'] - d['b_p']) * pos['qty'] * d['rate']
                est_fee = (d['u_p'] * pos['qty'] * FEE_UPBIT) + (d['b_p'] * pos['qty'] * d['rate'] * FEE_FOREIGN)
                total_fee = pos['entry_fee_u'] + pos['entry_fee_b'] + est_fee
                net_pnl = (gross_u + gross_b) - total_fee
                net_roi = (net_pnl / pos['invest_krw']) * 100
                
                roi_u = (gross_u / pos['invest_krw']) * 100
                roi_b = (gross_b / pos['invest_krw']) * 100
                
                st.markdown(f"**현재 포지션:** {pos['symbol']}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("업비트 수익", f"{int(gross_u):,} 원", f"{roi_u:.2f}%")
                m2.metric("업비트 수수료", f"-{int(pos['entry_fee_u'] + est_fee/2):,} 원")
                m3.metric("바이낸스 수익", f"{int(gross_b):,} 원", f"{roi_b:.2f}%")
                m4.metric("바이낸스 수수료", f"-{int(pos['entry_fee_b'] + est_fee/2):,} 원")
                
                st.divider()
                st.metric("최종 순수익 (Net Profit)", f"{int(net_pnl):,} 원", f"{net_roi:.2f}%")
                st.info(f"진입 김프: {pos['entry_kimp']:.2f}%  👉  현재 김프: {d['premium']:.2f}%")
    
    elif d and 'error' in d:
        with monitor_placeholder.container():
            st.warning(f"데이터 수신 대기 중... ({d['error']})")
            time.sleep(2)
            
    time.sleep(1)