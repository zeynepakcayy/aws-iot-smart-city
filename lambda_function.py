"""
lambda_function.py - AWS Lambda İşleyicisi
-------------------------------------------
Bu kod AWS Lambda üzerinde barındırılır ve AWS IoT Core tarafından tetiklenir.
Bir MQTT mesajı 'akillisehir/hava_kalitesi' konusuna ulaştığında,
IoT Core Kuralı (Rule) bu Lambda fonksiyonunu otomatik olarak çağırır.
Lambda'nın görevi: gelen sensör verisini DynamoDB'ye kaydetmektir.

KURULUM NOTU:
- Lambda fonksiyonuna 'AmazonDynamoDBFullAccess' IAM izninin verilmiş olması gerekir.
- DynamoDB tablosunun adı: 'SensorVerileri'
- Tablonun Partition Key'i: 'sensor_id' (String)
- Tablonun Sort Key'i: 'timestamp' (String)
"""

import json
import boto3
from decimal import Decimal  # DynamoDB, float yerine Decimal türü kullanır.

# ==============================================================
# YAPILANDIRMA
# ==============================================================

# DynamoDB tablosunun adı. Konsoldaki tablo adıyla birebir aynı olmalı.
TABLO_ADI = "SensorVerileri"

# ==============================================================
# LAMBDA HANDLER (GİRİŞ NOKTASI)
# ==============================================================

def lambda_handler(event, context):
    """
    AWS Lambda'nın giriş noktası. Her MQTT mesajı geldiğinde bu fonksiyon çağrılır.

    Parametreler:
        event   : IoT Core'dan gelen MQTT payload'unun içeriğidir (Python dict olarak gelir).
        context : Lambda çalışma ortamı hakkında bilgiler içerir (kullanmıyoruz).

    Dönüş Değeri:
        HTTP benzeri bir yanıt sözlüğü. Lambda'nın başarılı çalışıp çalışmadığını gösterir.
    """

    print(f"[LAMBDA] Tetiklendi. Gelen veri: {json.dumps(event)}")

    try:
        # 1. ADIM: DynamoDB kaynaklarına erişim için boto3 istemcisi oluştur.
        # boto3, AWS'nin resmi Python SDK'sıdır.
        # Lambda, IAM rolü sayesinde kimlik bilgisi girmeden otomatik bağlanır.
        dynamodb = boto3.resource("dynamodb")

        # Üzerinde işlem yapacağımız tabloyu seç.
        tablo = dynamodb.Table(TABLO_ADI)

        # 2. ADIM: Gelen 'event' verisi zaten bir Python sözlüğüdür.
        # IoT Core Kuralı, JSON payload'u otomatik olarak parse eder.
        # Ancak DynamoDB float türünü desteklemez; Decimal'e çevirmemiz gerekir.
        veri = json.loads(json.dumps(event), parse_float=Decimal)

        # 3. ADIM: Verinin gerekli alanları içerdiğini doğrula.
        zorunlu_alanlar = ["sensor_id", "timestamp", "sicaklik", "nem", "co2_seviyesi"]
        for alan in zorunlu_alanlar:
            if alan not in veri:
                raise ValueError(f"Eksik alan: '{alan}' gelen veride bulunamadı.")

        # 4. ADIM: Veriyi DynamoDB tablosuna yaz.
        # 'put_item', aynı primary key varsa üzerine yazar; yoksa yeni kayıt oluşturur.
        tablo.put_item(Item=veri)

        print(f"[DYNAMODB] Başarıyla kaydedildi: sensor_id={veri['sensor_id']}, timestamp={veri['timestamp']}")

        # 5. ADIM: Başarı yanıtı döndür.
        return {
            "statusCode": 200,
            "body": json.dumps({
                "mesaj": "Veri başarıyla DynamoDB'ye kaydedildi.",
                "sensor_id": veri["sensor_id"],
                "timestamp": str(veri["timestamp"])
            })
        }

    except ValueError as hata:
        # Eksik alan veya beklenen formatta olmayan veri.
        print(f"[HATA] Geçersiz veri formatı: {hata}")
        return {
            "statusCode": 400,
            "body": json.dumps({"hata": f"Geçersiz veri: {str(hata)}"})
        }

    except Exception as hata:
        # DynamoDB bağlantı hatası veya beklenmeyen durum.
        print(f"[HATA] Beklenmeyen hata: {hata}")
        return {
            "statusCode": 500,
            "body": json.dumps({"hata": f"Sunucu hatası: {str(hata)}"})
        }
