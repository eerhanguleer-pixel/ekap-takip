import os, csv, io, json, sqlite3, threading, time
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, session, redirect, render_template_string
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'change-this-secret-before-production')
DB_PATH = os.environ.get('DB_PATH', '/tmp/ekap_takip.db')
CITIES = ['Çorum','Kırıkkale','Samsun','Çankırı','Amasya','Tokat','Kastamonu']
CATEGORIES = ['Bakliyat','Kuru gıda','Donuk ürünler']


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE IF NOT EXISTS tenders (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, city TEXT DEFAULT '', category TEXT DEFAULT '',
      deadline TEXT DEFAULT '', url TEXT DEFAULT '', source TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      notified INTEGER DEFAULT 0)''')
    conn.commit()
    return conn


def logged_in():
    return session.get('logged_in') is True


def protected(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not logged_in():
            return jsonify({'ok': False, 'error': 'Önce giriş yapın.'}), 401
        return fn(*args, **kwargs)
    return wrapper


def send_telegram(text):
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat_id:
        return False, 'Render ortam değişkenlerinde TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID tanımlı değil.'
    try:
        r = requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
                          json={'chat_id': chat_id, 'text': text, 'disable_web_page_preview': True}, timeout=20)
        data = r.json()
        if r.ok and data.get('ok'):
            return True, 'Telegram mesajı gönderildi.'
        return False, data.get('description', 'Telegram mesajı gönderilemedi.')
    except Exception as e:
        return False, 'Telegram bağlantı hatası: ' + str(e)[:180]


LOGIN_HTML = '''<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EKAP Takip Girişi</title><style>body{font-family:system-ui;background:#f2f5f9;display:grid;place-items:center;min-height:100vh;margin:0;color:#182230}.card{background:white;padding:26px;border-radius:18px;width:min(88%,390px);box-shadow:0 8px 28px #0001}input,button{font:inherit;padding:13px;border-radius:10px;width:100%;box-sizing:border-box;margin-top:10px}input{border:1px solid #ccd4df}button{background:#155eef;color:white;border:0;font-weight:700}.err{color:#b42318}</style><div class="card"><h2>EKAP İhale Takip</h2><p>Yönetim ekranına girmek için uygulama şifresini yaz.</p>{% if error %}<p class="err">{{error}}</p>{% endif %}<form method="post"><input name="password" type="password" placeholder="Uygulama şifresi" required><button>Giriş yap</button></form><small>Şifre Render ayarlarında APP_PASSWORD olarak belirlenir.</small></div></html>'''

HTML = r'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#102a43"><title>EKAP İhale Takip</title><style>
:root{--navy:#102a43;--blue:#155eef;--bg:#f3f6fb;--line:#e1e7ef;--muted:#637083}*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#172b4d}.top{background:var(--navy);color:white;padding:22px 18px 26px}.top h1{font-size:23px;margin:0 0 5px}.top p{margin:0;color:#cbd5e1;font-size:13px}.wrap{max-width:900px;margin:auto;padding:14px}.status{background:white;border:1px solid var(--line);border-radius:14px;padding:14px;margin-top:-12px;box-shadow:0 5px 18px #102a430a}.pill{display:inline-block;padding:5px 9px;border-radius:999px;font-size:12px;background:#fff0d5;color:#8b4d00;font-weight:700}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:14px 0}.card{background:white;border:1px solid var(--line);border-radius:14px;padding:15px}.card h3{font-size:16px;margin:0 0 10px}.muted{color:var(--muted);font-size:13px;line-height:1.5}.btn{border:0;background:var(--blue);color:white;border-radius:10px;padding:12px 14px;font:inherit;font-weight:650;width:100%;cursor:pointer}.btn.secondary{background:#eaf0ff;color:#1746a2}.btn.dark{background:#344054}.field{width:100%;padding:11px;border:1px solid #cdd5df;border-radius:9px;font:inherit;margin:5px 0 10px;background:white}label{font-size:13px;font-weight:650}.checks{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:10px 0}.checks label{display:flex;gap:8px;align-items:center;font-weight:500;background:#f7f9fc;border:1px solid var(--line);border-radius:9px;padding:9px}.checks input{width:auto;margin:0}.tender{border-top:1px solid var(--line);padding:12px 0}.tender:first-child{border-top:0}.tender h4{margin:0 0 5px;font-size:15px}.meta{font-size:12px;color:var(--muted);margin-bottom:7px}.tender a{color:var(--blue);font-size:13px}.notice{font-size:13px;background:#fff7e6;border:1px solid #f7d79a;color:#7a4a00;padding:11px;border-radius:10px;line-height:1.5}.good{background:#e8f7ed;color:#17663a;border-color:#b9e5c8}.bad{background:#fff0f0;color:#9e2020;border-color:#f4c2c2}.hidden{display:none}.bar{display:flex;gap:8px}.bar>*{flex:1}.small{font-size:12px;color:var(--muted)}@media(max-width:520px){.grid{grid-template-columns:1fr}.checks{grid-template-columns:1fr}.bar{flex-direction:column}}
</style></head><body><header class="top"><h1>EKAP İhale Takip</h1><p>7 il · Bakliyat · Kuru gıda · Donuk ürünler</p></header><main class="wrap"><section class="status"><div class="bar" style="align-items:center"><div><strong>Telegram bağlantısı</strong><div class="muted" id="tgstatus">Durum kontrol ediliyor…</div></div><span class="pill" id="pill">Kontrol ediliyor</span></div><div id="msg" class="notice hidden" style="margin-top:12px"></div></section>
<div class="grid"><section class="card"><h3>1. Telegram'ı test et</h3><p class="muted">Bot token'ı ve Chat ID sunucuda güvenli ayarlarda tanımlıysa test mesajı gönderir.</p><button class="btn" onclick="testTelegram()">Test mesajı gönder</button></section><section class="card"><h3>2. İhale dosyası yükle</h3><p class="muted">EKAP'tan indirdiğin CSV dosyasını yükleyerek kayıtları filtreleyebilirsin. Gerekli sütunlar: title, city, category, deadline, url.</p><input class="field" id="file" type="file" accept=".csv,text/csv"><button class="btn secondary" onclick="uploadCsv()">CSV dosyasını içe aktar</button></section></div>
<section class="card"><h3>Filtreler</h3><p class="muted">İlgilendiğin illeri ve ürün gruplarını seç.</p><div class="checks" id="cities"></div><div class="checks" id="cats"></div><label for="interval">Kontrol aralığı (dakika)</label><select id="interval" class="field"><option>30</option><option>60</option><option>120</option></select><button class="btn secondary" onclick="saveFilters()">Filtreleri kaydet</button><p class="small">Filtre ayarları bu telefondaki tarayıcıda saklanır.</p></section>
<section class="card" style="margin-top:12px"><div class="bar" style="align-items:center"><h3 style="margin:0;flex:1">İhale kayıtları</h3><button class="btn secondary" style="width:auto" onclick="loadTenders()">Yenile</button></div><p class="muted" id="count">Yükleniyor…</p><div id="tenders"></div></section>
<section class="card" style="margin-top:12px"><h3>Gerçek veri ve otomatik takip hakkında</h3><p class="muted">Bu sürüm Telegram bağlantısını test eder ve yüklediğin CSV kayıtlarını filtreler. EKAP'a otomatik erişim henüz bağlı değil; resmi/veri kullanımına izin verilen bir kaynak tanımlanmadan canlı ihale çektiğini varsaymaz. Render ücretsiz web servisleri 15 dakika istek almazsa uykuya geçebilir; bu nedenle 30 dakikalık arka plan kontrolü ücretsiz planda kesintisiz garanti edilemez.</p><button class="btn dark" onclick="logout()">Güvenli çıkış</button></section></main>
<script>
const CITIES=['Çorum','Kırıkkale','Samsun','Çankırı','Amasya','Tokat','Kastamonu'];const CATS=['Bakliyat','Kuru gıda','Donuk ürünler'];
function checked(key,all){try{let x=JSON.parse(localStorage.getItem(key));return Array.isArray(x)?x:all}catch(e){return all}}
function drawChecks(id,items,key){let selected=checked(key,items);document.getElementById(id).innerHTML=items.map(x=>`<label><input type="checkbox" value="${x}" ${selected.includes(x)?'checked':''}>${x}</label>`).join('')}
drawChecks('cities',CITIES,'ekap_cities');drawChecks('cats',CATS,'ekap_cats');document.getElementById('interval').value=localStorage.getItem('ekap_interval')||'30';
function filters(){return {cities:[...document.querySelectorAll('#cities input:checked')].map(x=>x.value),cats:[...document.querySelectorAll('#cats input:checked')].map(x=>x.value)}}
function saveFilters(){let f=filters();localStorage.setItem('ekap_cities',JSON.stringify(f.cities));localStorage.setItem('ekap_cats',JSON.stringify(f.cats));localStorage.setItem('ekap_interval',document.getElementById('interval').value);loadTenders();notice('Filtreler bu telefona kaydedildi.','good')}
function notice(t,kind=''){let n=document.getElementById('msg');n.className='notice '+kind;n.textContent=t;n.classList.remove('hidden')}
async function status(){try{let r=await fetch('/api/status');let d=await r.json();document.getElementById('tgstatus').textContent=d.telegram_configured?'Bot ayarları sunucuda tanımlı.':'Telegram token/Chat ID sunucu ayarlarında eksik.';document.getElementById('pill').textContent=d.telegram_configured?'Ayarlandı':'Kurulum gerekli';document.getElementById('pill').style.background=d.telegram_configured?'#d9fbe5':'#fff0d5';}catch(e){document.getElementById('tgstatus').textContent='Sunucuya ulaşılamadı.'}}
async function testTelegram(){try{let r=await fetch('/api/test-telegram',{method:'POST'});let d=await r.json();notice(d.message||d.error,d.ok?'good':'bad')}catch(e){notice('Sunucuya bağlanılamadı.','bad')}}
async function uploadCsv(){let f=document.getElementById('file').files[0];if(!f){notice('Önce CSV dosyası seç.','bad');return}let fd=new FormData();fd.append('file',f);try{let r=await fetch('/api/import',{method:'POST',body:fd});let d=await r.json();notice(d.message||d.error,d.ok?'good':'bad');loadTenders()}catch(e){notice('Dosya yüklenemedi.','bad')}}
async function loadTenders(){try{let r=await fetch('/api/tenders');let d=await r.json();let f=filters();let rows=d.tenders.filter(t=>(!f.cities.length||f.cities.includes(t.city))&&(!f.cats.length||f.cats.includes(t.category)));document.getElementById('count').textContent=`${rows.length} kayıt gösteriliyor (${d.tenders.length} toplam).`;document.getElementById('tenders').innerHTML=rows.length?rows.map(t=>`<div class="tender"><h4>${esc(t.title)}</h4><div class="meta">${esc(t.city||'İl belirtilmemiş')} · ${esc(t.category||'Kategori belirtilmemiş')} · Son tarih: ${esc(t.deadline||'Belirtilmemiş')}</div>${t.url?`<a href="${esc(t.url)}" target="_blank" rel="noopener">İhale bağlantısını aç</a>`:''}</div>`).join(''):'<p class="muted">Bu filtrelerle kayıt yok. EKAP CSV dosyası yükleyebilirsin.</p>'}catch(e){document.getElementById('count').textContent='Kayıtlar yüklenemedi.'}}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function logout(){await fetch('/logout',{method:'POST'});location.href='/'}status();loadTenders();
</script></body></html>'''

@app.route('/', methods=['GET','POST'])
def home():
    if not os.environ.get('APP_PASSWORD'):
        return 'Kurulum eksik: Render ortam değişkenlerinde APP_PASSWORD belirleyin.', 503
    if request.method == 'POST':
        if request.form.get('password','') == os.environ.get('APP_PASSWORD'):
            session['logged_in'] = True
            return redirect('/')
        return render_template_string(LOGIN_HTML, error='Şifre yanlış.'), 401
    if not logged_in():
        return render_template_string(LOGIN_HTML, error='')
    return HTML

@app.post('/logout')
def logout():
    session.clear()
    return jsonify({'ok': True})

@app.get('/api/status')
@protected
def api_status():
    return jsonify({'ok': True, 'telegram_configured': bool(os.environ.get('TELEGRAM_BOT_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID')), 'ekap_live_feed_configured': bool(os.environ.get('EKAP_FEED_URL'))})

@app.post('/api/test-telegram')
@protected
def api_test():
    ok, msg = send_telegram('✅ EKAP İhale Takip test mesajı\nTelegram bağlantısı çalışıyor. Henüz canlı EKAP takibi etkin değil.')
    return jsonify({'ok': ok, 'message': msg}), (200 if ok else 400)

@app.get('/api/tenders')
@protected
def api_tenders():
    conn = db()
    rows = [dict(r) for r in conn.execute('SELECT id,title,city,category,deadline,url,source,created_at FROM tenders ORDER BY created_at DESC').fetchall()]
    conn.close()
    return jsonify({'ok': True, 'tenders': rows})

@app.post('/api/import')
@protected
def api_import():
    f = request.files.get('file')
    if not f:
        return jsonify({'ok': False, 'error': 'CSV dosyası seçilmedi.'}), 400
    try:
        raw = f.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(raw))
        if not reader.fieldnames:
            return jsonify({'ok': False, 'error': 'CSV başlık satırı bulunamadı.'}), 400
        aliases = {'title':['title','başlık','ihale adı','ihale adi','işin adı','isin adi','name'], 'city':['city','il','şehir','sehir'], 'category':['category','kategori','ürün grubu','urun grubu'], 'deadline':['deadline','son tarih','son teklif tarihi','ihale tarihi'], 'url':['url','link','ihale linki']}
        norm = {h.strip().lower(): h for h in reader.fieldnames}
        mapping = {k: next((norm[a] for a in al if a in norm), None) for k,al in aliases.items()}
        if not mapping['title']:
            return jsonify({'ok': False, 'error': 'Başlık sütunu bulunamadı. CSV başlığı title veya İhale Adı olmalı.'}), 400
        conn = db(); added=0; matched=[]
        for row in reader:
            title = (row.get(mapping['title']) or '').strip()
            if not title: continue
            city = (row.get(mapping['city']) or '').strip() if mapping['city'] else ''
            cat = (row.get(mapping['category']) or '').strip() if mapping['category'] else ''
            deadline = (row.get(mapping['deadline']) or '').strip() if mapping['deadline'] else ''
            url = (row.get(mapping['url']) or '').strip() if mapping['url'] else ''
            key = (url or (title+'|'+city+'|'+deadline)).strip()
            try:
                cur=conn.execute('INSERT OR IGNORE INTO tenders(id,title,city,category,deadline,url,source) VALUES(?,?,?,?,?,?,?)',(key,title,city,cat,deadline,url,'CSV içe aktarma'))
                if cur.rowcount:
                    added += 1
                    if (city in CITIES or not city) and (cat in CATEGORIES or not cat): matched.append((title,city,cat,deadline,url))
            except sqlite3.Error: pass
        conn.commit(); conn.close()
        notified=0
        for title,city,cat,deadline,url in matched:
            msg='📢 EKAP ihale kaydı\n'+title+'\nİl: '+(city or 'Belirtilmemiş')+'\nKategori: '+(cat or 'Belirtilmemiş')+'\nSon tarih: '+(deadline or 'Belirtilmemiş')+(('\n'+url) if url else '')
            ok,_=send_telegram(msg)
            if ok: notified+=1
        return jsonify({'ok': True, 'message': f'{added} yeni kayıt eklendi. Telegram ile {notified} bildirim gönderildi. Yüklenen dosyadaki kayıtların doğruluğunu EKAP üzerinden kontrol et.'})
    except Exception as e:
        return jsonify({'ok': False, 'error': 'CSV okunamadı: '+str(e)[:180]}), 400

@app.get('/health')
def health():
    return jsonify({'ok': True, 'app': 'ekap-takip'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
