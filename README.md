# Ekşi Sözlük Scraper

**Note:** Turkish documentation is available below. English documentation follows.

---

## English Documentation

### Description

EksiScraper is a robust and flexible scraper for extracting entries from Ekşi Sözlük topics. It uses advanced browser fingerprint spoofing techniques to bypass anti-bot protection and reliably fetch data.

### Features

- **Browser Fingerprint Spoofing**: Uses `curl_cffi` to impersonate Chrome 120 browser
- **Rate Limiting Protection**: Automatic delays between requests with exponential backoff
- **Error Recovery**: Retry logic with intelligent error handling (429, 403, etc.)
- **Duplicate Detection**: Filters out duplicate entries automatically
- **Multi-page Support**: Automatically detects and scrapes all pages of a topic
- **CSV Export**: Saves data with descriptive filenames (`topicname_pagecount_timestamp.csv`)
- **Detailed Logging**: Both console and file logging with configurable verbosity

### Installation

1. Clone or download this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage

#### Command Line Interface

Basic usage:
```bash
python eksiscraper.py "https://eksisozluk.com/topic--123"
```

With custom delay (in milliseconds):
```bash
python eksiscraper.py "https://eksisozluk.com/topic--123" --delay 3000
```

Silent mode (suppress info logs):
```bash
python eksiscraper.py "https://eksisozluk.com/topic--123" --silent
```

Custom output filename:
```bash
python eksiscraper.py "https://eksisozluk.com/topic--123" --output mydata.csv
```

#### Python Module

```python
import eksiscraper

# Create scraper instance
scraper = eksiscraper.EksiScraper(delay_ms=2000, verbose=True)

# Scrape a topic
df = scraper.scrape("https://eksisozluk.com/topic--123")

# Save to CSV
scraper.save_to_csv(df)

# Get summary statistics
summary = scraper.get_summary(df)
print(summary)
```

### How It Works

#### Connection Algorithm

The scraper uses several techniques to ensure reliable connections to Ekşi Sözlük:

1. **TLS Fingerprint Spoofing**: Uses `curl_cffi` library with `impersonate="chrome120"` to mimic Chrome 120's TLS fingerprint, bypassing basic bot detection

2. **Browser-Like Headers**: Sends realistic HTTP headers including:
   - Accept headers for HTML/XML content
   - Turkish language preference
   - Security fetch metadata
   - DNT (Do Not Track) header

3. **Rate Limiting Strategy**:
   - Configurable delay between requests (default: 2000ms)
   - Exponential backoff on rate limit errors (429)
   - Automatic retry with increasing delays on failures

4. **HTML Parsing**:
   - Locates `<ul id="entry-item-list">` container
   - Finds all `<li id="entry-item">` elements
   - Extracts data attributes: `data-id`, `data-author`, `data-author-id`, `data-favorite-count`
   - Parses content from `<div class="content">`
   - Extracts dates from footer links

#### Troubleshooting Connection Issues

If you encounter connection problems:

1. **Test the connection first**:
   ```bash
   python check_html.py
   ```
   This script tests the current connection algorithm against Ekşi Sözlük

2. **If check_html.py fails**: Modify the headers, impersonate parameter, or parsing logic in `check_html.py` until it successfully connects

3. **Apply the fix**: Once `check_html.py` works, copy the working algorithm (headers, impersonate parameter, parsing selectors) to `eksiscraper.py`

### Output Format

Scraped data is saved to the `data/` directory with filenames in the format:
```
data/topic_name_Npages_YYYYMMDD_HHMMSS.csv
```

CSV columns:
- `entry_id`: Unique entry identifier
- `author`: Username of the entry author
- `author_id`: Author's user ID
- `favorite_count`: Number of favorites
- `content`: Entry text content
- `date`: Entry timestamp
- `page_number`: Page where the entry was found

### Requirements

- Python 3.7+
- curl_cffi >= 0.7.0
- beautifulsoup4 >= 4.12.0
- pandas >= 2.0.0
- lxml >= 4.9.0

### License

MIT License

---

## Türkçe Dokümantasyon

### Açıklama

EksiScraper, Ekşi Sözlük başlıklarından entry'leri çekmek için geliştirilmiş sağlam ve esnek bir scraper'dır. Anti-bot korumasını aşmak ve güvenilir veri çekimi için gelişmiş tarayıcı parmak izi taklit teknikleri kullanır.

### Özellikler

