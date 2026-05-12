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
    data = {"stats": {}, "daily_nested": {}, "portfolio_grouped": {}, "trades_grouped": {}, "monthly_grouped": {}, "error": None}
    try:
        df_daily = pd.read_csv(get_csv_url(GIDS["daily"])).fillna('')
        df_portfolio = pd.read_csv(get_csv_url(GIDS["portfolio"])).fillna('')
        df_trades = pd.read_csv(get_csv_url(GIDS["trades"])).fillna('')
        df_monthly = pd.read_csv(get_csv_url(GIDS["monthly"])).fillna('')

        # 1. คำนวณ 4 กล่องสรุป
        pnl_val = pd.to_numeric(df_daily.get('PnL ($)', 0), errors='coerce').fillna(0)
        pnl_pct = pd.to_numeric(df_daily.get('PnL (%)', 0), errors='coerce').fillna(0)
        data["stats"] = {
            "total_pnl": pnl_val.sum(),
            "avg_pnl_pct": pnl_pct.mean() * 100 if not pnl_pct.empty else 0,
            "total_stocks": df_daily['Symbol'].nunique() if 'Symbol' in df_daily else 0,
            "trend_up": df_daily[df_daily.get('Reasons', '').astype(str).str.contains('ขาขึ้น', na=False)].shape[0] if 'Reasons' in df_daily else 0
        }

        # 2. จัดกลุ่มรายวัน (เดือน -> วัน)
        if 'Date' in df_daily.columns:
            df_daily['Date'] = pd.to_datetime(df_daily['Date'])
            df_daily = df_daily.sort_values('Date', ascending=False)
            
            # สร้างคอลัมน์เดือนเพื่อจัดกลุ่ม
            df_daily['Month_Group'] = df_daily['Date'].dt.strftime('%B %Y')
            df_daily['Date_Str'] = df_daily['Date'].dt.strftime('%Y-%m-%d')

            for m, m_group in df_daily.groupby('Month_Group', sort=False):
                data["daily_nested"][m] = {}
                for d, d_group in m_group.groupby('Date_Str', sort=False):
                    data["daily_nested"][m][d] = d_group.drop(columns=['Date', 'Month_Group', 'Date_Str']).to_dict(orient='records')

        # 3. จัดกลุ่มพอร์ตลงทุน (ตาม User)
        if 'User' in df_portfolio.columns:
            cols = ['Month', 'User', 'Total Invested ($)', 'Open Positions', 'Unrealized PnL ($)', 'Net PnL ($)']
            df_p = df_portfolio[[c for c in cols if c in df_portfolio.columns]]
            for u, g in df_p.groupby('User', sort=False):
                data["portfolio_grouped"][u or 'N/A'] = g.drop(columns=['User']).to_dict(orient='records')

        # 4. ประวัติการเทรด & รายเดือน
        t_grp = 'User' if 'User' in df_trades.columns else 'Port ID'
        for k, g in df_trades.groupby(t_grp, sort=False):
            data["trades_grouped"][k or 'N/A'] = g.to_dict(orient='records')

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
        details[open] > summary svg { transform: rotate(180deg); }
        
        .table-container::-webkit-scrollbar { height: 6px; }
        .table-container::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 10px; }
    </style>
