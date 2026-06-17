"""
arayuz.py - Streamlit Web Arayüzü (Front-End)
-----------------------------------------------
Bu dosya yerel bilgisayarda tarayıcı üzerinden çalışan web arayüzüdür.
Çalıştırmak için terminale şunu yazın:
    streamlit run arayuz.py

DynamoDB'deki 'SensorVerileri' tablosundan verileri çeker ve
anlık metrikler ile zaman serisi grafikleri olarak gösterir.

KURULUM NOTU:
- AWS kimlik bilgilerinizin yapılandırılmış olması gerekir.
- Bunu yapmak için terminalde şunu çalıştırın: aws configure
- Gerekli izin: DynamoDB tablosunda 'scan' veya 'query' yetkisi.
"""

import streamlit as st
import boto3
import pandas as pd
from decimal import Decimal
from boto3.dynamodb.conditions import Key

# ==============================================================
# YAPILANDIRMA
# ==============================================================

# DynamoDB tablosunun adı (Lambda'daki ile aynı olmalı).
TABLO_ADI = "SensorVerileri"

# Hangi AWS bölgesinde çalıştığınızı belirtin (örn: "eu-central-1", "us-east-1").
AWS_BOLGE = "eu-central-1"

# ==============================================================
# VERİ ÇEKME FONKSİYONU
# ==============================================================

@st.cache_data(ttl=0)  # Her çağrıda DynamoDB'den taze veri çek, önbelleğe alma.
def veri_cek():
    """
    DynamoDB tablosundaki tüm kayıtları çeker ve Pandas DataFrame'e dönüştürür.
    Veriler zaman damgasına (timestamp) göre eskiden yeniye doğru sıralanır.

    Dönüş: pandas.DataFrame - başarılıysa dolu, hata olursa boş DataFrame.
    """
    try:
        # boto3 ile DynamoDB'ye bağlan.
        dynamodb = boto3.resource(
            'dynamodb',
            region_name='eu-central-1',
            aws_access_key_id='YOUR_AWS_ACCESS_KEY_ID',
            aws_secret_access_key='YOUR_AWS_SECRET_ACCESS_KEY'
        )
        tablo = dynamodb.Table(TABLO_ADI)

        # 'scan', tablodaki tüm verileri çeker.
        # NOT: Büyük veritabanları için daha verimli olan 'query' tercih edilmeli.
        # Şu an eğitim amaçlı olduğu için scan kullanıyoruz.
        yanit = tablo.scan()
        kayitlar = yanit["Items"]

        # DynamoDB bazen 1 MB'lık sayfalar halinde veri döndürür.
        # "LastEvaluatedKey" varsa, daha fazla sayfa olduğu anlamına gelir; hepsini çekiyoruz.
        while "LastEvaluatedKey" in yanit:
            yanit = tablo.scan(ExclusiveStartKey=yanit["LastEvaluatedKey"])
            kayitlar.extend(yanit["Items"])

        if not kayitlar:
            return pd.DataFrame()  # Tablo boşsa boş DataFrame döndür.

        # Python listesini Pandas DataFrame'e çevir.
        df = pd.DataFrame(kayitlar)

        # DynamoDB'den gelen sayısal değerler Decimal türündedir; float'a çeviriyoruz.
        for sutun in ["sicaklik", "nem", "co2_seviyesi"]:
            if sutun in df.columns:
                df[sutun] = df[sutun].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

        # Zaman damgasını string'den gerçek bir datetime nesnesine çevir.
        # Bu işlem, grafiklerde X ekseninin düzgün görünmesi için zorunludur.
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Verileri zaman damgasına göre sırala (en eski -> en yeni).
        df = df.sort_values("timestamp").reset_index(drop=True)

        return df

    except Exception as hata:
        # AWS bağlantı hatası, izin hatası vb. durumlar için.
        st.error(f"DynamoDB bağlantı hatası: {hata}")
        return pd.DataFrame()


# ==============================================================
# SAYFA DÜZENİ VE ARAYÜZ BİLEŞENLERİ
# ==============================================================