- **Tarayıcı Parmak İzi Taklidi**: Chrome 120 tarayıcısını taklit etmek için `curl_cffi` kullanır
- **Rate Limiting Koruması**: İstekler arası otomatik bekleme ve üstel geri çekilme
- **Hata Kurtarma**: Akıllı hata yönetimi ile tekrar deneme mantığı (429, 403, vb.)
- **Kopya Tespiti**: Tekrarlayan entry'leri otomatik filtreler
- **Çoklu Sayfa Desteği**: Başlığın tüm sayfalarını otomatik tespit eder ve tarar
- **CSV Dışa Aktarma**: Açıklayıcı dosya adlarıyla veri kaydeder (`baslikadi_sayfasayisi_zaman.csv`)
- **Detaylı Loglama**: Ayarlanabilir ayrıntı seviyesi ile konsol ve dosya loglama

### Kurulum

1. Bu repo'yu klonlayın veya indirin
2. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

### Kullanım

#### Komut Satırı Arayüzü

Temel kullanım:
```bash
python eksiscraper.py "https://eksisozluk.com/baslik--123"
```

Özel bekleme süresiyle (milisaniye cinsinden):
```bash
python eksiscraper.py "https://eksisozluk.com/baslik--123" --delay 3000
```

Sessiz mod (bilgi loglarını gizle):
```bash
python eksiscraper.py "https://eksisozluk.com/baslik--123" --silent
```

Özel çıktı dosya adı:
```bash
python eksiscraper.py "https://eksisozluk.com/baslik--123" --output verim.csv
```

#### Python Modülü

```python
import eksiscraper

# Scraper örneği oluştur
scraper = eksiscraper.EksiScraper(delay_ms=2000, verbose=True)

# Bir başlığı tara
df = scraper.scrape("https://eksisozluk.com/baslik--123")

# CSV'ye kaydet
scraper.save_to_csv(df)

# Özet istatistikler al
summary = scraper.get_summary(df)
print(summary)
```

### Nasıl Çalışır

#### Bağlantı Algoritması

Scraper, Ekşi Sözlük'e güvenilir bağlantılar sağlamak için çeşitli teknikler kullanır:

1. **TLS Parmak İzi Taklidi**: Chrome 120'nin TLS parmak izini taklit etmek için `curl_cffi` kütüphanesini `impersonate="chrome120"` parametresiyle kullanır, temel bot tespitini atlatır

2. **Tarayıcı Benzeri Header'lar**: Gerçekçi HTTP header'ları gönderir:
   - HTML/XML içerik için Accept header'ları
   - Türkçe dil tercihi
   - Güvenlik fetch metadata'sı
   - DNT (Do Not Track) header'ı

3. **Rate Limiting Stratejisi**:
   - İstekler arası ayarlanabilir bekleme (varsayılan: 2000ms)
   - Rate limit hatalarında (429) üstel geri çekilme
   - Hatalarda artan bekleme süreleriyle otomatik tekrar deneme

4. **HTML Ayrıştırma**:
   - `<ul id="entry-item-list">` konteynerini bulur
   - Tüm `<li id="entry-item">` elementlerini bulur
   - Data attribute'larını çıkarır: `data-id`, `data-author`, `data-author-id`, `data-favorite-count`
   - `<div class="content">` içeriğini ayrıştırır
   - Footer linklerinden tarihleri çıkarır

#### Bağlantı Sorunlarını Giderme

Bağlantı sorunlarıyla karşılaşırsanız:

1. **Önce bağlantıyı test edin**:
   ```bash
   python check_html.py
   ```
   Bu script mevcut bağlantı algoritmasını Ekşi Sözlük'e karşı test eder

2. **check_html.py başarısız olursa**: `check_html.py` içindeki header'ları, impersonate parametresini veya ayrıştırma mantığını başarıyla bağlanana kadar değiştirin

3. **Düzeltmeyi uygulayın**: `check_html.py` çalıştıktan sonra, çalışan algoritmayı (header'lar, impersonate parametresi, ayrıştırma seçicileri) `eksiscraper.py`'ye kopyalayın

### Çıktı Formatı

Taranan veriler `data/` dizinine şu formatta kaydedilir:
```
data/baslik_adi_Nsayfa_YYYYMMDD_HHMMSS.csv
```

CSV sütunları:
- `entry_id`: Benzersiz entry kimliği
- `author`: Entry yazarının kullanıcı adı
- `author_id`: Yazarın kullanıcı ID'si
- `favorite_count`: Favori sayısı
- `content`: Entry metin içeriği
- `date`: Entry zaman damgası
- `page_number`: Entry'nin bulunduğu sayfa

### Gereksinimler

- Python 3.7+
- curl_cffi >= 0.7.0
- beautifulsoup4 >= 4.12.0
- pandas >= 2.0.0
- lxml >= 4.9.0

### Lisans

MIT License
