"""
Ekşi Sözlük HTML yapısını kontrol et
"""
from curl_cffi import requests
from bs4 import BeautifulSoup

# Test sayfası
url = "https://eksisozluk.com/test--114?p=2"  # 2. sayfa

# curl_cffi ile TLS fingerprint bypass - Chrome 120 tarayıcısını taklit eder
headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'DNT': '1'
}

# impersonate="chrome120" parametresi Chrome 120'nin TLS fingerprint'ini kullanır
response = requests.get(url, headers=headers, impersonate="chrome120", timeout=30)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    entry_list = soup.find('ul', {'id': 'entry-item-list'})
    
    if entry_list:
        # İlk birkaç li elementini kontrol et
        li_elements = entry_list.find_all('li')[:2]  # İlk 2 li elementi al
        
        print("Li elementi örnekleri:")
        print("-" * 60)
        for i, li in enumerate(li_elements, 1):
            print(f"\n{i}. Li elementi:")
            print(f"  - Tag: {li.name}")
            print(f"  - ID: {li.get('id', 'YOK')}")
            print(f"  - Class: {li.get('class', 'YOK')}")
            print(f"  - data-id: {li.get('data-id', 'YOK')}")
            print(f"  - data-author: {li.get('data-author', 'YOK')}")
            
            # İçerik preview
            content = li.find('div', class_='content')
            if content:
                text = content.get_text(strip=True)[:100]
                print(f"  - İçerik: {text}...")
        
        # Farklı selector'ları dene
        print("\n" + "="*60)
        print("Farklı selector sonuçları:")
        print("-" * 60)
        
        # 1. id="entry-item" ile
        test1 = entry_list.find_all('li', {'id': 'entry-item'})
        print(f"li[id='entry-item']: {len(test1)} adet")
        
        # 2. data-id attribute'u olanlar
        test2 = entry_list.find_all('li', attrs={'data-id': True})
        print(f"li[data-id]: {len(test2)} adet")
        
        # 3. Doğrudan li elementi
        test3 = entry_list.find_all('li')
        print(f"Tüm li: {len(test3)} adet")
        
        # İlk entry'nin HTML'ini göster
        if test3:
            print("\n" + "="*60)
            print("İlk li elementinin tam HTML'i (ilk 500 karakter):")
            print("-" * 60)
            print(str(test3[0])[:500])
    else:
        print("entry-item-list bulunamadı!")
else:
    print(f"Sayfa çekilemedi: {response.status_code}")
    print(f"Response headers: {response.headers}")