def main():
    """Ana arayüz fonksiyonu. Tüm Streamlit bileşenlerini oluşturur."""

    # Tarayıcı sekmesinin başlığını ve ikon ayarını yap.
    st.set_page_config(
        page_title="Akıllı Şehir Paneli",
        page_icon="🏙️",
        layout="wide"  # Geniş ekran düzeni kullan.
    )

    # ---- BAŞLIK BÖLÜMÜ ----
    st.title("🏙️ Akıllı Şehir Hava Kalitesi Takip Paneli")
    st.markdown("**AWS IoT Core & DynamoDB** üzerinden gerçek zamanlı sensör verilerini görselleştirir.")
    st.divider()  # Görsel ayırıcı çizgi.

    # ---- YENİLEME BUTONU ----
    # Kullanıcı bu butona tıkladığında DynamoDB'den en güncel veriler çekilir.
    yenile_butonu = st.button("🔄 Verileri Yenile", type="primary")

    # Buton tıklandığında Streamlit'in önbelleğini temizle, böylece taze veri gelsin.
    if yenile_butonu:
        st.cache_data.clear()
        st.success("Veriler güncellendi!")

    # ---- VERİYİ ÇEK ----
    with st.spinner("DynamoDB'den veriler yükleniyor..."):
        df = veri_cek()

    # Eğer hiç veri yoksa kullanıcıya bilgi mesajı göster ve dur.
    if df.empty:
        st.warning("⚠️ DynamoDB tablosunda henüz veri yok veya bağlantı kurulamadı. "
                   "Lütfen 'sensor.py' dosyasını çalıştırarak veri üretmeye başlayın.")
        return  # Arayüzün geri kalanını oluşturmaya gerek yok.

    # En son gelen kaydı alıyoruz (DataFrame zaman damgasına göre sıralı).
    son_kayit = df.iloc[-1]

    # ---- ANLIK DURUM KARTLARI (METRIKLER) ----
    # st.metric, büyük ve okunaklı metrik kartları oluşturur.
    st.subheader("📊 Anlık Sensor Değerleri")
    kol1, kol2, kol3, kol4 = st.columns(4)

    with kol1:
        st.metric(
            label="🌡️ Sıcaklık",
            value=f"{son_kayit['sicaklik']:.1f} °C"
        )

    with kol2:
        st.metric(
            label="💧 Nem",
            value=f"{son_kayit['nem']:.1f} %"
        )

    with kol3:
        # CO2 değerini int olarak göster, daha okunabilir.
        co2_degeri = int(son_kayit["co2_seviyesi"])
        # CO2 seviyesine göre renk/uyarı mantığı.
        co2_durumu = "Normal ✅" if co2_degeri < 600 else ("Dikkat ⚠️" if co2_degeri < 800 else "Kötü 🚨")
        st.metric(
            label="☁️ CO₂ Seviyesi (ppm)",
            value=f"{co2_degeri} ppm",
            delta=co2_durumu,
            delta_color="off"
        )

    with kol4:
        st.metric(
            label="🕒 Son Güncelleme",
            value=son_kayit["timestamp"].strftime("%H:%M:%S"),
            help="Son verinin alındığı saat (UTC)."
        )

    st.divider()

    # ---- ZAMANSAL GRAFİKLER ----
    st.subheader("📈 Zaman Serisi Grafikleri")

    # Grafikleri yan yana iki sütunda göster.
    grafik_kol1, grafik_kol2 = st.columns(2)

    with grafik_kol1:
        st.markdown("**Sıcaklık Değişimi (°C)**")
        # st.line_chart, Pandas DataFrame sütununu doğrudan grafik olarak çizer.
        # 'x' parametresi X eksenini, 'y' parametresi Y eksenini belirler.
        st.line_chart(
            df.set_index("timestamp")["sicaklik"],
            color="#FF6B6B"  # Kırmızımsı renk (ısı hissi).
        )

    with grafik_kol2:
        st.markdown("**CO₂ Seviyesi Değişimi (ppm)**")
        st.line_chart(
            df.set_index("timestamp")["co2_seviyesi"],
            color="#4ECDC4"  # Yeşilimsi-mavi renk (hava kalitesi).
        )

    # Nem grafiği tam genişlikte göster.
    st.markdown("**Nem Değişimi (%)**")
    st.line_chart(
        df.set_index("timestamp")["nem"],
        color="#45B7D1"  # Mavi renk (su/nem hissi).
    )

    st.divider()

    # ---- HAM VERİ TABLOSU ----
    # Kullanıcı isterse tüm verileri tablo olarak da görebilsin.
    with st.expander("📋 Ham Veriyi Göster / Gizle"):
        # Tabloyu ters sırada göster: en yeni kayıt en üstte.
        st.dataframe(
            df[["timestamp", "sensor_id", "sicaklik", "nem", "co2_seviyesi"]]
            .sort_values("timestamp", ascending=False)
            .reset_index(drop=True),
            use_container_width=True
        )

    # Sayfanın alt kısmına küçük bir bilgi notu ekle.
    st.caption(f"Toplam {len(df)} kayıt gösteriliyor. Kaynak: AWS DynamoDB '{TABLO_ADI}' tablosu.")


# Bu dosya doğrudan çalıştırıldığında (streamlit run arayuz.py) main() çağrılır.
if __name__ == "__main__":
    main()
