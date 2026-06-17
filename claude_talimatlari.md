# Proje İsterleri: AWS IoT ve Streamlit Tabanlı Akıllı Şehir Uygulaması

## 1. Proje Özeti ve Amacı
[cite_start]Bu proje, bir Bulut Bilişim dersi final ödevi için geliştirilmektedir[cite: 1, 56]. [cite_start]Amaç; sanal bir IoT cihazından (Python simülatörü) üretilen çevre verilerini MQTT protokolü üzerinden AWS bulutuna aktarmak, AWS üzerinde işlemek ve bir web arayüzünde (front-end) gerçek zamanlı olarak görselleştirmektir[cite: 41, 46, 47, 51].

## 2. Hedeflenen Mimari ve Teknoloji Yığını
- **IoT Cihaz Simülatörü:** Python (awsiotsdk kütüphanesi)
- [cite_start]**Haberleşme Protokolü:** MQTT (Port: 8883 - Güvenli Bağlantı) [cite: 46]
- [cite_start]**Bulut Platformu:** AWS (IoT Core, AWS Lambda, Amazon DynamoDB) [cite: 47]
- **Front-End / Görselleştirme:** Python (Streamlit ve Pandas)

## 3. Senden (Claude Code) Beklenen Dosya Yapısı ve Kodlar

Lütfen projeyi modüler ve temiz bir Python koduyla yaz. Aşağıdaki 3 ana dosyayı oluşturmanı bekliyorum:

### A) `sensor.py` (IoT Simülatörü)
[cite_start]Bu dosya yerel bilgisayarda çalışacak ve AWS IoT Core'a bağlanacaktır[cite: 47].
- **Gereksinimler:**
  - `awsiotsdk` kütüphanesini kullanmalıdır.
  - `./certs/` klasörü altındaki AWS sertifikalarını (`certificate.pem.crt`, `private.pem.key`, `AmazonRootCA1.pem`) okuyarak güvenli bağlantı (TLS/SSL) kurmalıdır.
  - [cite_start]AWS IoT Core üzerindeki `akillisehir/hava_kalitesi` MQTT konusuna (topic) her 5 saniyede bir veri yayınlamalıdır (publish)[cite: 46].
  - Gönderilecek JSON veri yapısı şu şekilde olmalıdır:
    ```json
    {
      "sensor_id": "ANK_Golbasi_01",
      "timestamp": "Mevcut Zaman Damgası (ISO formatında)",
      "sicaklik": 20 ile 35 arasında rastgele float,
      "nem": 30 ile 70 arasında rastgele float,
      "co2_seviyesi": 350 ile 900 arasında rastgele int
    }
    ```

### B) `lambda_function.py` (AWS Lambda İşleyicisi)
[cite_start]Bu kod AWS Lambda üzerinde çalışacaktır[cite: 47]. IoT Core'a gelen verileri yakalayıp DynamoDB'ye yazacaktır.
- **Gereksinimler:**
  - `boto3` kütüphanesini kullanmalıdır.
  - AWS IoT Core tetiklemesiyle gelen MQTT payload'unu (JSON) almalıdır.
  - Gelen veriyi `SensorVerileri` isimli Amazon DynamoDB tablosuna kaydetmelidir.

### C) `arayuz.py` (Streamlit Front-End)
[cite_start]Bu dosya yerel bilgisayarda tarayıcı üzerinden çalışacak web arayüzüdür[cite: 51].
- **Gereksinimler:**
  - `streamlit`, `boto3` ve `pandas` kütüphanelerini kullanmalıdır.
  - `SensorVerileri` isimli DynamoDB tablosundan son gelen verileri çekmelidir (boto3 scan veya query ile).
  - **Arayüz Bileşenleri:**
    - Sayfa Başlığı: "Akıllı Şehir Hava Kalitesi Takip Paneli"
    - Anlık Durum Kartları (st.metric): En son gelen Sıcaklık, Nem ve CO2 değerleri.
    - Canlı Grafikler (st.line_chart): Zaman serisi grafiği (Zamana göre sıcaklık ve CO2 değişim trendleri).
    - Yenileme Butonu: Veritabanından güncel verileri çekmek için bir buton.

## 4. Kodlama Standartları
- Kodlar son derece açıklayıcı yorum satırları (comment) içermelidir. (Proje videosunda kodları sözlü olarak açıklayacağım için mantığı net olmalı) [cite_start][cite: 58].
- Hataları yakalamak için `try-except` blokları kullanılmalıdır (Özellikle AWS bağlantı kısımlarında).