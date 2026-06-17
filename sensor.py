"""
sensor.py - IoT Cihaz Simülatörü
---------------------------------
Bu dosya, gerçek bir hava kalitesi sensörünü taklit eden bir Python simülatörüdür.
Yerel bilgisayarda çalışır ve ürettiği sahte sensör verilerini
MQTT protokolü aracılığıyla AWS IoT Core'a iletir.
"""

import json
import random
import time
from datetime import datetime, timezone

# AWS IoT SDK'dan gerekli sınıfları içe aktarıyoruz.
# awsiotsdk, AWS'nin resmi Python kütüphanesidir.
from awsiot import mqtt_connection_builder
from awscrt import mqtt

# ==============================================================
# YAPILANDIRMA (CONFIG) - Kendi AWS bilgilerinizle doldurun
# ==============================================================

# AWS IoT Core'daki cihaz özel endpoint'iniz.
# Bu adresi AWS Konsolu > IoT Core > Settings bölümünden bulabilirsiniz.
AWS_IOT_ENDPOINT = "YENI_AWS_ENDPOINT_ADRESIN"

# Sertifika dosyalarının yolları.
# Bu dosyaları AWS'den indirip proje klasörü altındaki 'certs' klasörüne koyun.
CERT_FILE   = "./certs/certificate.pem.crt"   # Cihaz sertifikası
KEY_FILE    = "./certs/private.pem.key"        # Cihaz özel anahtarı
CA_FILE     = "./certs/AmazonRootCA1.pem"      # Amazon Kök CA sertifikası

# MQTT konusu (Topic): Verinin yayınlanacağı adres.
# AWS IoT Core'daki Kural (Rule) bu konuyu dinleyecek.
MQTT_TOPIC  = "akillisehir/hava_kalitesi"

# Sensörümüze verdiğimiz benzersiz kimlik (ID).
# Birden fazla sensör varsa her birinin farklı bir ID'si olur.
SENSOR_ID   = "ANK_Golbasi_01"

# Kaç saniyede bir veri gönderilecek?
PUBLISH_INTERVAL_SECONDS = 5

# ==============================================================
# BAĞLANTI KURMA FONKSİYONU
# ==============================================================

def baglan():
    """
    AWS IoT Core'a güvenli (TLS/SSL) bir MQTT bağlantısı kurar.
    Sertifika dosyalarını kullanarak kimlik doğrulaması yapar.
    Başarılı bağlantı nesnesi (mqtt_connection) döndürür.
    """
    print(f"[BAĞLANTI] AWS IoT Core'a bağlanılıyor: {AWS_IOT_ENDPOINT}")

    # mqtt_connection_builder, sertifika tabanlı bağlantıyı kolayca kurmamızı sağlar.
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=AWS_IOT_ENDPOINT,
        cert_filepath=CERT_FILE,
        pri_key_filepath=KEY_FILE,
        ca_filepath=CA_FILE,
        # Bağlantı kimliği: Her bağlanan cihazın benzersiz olması gerekir.
        client_id=f"simülasyon-{SENSOR_ID}"
    )

    # Bağlantı isteğini gönder ve yanıt bekle.
    connect_future = mqtt_connection.connect()
    connect_future.result()  # Bağlantı tamamlanana kadar burada bekler.

    print("[BAĞLANTI] Başarıyla bağlandı!")
    return mqtt_connection


# ==============================================================
# SENSÖR VERİSİ ÜRETME FONKSİYONU
# ==============================================================

def sensör_verisi_üret():
    """
    Gerçekçi değer aralıklarında rastgele sensör verisi üretir.
    Döndürdüğü sözlük (dict), JSON formatına dönüştürülerek gönderilecektir.
    """
    veri = {
        # Sensörün kim olduğunu belirtir.
        "sensor_id": SENSOR_ID,

        # ISO 8601 formatında UTC zaman damgası (örn: 2026-06-17T10:30:00+00:00).
        # DynamoDB'de zaman bazlı sorgulama için kritik bir alandır.
        "timestamp": datetime.now(timezone.utc).isoformat(),

        # Sıcaklık: 20.0 ile 35.0 derece Celsius arasında, 2 ondalık basamakla.
        "sicaklik": round(random.uniform(20.0, 35.0), 2),

        # Nem: %30 ile %70 arasında, 2 ondalık basamakla.
        "nem": round(random.uniform(30.0, 70.0), 2),

        # CO2 Seviyesi: 350 ile 900 ppm arasında tam sayı.
        # 400 ppm normal dış hava, 1000+ ppm kötü iç hava kalitesini ifade eder.
        "co2_seviyesi": random.randint(350, 900),
    }
    return veri


# ==============================================================
# ANA DÖNGÜ
# ==============================================================

def main():
    """
    Ana fonksiyon: AWS'ye bağlanır ve her 5 saniyede bir veri yayınlar.
    Programı durdurmak için Ctrl+C kullanın.
    """
    try:
        # 1. ADIM: AWS IoT Core'a bağlan.
        mqtt_connection = baglan()

        print(f"\n[YAYINCA] '{MQTT_TOPIC}' konusuna her {PUBLISH_INTERVAL_SECONDS} saniyede bir veri gönderiliyor...")
        print("[YAYINCI] Durdurmak için Ctrl+C'ye basın.\n")

        # 2. ADIM: Sonsuz döngüde veri üretip yayınla.
        while True:
            # Sahte sensör verisi oluştur.
            veri = sensör_verisi_üret()

            # Python sözlüğünü JSON formatındaki string'e dönüştür.
            # AWS IoT Core ve Lambda, veriyi JSON formatında bekler.
            json_verisi = json.dumps(veri, ensure_ascii=False)

            # MQTT publish: Veriyi belirlenen konuya (topic) gönder.
            # QoS=1, mesajın en az bir kez iletilmesini garanti eder.
            mqtt_connection.publish(
                topic=MQTT_TOPIC,
                payload=json_verisi,
                qos=mqtt.QoS.AT_LEAST_ONCE
            )

            print(f"[GÖNDERİLDİ] {json_verisi}")

            # Bir sonraki gönderme işlemine kadar bekle.
            time.sleep(PUBLISH_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        # Kullanıcı Ctrl+C'ye bastığında buraya düşer.
        print("\n\n[DURDURULDU] Kullanıcı tarafından durduruldu.")

    except Exception as hata:
        # AWS bağlantı hataları veya beklenmeyen durumlar için.
        print(f"\n[HATA] Beklenmeyen bir hata oluştu: {hata}")

    finally:
        # Program hangi nedenle sonlanırsa sonlansın, bağlantıyı temiz kapat.
        if 'mqtt_connection' in locals():
            print("[BAĞLANTI] Bağlantı kapatılıyor...")
            disconnect_future = mqtt_connection.disconnect()
            disconnect_future.result()
            print("[BAĞLANTI] Bağlantı kapatıldı. Güle güle!")


# Bu dosya doğrudan çalıştırıldığında main() fonksiyonunu başlat.
if __name__ == "__main__":
    main()
