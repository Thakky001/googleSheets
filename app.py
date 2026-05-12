from flask import Flask, render_template_string
import pandas as pd
import os

app = Flask(__name__)

# ==========================================
# 📌 ตั้งค่า Sheet ID และ GIDs
# ==========================================
SHEET_ID = '17OFZ8V9OIU88oFrcobgs5DzVKMVbrFU_900C8YDLXS0'
GIDS = {
    "daily": "0",             
    "portfolio": "1041864931",
    "trades": "1995274580",   
    "monthly": "2060485547"
}

def get_csv_url(gid):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"

def fetch_all_data():
    data = {"stats": {}, "daily_grouped": {}, "portfolio_grouped": {}, "trades_grouped": {}, "monthly_grouped": {}, "error": None}
    try:
        # ดึงข้อมูลจาก Google Sheets
        df_daily = pd.read_csv(get_csv_url(GIDS["daily"])).fillna('')
        df_portfolio = pd.read_csv(get_csv_url(GIDS["portfolio"])).fillna('')
        df_trades = pd.read_csv(get_csv_url(GIDS["trades"])).fillna('')
        df_monthly = pd.read_csv(get_csv_url(GIDS["monthly"])).fillna('')

        # คำนวณ 4 กล่องสรุป (อิงจากแท็บสถิติรายวัน)
        pnl_val = pd.to_numeric(df_daily.get('PnL ($)', 0), errors='coerce').fillna(0)
        pnl_pct = pd.to_numeric(df_daily.get('PnL (%)', 0), errors='coerce').fillna(0)
        data["stats"] = {
            "total_pnl": pnl_val.sum(),
            "avg_pnl_pct": pnl_pct.mean() * 100 if not pnl_pct.empty else 0,
            "total_stocks": df_daily['Symbol'].nunique() if 'Symbol' in df_daily else 0,
            "trend_up": df_daily[df_daily.get('Reasons', '').astype(str).str.contains('ขาขึ้น', na=False)].shape[0] if 'Reasons' in df_daily else 0
        }

        # จัดกลุ่มข้อมูลรายวัน (แยกตามวันที่)
        if 'Date' in df_daily.columns:
            for d, g in df_daily.sort_values('Date', ascending=False).groupby('Date', sort=False):
                data["daily_grouped"][d] = g.drop(columns=['Date']).to_dict(orient='records')

        # จัดกลุ่มสรุปพอร์ต (แยกตาม User)
        if 'User' in df_portfolio.columns:
            cols = ['Month', 'User', 'Total Invested ($)', 'Open Positions', 'Unrealized PnL ($)', 'Net PnL ($)']
            df_p = df_portfolio[[c for c in cols if c in df_portfolio.columns]]
            for u, g in df_p.groupby('User', sort=False):
                data["portfolio_grouped"][u or 'N/A'] = g.drop(columns=['User']).to_dict(orient='records')

        # จัดกลุ่มประวัติการเทรด (แยกตาม User/Port ID)
        t_grp = 'User' if 'User' in df_trades.columns else 'Port ID'
        for k, g in df_trades.groupby(t_grp, sort=False):
            data["trades_grouped"][k or 'N/A'] = g.to_dict(orient='records')

        # จัดกลุ่มสรุปรายเดือน (แยกตามเดือน)
        if 'Month' in df_monthly.columns:
            for m, g in df_monthly.groupby('Month', sort=False):
                data["monthly_grouped"][m or 'N/A'] = g.to_dict(orient='records')

    except Exception as e:
        data["error"] = str(e)
    return data

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading System Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Kanit', sans-serif; background-color: #f1f5f9; }
        .tab-active { border-bottom: 4px solid #2563eb; color: #2563eb; background-color: #eff6ff; }
        .money-pos { color: #10b981; font-weight: 700; }
        .money-neg { color: #ef4444; font-weight: 700; }
        
        details summary::-webkit-details-marker { display:none; }
        details summary { list-style: none; outline: none; cursor: pointer; }
        details[open] summary { border-bottom-left-radius: 0; border-bottom-right-radius: 0; }
        details[open] svg { transform: rotate(180deg); }
        
        .table-container::-webkit-scrollbar { height: 6px; }
        .table-container::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 10px; }
    </style>
</head>
<body class="p-4 md:p-8">
    <div class="max-w-7xl mx-auto">
        
        <div class="bg-white p-6 rounded-2xl shadow-sm mb-6 flex justify-between items-center border border-slate-200">
            <h1 class="text-2xl font-bold text-slate-800 tracking-tight">🚀 Trading System Dashboard</h1>
            <div class="text-[10px] font-extrabold text-white bg-slate-800 px-3 py-1 rounded-full uppercase flex items-center">
                <span class="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></span> Live Sync
            </div>
        </div>

        {% if data.error %}
            <div class="bg-red-50 p-6 rounded-xl text-red-600 border border-red-100 font-medium">⚠️ ข้อผิดพลาด: {{ data.error }}</div>
        {% else %}

        <div class="mb-4 ml-2">
            <h2 class="text-sm font-bold text-slate-600 flex items-center uppercase tracking-wider">
                <span class="w-1.5 h-4 bg-blue-600 rounded-full mr-2"></span>
                สรุปภาพรวมข้อมูลจากสถิติหุ้น Top 5
            </h2>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                <p class="text-slate-400 text-[10px] font-bold uppercase mb-1">PnL รวม ($)</p>
                <p class="text-2xl font-bold {{ 'money-pos' if data.stats.total_pnl >= 0 else 'money-neg' }}">{{ "${:,.2f}".format(data.stats.total_pnl) }}</p>
            </div>
            <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                <p class="text-slate-400 text-[10px] font-bold uppercase mb-1">กำไรเฉลี่ย (%)</p>
                <p class="text-2xl font-bold {{ 'money-pos' if data.stats.avg_pnl_pct >= 0 else 'money-neg' }}">{{ "{:.2f}%".format(data.stats.avg_pnl_pct) }}</p>
            </div>
            <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                <p class="text-slate-400 text-[10px] font-bold uppercase mb-1">หุ้นทั้งหมด</p>
                <p class="text-2xl font-bold text-blue-600">{{ data.stats.total_stocks }} ตัว</p>
            </div>
            <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                <p class="text-slate-400 text-[10px] font-bold uppercase mb-1">Bullish Trend</p>
                <p class="text-2xl font-bold text-amber-500">{{ data.stats.trend_up }} ตัว</p>
            </div>
        </div>

        <div class="flex bg-white rounded-t-2xl shadow-sm border border-slate-200 border-b-0 overflow-x-auto">
            <button onclick="switchTab('daily')" id="btn-daily" class="tab-btn px-6 py-4 text-xs font-bold transition tab-active uppercase tracking-wider">📊 สถิติรายวัน</button>
            <button onclick="switchTab('portfolio')" id="btn-portfolio" class="tab-btn px-6 py-4 text-xs font-bold transition text-slate-400 uppercase tracking-wider">💼 สรุปพอร์ตลงทุน</button>
            <button onclick="switchTab('trades')" id="btn-trades" class="tab-btn px-6 py-4 text-xs font-bold transition text-slate-400 uppercase tracking-wider">📝 ประวัติการเทรด</button>
            <button onclick="switchTab('monthly')" id="btn-monthly" class="tab-btn px-6 py-4 text-xs font-bold transition text-slate-400 uppercase tracking-wider">🗓️ สรุปรายเดือน</button>
        </div>

        <div class="bg-white p-6 rounded-b-2xl shadow-sm border border-slate-200 min-h-[500px]">
            
            {% macro render_accordion(grouped_dict, label) %}
                {% if grouped_dict %}
                    {% for key, rows in grouped_dict.items() %}
                    <details class="group mb-4">
                        <summary class="flex justify-between items-center p-4 bg-slate-50 border border-slate-200 rounded-xl hover:bg-slate-100 transition-all shadow-sm">
                            <div class="flex items-center">
                                <span class="w-8 h-8 flex items-center justify-center bg-white rounded-lg border border-slate-200 mr-3 text-slate-400 transition-transform duration-200">
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 transition-transform duration-200" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
                                </span>
                                <span class="font-bold text-slate-700">{{ label }}: <span class="text-blue-600 ml-1">{{ key }}</span></span>
                            </div>
                            <span class="text-[10px] font-bold text-slate-400 bg-white border border-slate-200 px-2 py-1 rounded uppercase">{{ rows|length }} รายการ</span>
                        </summary>
                        
                        <div class="border border-t-0 border-slate-200 rounded-b-xl overflow-hidden bg-white">
                            <div class="overflow-x-auto table-container">
                                <table class="w-full text-[11px] text-left">
                                    <thead class="bg-slate-50 text-slate-400 font-bold border-b border-slate-100 uppercase">
                                        <tr>
                                            {% for col in rows[0].keys() %}<th class="px-4 py-3 whitespace-nowrap">{{ col }}</th>{% endfor %}
                                        </tr>
                                    </thead>
                                    <tbody class="divide-y divide-slate-50 text-slate-600">
                                        {% for row in rows %}
                                        <tr class="hover:bg-blue-50/50 transition">
                                            {% for col, val in row.items() %}
                                                {% set is_money = ('PnL' in col or 'Net' in col) and val|string != '' and val != '-' %}
                                                {% set num = val|string|replace('$','')|replace('%','')|float if is_money else 0 %}
                                                {% if val == 'BUY' %}
                                                    <td class="px-4 py-3"><span class="bg-green-100 text-green-700 px-2 py-1 rounded text-[10px] font-bold">{{ val }}</span></td>
                                                {% elif val == 'SELL' %}
                                                    <td class="px-4 py-3"><span class="bg-red-100 text-red-700 px-2 py-1 rounded text-[10px] font-bold">{{ val }}</span></td>
                                                {% else %}
                                                    <td class="px-4 py-3 whitespace-nowrap {{ 'money-pos' if is_money and num >= 0 else ('money-neg' if is_money and num < 0 else '') }}">{{ val }}</td>
                                                {% endif %}
                                            {% endfor %}
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </details>
                    {% endfor %}
                {% else %}
                    <div class="text-center py-10 text-slate-400 font-medium italic">ไม่พบข้อมูลในส่วนนี้</div>
                {% endif %}
            {% endmacro %}

            <div id="tab-daily" class="tab-content block">{{ render_accordion(data.daily_grouped, "วันที่") }}</div>
            <div id="tab-portfolio" class="tab-content hidden">{{ render_accordion(data.portfolio_grouped, "พอร์ตลงทุน") }}</div>
            <div id="tab-trades" class="tab-content hidden">{{ render_accordion(data.trades_grouped, "ประวัติของ") }}</div>
            <div id="tab-monthly" class="tab-content hidden">{{ render_accordion(data.monthly_grouped, "สถิติประจำเดือน") }}</div>

        </div>
        {% endif %}
    </div>

    <script>
        function switchTab(id) {
            document.querySelectorAll('.tab-content').forEach(c => {
                c.classList.add('hidden');
                c.classList.remove('block');
            });
            document.getElementById('tab-' + id).classList.remove('hidden');
            document.getElementById('tab-' + id).classList.add('block');
            
            document.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.remove('tab-active', 'text-blue-600');
                b.classList.add('text-slate-400');
            });
            document.getElementById('btn-' + id).classList.add('tab-active');
            document.getElementById('btn-' + id).classList.remove('text-slate-400');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    data = fetch_all_data()
    return render_template_string(HTML_TEMPLATE, data=data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)