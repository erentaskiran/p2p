# P2P Dosya Paylaşım Uygulaması

## Mevcut Özellikler
- UDP ile aktif peer'lar taranıp array'de tutuluyor
- TCP ile peer'lar arası bağlantı kuruluyor
- Websocket sunucusu client için başlatılıyor

## Planlanan Özellikler
### Dosya Paylaşım Sistemi
- Dosyalar 128KB'lık chunk'lara bölünecek (şimdilik)
- Dosyalar için otomatik manifest JSON'ları oluşturulacak
- Örnek manifest yapısı: `file-manifest.json`

### Peer İletişimi
- Peer'lar dosya istediğinde:
  1. İlgili dosyanın manifest dosyasını alacak
  2. Chunk'ları farklı peer'lardan elde etmeye çalışacak
  3. Tüm chunk'ları birleştirecek

## Yapılacaklar Listesi
1. Dosya manifest JSON'larının otomatik oluşturulması
2. Dosyaların chunk'lara bölünmesi
3. Dosyaların gönderilip alınması
4. Websocket ile frontend'e bilgi gönderimi
5. Electron ile frontend oluşturulması
6. Electron'dan dosya seçimi gibi işlemlerin websocket ile P2P client'a gönderilmesi

## Sistem Tasarımı
![Sistem Tasarımı](./system-design.png)