</head>
<body class="p-4 md:p-8">
    <div class="max-w-7xl mx-auto">
        
        <div class="bg-white p-6 rounded-2xl shadow-sm mb-6 flex justify-between items-center border border-slate-200">
            <h1 class="text-2xl font-bold text-slate-800 tracking-tight">🚀 Trading System Dashboard</h1>
            <div class="text-[10px] font-extrabold text-white bg-slate-800 px-3 py-1 rounded-full uppercase flex items-center shadow-sm">
                <span class="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></span> Live Sync
            </div>
        </div>

        {% if data.error %}
            <div class="bg-red-50 p-6 rounded-xl text-red-600 border border-red-100 font-medium">⚠️ Error: {{ data.error }}</div>
        {% else %}

        <div class="mb-4 ml-2">
            <h2 class="text-xs font-bold text-slate-600 flex items-center uppercase tracking-wider">
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
            <button onclick="switchTab('daily')" id="btn-daily" class="tab-btn px-6 py-4 text-xs font-bold transition tab-active uppercase">📊 สถิติรายวัน</button>
            <button onclick="switchTab('portfolio')" id="btn-portfolio" class="tab-btn px-6 py-4 text-xs font-bold transition text-slate-400 uppercase">💼 สรุปพอร์ตลงทุน</button>
            <button onclick="switchTab('trades')" id="btn-trades" class="tab-btn px-6 py-4 text-xs font-bold transition text-slate-400 uppercase">📝 ประวัติการเทรด</button>
            <button onclick="switchTab('monthly')" id="btn-monthly" class="tab-btn px-6 py-4 text-xs font-bold transition text-slate-400 uppercase">🗓️ สรุปรายเดือน</button>
        </div>

        <div class="bg-white p-6 rounded-b-2xl shadow-sm border border-slate-200 min-h-[500px]">
            
            <div id="tab-daily" class="tab-content block">
                {% for month, dates in data.daily_nested.items() %}
                <details class="mb-6 group/month">
                    <summary class="flex justify-between items-center p-5 bg-blue-600 text-white rounded-xl shadow-md cursor-pointer hover:bg-blue-700 transition">
                        <span class="text-lg font-bold">📅 ประจำเดือน: {{ month }}</span>
                        <div class="flex items-center">
                            <span class="text-xs bg-white/20 px-3 py-1 rounded-full mr-4">{{ dates|length }} วันที่มีข้อมูล</span>
                            <svg class="w-5 h-5 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                        </div>
                    </summary>
                    <div class="p-4 bg-slate-50 border border-t-0 border-blue-200 rounded-b-xl">
                        {% for date, rows in dates.items() %}
                        <details class="mb-3 group/date">
                            <summary class="flex justify-between items-center p-3 bg-white border border-slate-200 rounded-lg hover:border-blue-400 transition cursor-pointer">
                                <span class="font-bold text-slate-700 text-sm italic">วันที่: {{ date }}</span>
                                <svg class="w-4 h-4 text-slate-400 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                            </summary>
                            <div class="mt-2 border border-slate-100 rounded-lg overflow-hidden bg-white shadow-sm">
                                <div class="overflow-x-auto table-container">
                                    <table class="w-full text-[10px] text-left">
                                        <thead class="bg-slate-50 text-slate-400 border-b border-slate-100 uppercase font-bold">
                                            <tr>{% for col in rows[0].keys() %}<th class="px-4 py-3">{{ col }}</th>{% endfor %}</tr>
                                        </thead>
                                        <tbody class="divide-y divide-slate-50">
                                            {% for row in rows %}
                                            <tr class="hover:bg-blue-50/50 transition">
                                                {% for col, val in row.items() %}
                                                {% set is_money = ('PnL' in col or 'Net' in col) and val|string != '' and val != '-' %}
                                                {% set num = val|string|replace('$','')|replace('%','')|float if is_money else 0 %}
                                                <td class="px-4 py-3 whitespace-nowrap {{ 'money-pos' if is_money and num >= 0 else ('money-neg' if is_money and num < 0 else '') }}">{{ val }}</td>
                                                {% endfor %}
                                            </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </details>
                        {% endfor %}
                    </div>
                </details>
                {% endfor %}
            </div>

            {% macro simple_accordion(dict_data, label) %}
                {% for key, rows in dict_data.items() %}
                <details class="mb-4 group">
                    <summary class="flex justify-between items-center p-4 bg-slate-800 text-white rounded-xl cursor-pointer hover:bg-slate-900 shadow-sm">
                        <span class="font-bold text-sm">{{ label }}: {{ key }}</span>
                        <svg class="w-4 h-4 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                    </summary>
                    <div class="border border-t-0 border-slate-200 rounded-b-xl overflow-hidden bg-white">
                        <div class="overflow-x-auto table-container">
                            <table class="w-full text-[10px] text-left">
                                <thead class="bg-slate-50 text-slate-400 font-bold border-b border-slate-100 uppercase">
                                    <tr>{% for col in rows[0].keys() %}<th class="px-4 py-3">{{ col }}</th>{% endfor %}</tr>
                                </thead>
                                <tbody class="divide-y divide-slate-50">
                                    {% for row in rows %}
                                    <tr class="hover:bg-slate-50 transition">
                                        {% for col, val in row.items() %}
                                        {% set is_money = ('PnL' in col or 'Net' in col) and val|string != '' and val != '-' %}
                                        {% set num = val|string|replace('$','')|replace('%','')|float if is_money else 0 %}
                                        {% if val == 'BUY' %}<td class="px-4 py-3"><span class="bg-green-100 text-green-700 px-2 py-0.5 rounded text-[9px] font-bold">{{ val }}</span></td>
                                        {% elif val == 'SELL' %}<td class="px-4 py-3"><span class="bg-red-100 text-red-700 px-2 py-0.5 rounded text-[9px] font-bold">{{ val }}</span></td>
                                        {% else %}<td class="px-4 py-3 whitespace-nowrap {{ 'money-pos' if is_money and num >= 0 else ('money-neg' if is_money and num < 0 else '') }}">{{ val }}</td>
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
            {% endmacro %}

            <div id="tab-portfolio" class="tab-content hidden">{{ simple_accordion(data.portfolio_grouped, "ผู้ใช้/พอร์ต") }}</div>
            <div id="tab-trades" class="tab-content hidden">{{ simple_accordion(data.trades_grouped, "ประวัติของ") }}</div>
            <div id="tab-monthly" class="tab-content hidden">{{ simple_accordion(data.monthly_grouped, "เดือน") }}</div>

        </div>
        {% endif %}
    </div>

    <script>
        function switchTab(id) {
            document.querySelectorAll('.tab-content').forEach(c => { c.classList.add('hidden'); c.classList.remove('block'); });
            document.getElementById('tab-' + id).classList.remove('hidden');
            document.getElementById('tab-' + id).classList.add('block');
            document.querySelectorAll('.tab-btn').forEach(b => { b.classList.remove('tab-active'); b.classList.add('text-slate-400'); });
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