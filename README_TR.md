# EKAP İhale Takip — Android ile kurulum

Bu paket, eski yalnızca görsel arayüzün yerine gerçek sunucu tarafı olan bir ilk sürüm sunar.

## Neler çalışır?
- Şifreli giriş ekranı.
- Sunucuda tanımlı Telegram bot tokenı ve Chat ID ile gerçek test mesajı.
- EKAP'tan dışa aktarılmış/izinli kaynaktan alınmış CSV dosyasını yükleme.
- CSV kayıtlarını ekranda listeleme ve telefonda seçilen il/kategori filtreleri.
- İçe aktarılan yeni kayıtlar için Telegram bildirimi.

## Henüz ne çalışmaz?
- Resmî EKAP canlı verisine otomatik bağlanma yoktur. EKAP'ta izin verilen bir veri kaynağı/aktarım yöntemi bulunmadan canlı ihale çektiğini varsaymayın.
- 30 dakikalık otomatik canlı tarama bu sürümde kurulmamıştır.
- Render ücretsiz web hizmetleri 15 dakika istek almadığında uykuya geçebilir; ücretsiz planda sürekli arka plan görevi garanti edilmez.
- Render ücretsiz dosya sistemi kalıcı değildir; örnek SQLite kayıtları yeniden başlatma/deploy sonrası silinebilir. Kalıcı kullanım için kalıcı veritabanı gerekir.

## Render kurulum özeti
1. Bu klasördeki dosyaları GitHub'da yeni ve PRIVATE bir depoya yükleyin. Token'ları asla dosyalara koymayın.
2. Render Dashboard > New > Blueprint ile bu depoyu bağlayıp `render.yaml` dosyasını seçin. (Alternatif: New > Web Service, Build: `pip install -r requirements.txt`, Start: `gunicorn app:app --bind 0.0.0.0:$PORT`.)
3. Render servisi için Environment bölümünde şunları tanımlayın:
   - `APP_PASSWORD`: yalnızca sizin bileceğiniz güçlü bir giriş şifresi
   - `TELEGRAM_BOT_TOKEN`: BotFather'dan alınan yeni token (gizli)
   - `TELEGRAM_CHAT_ID`: sizin sohbet ID'niz
   - `FLASK_SECRET`: rastgele, uzun gizli değer (render.yaml otomatik üretir)
4. Deploy tamamlanınca Render'ın verdiği HTTPS adresini açın ve APP_PASSWORD ile giriş yapın.
5. “Test mesajı gönder”e basın. Telegram'a mesaj gelirse entegrasyon çalışıyor demektir.

## CSV biçimi
Başlık satırı zorunlu. Tercih edilen sütun adları:
`title,city,category,deadline,url`

Örnek satır (sadece şablon, gerçek ihale değildir):
`Örnek kayıt,Çorum,Bakliyat,2026-12-01,https://example.com`

Kategori alanı filtrelerde kullanılan şu değerlerden biriyle aynı yazılmalı: `Bakliyat`, `Kuru gıda`, `Donuk ürünler`.
İller: `Çorum`, `Kırıkkale`, `Samsun`, `Çankırı`, `Amasya`, `Tokat`, `Kastamonu`.

## Güvenlik
- Bot token'ını sohbetlerde, ekran görüntülerinde veya GitHub dosyalarında paylaşmayın.
- Token daha önce ifşa olduysa BotFather'da `/revoke` ile yenisini oluşturun.
- Bu ilk sürüm, gerçek ihale bilgisi ve mevzuata uygunluk için EKAP kaynağının ayrıca doğrulanmasını gerektirir.
