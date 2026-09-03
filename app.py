"""
================================================================================
 Kurgusal Hava Araçları için Aerodinamik Analiz Dashboard'u
 Havacılık ve Uzay Mühendisliği Portfolyo Projesi
================================================================================
Bu uygulama; SimScale üzerinde k-omega SST türbülans modeli kullanılarak
gerçekleştirilen CFD (Hesaplamalı Akışkanlar Dinamiği) simülasyon sonuçlarını
interaktif olarak sunar. Analiz edilen geometriler Fusion 360'ta modellenmiş
kurgusal hava araçlarıdır (ör. Quinjet, Iron Man Zırhı).

Not: Bu dosyadaki sayısal veriler (Cd, Cl, L/D vb.) ÖRNEK/PLACEHOLDER
verilerdir. Kendi SimScale sonuçlarınızı 'get_simulation_data()' ve
'get_comparison_data()' fonksiyonlarındaki ilgili yerlere girmeniz
gerekmektedir. Aynı şekilde basınç haritası / streamline görselleri için
'assets/' klasörü altına kendi render'larınızı eklemeniz gerekir.
================================================================================
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# ------------------------------------------------------------------------------
# SAYFA YAPILANDIRMASI
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Aerodinamik Analiz | Kurgusal Hava Araçları CFD Projesi",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------------------
# ÖZEL CSS - Mühendislik/Teknik Tema
# ------------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
    /* Genel arka plan ve font ayarları */
    .main {
        background-color: #0e1117;
    }
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        color: #e6edf3;
    }
    /* Hero bölümü kutusu */
    .hero-box {
        background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%);
        padding: 2.2rem;
        border-radius: 14px;
        border: 1px solid #2a3f5f;
        margin-bottom: 1.5rem;
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: #4fc3f7;
        margin-bottom: 0.3rem;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #b0bec5;
    }
    /* Metodoloji kutuları */
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .metric-card h3 {
        color: #4fc3f7;
        font-size: 1.6rem;
        margin: 0;
    }
    .metric-card p {
        color: #8b949e;
        margin: 0;
        font-size: 0.85rem;
    }
    .section-divider {
        border-top: 1px solid #30363d;
        margin: 2rem 0;
    }
    .disclaimer-box {
        background-color: #1c1f26;
        border-left: 4px solid #f7b731;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        font-size: 0.85rem;
        color: #d1d5da;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==============================================================================
# 1. VERİ KATMANI (DATA LAYER)
# ==============================================================================
# NOT: Aşağıdaki fonksiyonlar örnek/sentetik veri üretir. Kendi SimScale
# çıktılarınızla (CSV/Excel export) bu kısmı değiştirebilir veya
# pd.read_csv("data/simscale_results.csv") gibi bir okuma ekleyebilirsiniz.

AOA_LIST = [0, 5, 10, 15]  # Hücum Açısı (derece) - sidebar seçenekleriyle eşleşmeli


@st.cache_data
def get_simulation_data(aircraft: str) -> pd.DataFrame:
    """
    Seçilen araç için Hücum Açısına (AoA) bağlı Cd ve Cl verilerini döndürür.
    Gerçek kullanımda: SimScale'den export edilen kuvvet katsayılarını
    buraya CSV olarak okutabilirsiniz.
    """
    rng = np.random.default_rng(seed=hash(aircraft) % 1000)

    aoa = np.array(AOA_LIST, dtype=float)

    if aircraft == "Quinjet":
        cd = 0.045 + 0.0028 * aoa + 0.00015 * aoa**2
        cl = 0.02 + 0.062 * aoa - 0.0009 * aoa**2
    else:  # Iron Man Zırhı
        cd = 0.38 + 0.006 * aoa + 0.0004 * aoa**2
        cl = 0.05 + 0.031 * aoa - 0.0004 * aoa**2

    # Küçük gerçekçi gürültü (simülasyon-benzeri varyasyon)
    cd += rng.normal(0, 0.0015, size=len(aoa))
    cl += rng.normal(0, 0.003, size=len(aoa))

    df = pd.DataFrame({
        "AoA": aoa,
        "Cd": cd,
        "Cl": cl,
        "L/D": cl / cd,
    })
    return df


@st.cache_data
def get_comparison_data() -> pd.DataFrame:
    """
    Orijinal kurgusal tasarım ile aerodinamik olarak iyileştirilmiş
    (winglet eklenmiş) tasarımın karşılaştırma verisi.
    """
    data = {
        "Tasarım": [
            "Orijinal Quinjet (Kurgusal)",
            "İyileştirilmiş Quinjet (+ Winglet)",
            "Orijinal Iron Man Zırhı (Kurgusal)",
            "İyileştirilmiş Zırh (+ Kanat Profili Düzeltmesi)",
        ],
        "Cd (Sürükleme Katsayısı)": [0.061, 0.052, 0.402, 0.365],
        "Cl (Kaldırma Katsayısı)": [0.24, 0.29, 0.11, 0.14],
        "L/D (Verimlilik)": [3.93, 5.58, 0.27, 0.38],
        "İyileşme (%)": ["-", "+42.0%", "-", "+40.7%"],
    }
    return pd.DataFrame(data)


def get_pressure_image_path(aircraft: str, aoa: int) -> str:
    """
    Belirli bir araç ve hücum açısı için basınç haritası görselinin
    dosya yolunu döndürür. Kendi SimScale render görsellerinizi
    'assets/pressure/' klasörüne aşağıdaki isimlendirme ile koyun:
        quinjet_aoa0.png, quinjet_aoa5.png, ironman_aoa10.png ...
    """
    prefix = "quinjet" if aircraft == "Quinjet" else "ironman"
    return f"assets/pressure/{prefix}_aoa{aoa}.png"


def get_streamline_image_path(aircraft: str, aoa: int) -> str:
    """Streamline (akım çizgisi) görseli için dosya yolu - aynı mantık."""
    prefix = "quinjet" if aircraft == "Quinjet" else "ironman"
    return f"assets/streamlines/{prefix}_aoa{aoa}.png"


# ==============================================================================
# 2. SIDEBAR - İNTERAKTİF PARAMETRE SEÇİMİ
# ==============================================================================
with st.sidebar:
    st.markdown("## 🛠️ Simülasyon Parametreleri")
    st.markdown("---")

    aircraft_choice = st.selectbox(
        "Analiz Edilecek Araç",
        options=["Quinjet", "Iron Man Zırhı"],
        help="CFD analizinin yürütüldüğü kurgusal hava aracı geometrisi.",
    )

    st.markdown("#### Akış Koşulları")
    speed_unit = st.radio("Hız Birimi", ["m/s", "Mach"], horizontal=True)

    if speed_unit == "m/s":
        flow_speed = st.slider(
            "Akış Hızı (m/s)", min_value=10, max_value=300, value=120, step=5
        )
        mach_display = flow_speed / 343.0  # deniz seviyesi ses hızı yaklaşık
    else:
        mach_slider = st.slider(
            "Mach Sayısı", min_value=0.05, max_value=0.9, value=0.35, step=0.01
        )
        flow_speed = mach_slider * 343.0
        mach_display = mach_slider

    st.caption(f"≈ {flow_speed:.1f} m/s  |  Mach {mach_display:.2f}")

    st.markdown("#### Hücum Açısı (Angle of Attack)")
    angle_of_attack = st.select_slider(
        "AoA (°)",
        options=AOA_LIST,
        value=5,
        help="Aracın gövde ekseni ile gelen akış arasındaki açı.",
    )

    st.markdown("---")
    st.markdown("#### Türbülans Modeli")
    st.info("k-ω SST (Shear Stress Transport)", icon="🌀")

    st.markdown("---")
    st.caption(
        "Bu parametreler, aşağıdaki grafik ve görselleştirmeleri "
        "gerçek zamanlı olarak günceller."
    )


# ==============================================================================
# 3. HERO / GİRİŞ BÖLÜMÜ
# ==============================================================================
st.markdown(
    f"""
    <div class="hero-box">
        <div class="hero-title">🚀 Kurgusal Hava Araçlarının Aerodinamik Analizi</div>
        <div class="hero-subtitle">
            Marvel Evreni'ndeki hava araçlarının (Quinjet, Iron Man Zırhı) CFD tabanlı
            aerodinamik performans değerlendirmesi — Havacılık ve Uzay Mühendisliği
            Portfolyo Projesi
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        '<div class="metric-card"><h3>Fusion 360</h3><p>CAD Modelleme</p></div>',
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        '<div class="metric-card"><h3>SimScale</h3><p>Bulut Tabanlı CFD Çözücü</p></div>',
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        '<div class="metric-card"><h3>k-ω SST</h3><p>Türbülans Modeli</p></div>',
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        '<div class="metric-card"><h3>Python + Plotly</h3><p>Veri Görselleştirme</p></div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

with st.expander("📘 Proje Amacı ve Metodoloji Hakkında Detaylı Bilgi", expanded=False):
    st.markdown(
        """
        **Amaç:** Bu proje, popüler kurguda yer alan hava araçlarının dış hatlarını
        gerçek mühendislik prensipleriyle değerlendirerek, temel aerodinamik
        kavramların (sürükleme, kaldırma, akış ayrılması, basınç dağılımı) somut ve
        ilgi çekici bir bağlamda öğrenilmesini/aktarılmasını amaçlamaktadır.

        **Metodoloji:**
        1. Geometriler Fusion 360'ta referans görsellerden yola çıkılarak 3B olarak
           modellenmiştir.
        2. Modeller SimScale platformuna aktarılarak sanal rüzgar tüneli
           (virtual wind tunnel) ortamı oluşturulmuştur.
        3. Akış çözümü, ayrılmış akışların ve sınır tabaka davranışının doğru
           yakalanması için **k-ω SST** türbülans modeli ile elde edilmiştir.
        4. Farklı hücum açılarında (0°–15°) koşulan simülasyonlardan Cd (sürükleme)
           ve Cl (kaldırma) katsayıları çıkarılmıştır.
        5. Sonuçlar, tasarımda yapılan iyileştirmelerin (örn. winglet eklenmesi)
           etkisini ölçmek amacıyla karşılaştırmalı olarak analiz edilmiştir.

        **Temel Bulgular (Özet):** İyileştirilmiş tasarımlar, orijinal kurgusal
        geometrilere kıyasla sürükleme katsayısında azalma ve L/D oranında belirgin
        bir artış göstermiştir (detaylar aşağıdaki karşılaştırma tablosunda).
        """
    )

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ==============================================================================
# 4. VERİ GÖRSELLEŞTİRME - Cd / Cl GRAFİKLERİ
# ==============================================================================
st.markdown(f"## 📊 {aircraft_choice} — Aerodinamik Katsayı Analizi")
st.caption(
    f"Seçilen koşullar: Akış Hızı ≈ {flow_speed:.1f} m/s (Mach {mach_display:.2f}) "
    f"| Hücum Açısı: {angle_of_attack}°"
)

sim_df = get_simulation_data(aircraft_choice)

graph_col1, graph_col2 = st.columns(2)

with graph_col1:
    fig_cd = go.Figure()
    fig_cd.add_trace(
        go.Scatter(
            x=sim_df["AoA"], y=sim_df["Cd"],
            mode="lines+markers",
            name="Cd",
            line=dict(color="#ef5350", width=3),
            marker=dict(size=9),
        )
    )
    # Seçili AoA'yı vurgula
    selected_row = sim_df[sim_df["AoA"] == angle_of_attack]
    fig_cd.add_trace(
        go.Scatter(
            x=selected_row["AoA"], y=selected_row["Cd"],
            mode="markers",
            marker=dict(size=16, color="#ffee58", line=dict(width=2, color="white")),
            name="Seçili Nokta",
            showlegend=False,
        )
    )
    fig_cd.update_layout(
        title="Hücum Açısına Bağlı Sürükleme Katsayısı (Cd)",
        xaxis_title="Hücum Açısı (°)",
        yaxis_title="Cd",
        template="plotly_dark",
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig_cd, use_container_width=True)

with graph_col2:
    fig_cl = go.Figure()
    fig_cl.add_trace(
        go.Scatter(
            x=sim_df["AoA"], y=sim_df["Cl"],
            mode="lines+markers",
            name="Cl",
            line=dict(color="#42a5f5", width=3),
            marker=dict(size=9),
        )
    )
    fig_cl.add_trace(
        go.Scatter(
            x=selected_row["AoA"], y=selected_row["Cl"],
            mode="markers",
            marker=dict(size=16, color="#ffee58", line=dict(width=2, color="white")),
            name="Seçili Nokta",
            showlegend=False,
        )
    )
    fig_cl.update_layout(
        title="Hücum Açısına Bağlı Kaldırma Katsayısı (Cl)",
        xaxis_title="Hücum Açısı (°)",
        yaxis_title="Cl",
        template="plotly_dark",
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig_cl, use_container_width=True)

# Seçili nokta için anlık metrikler
m1, m2, m3 = st.columns(3)
m1.metric("Cd (Seçili Açı)", f"{selected_row['Cd'].values[0]:.4f}")
m2.metric("Cl (Seçili Açı)", f"{selected_row['Cl'].values[0]:.4f}")
m3.metric("L/D (Verimlilik)", f"{selected_row['L/D'].values[0]:.2f}")

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ==============================================================================
# 5. SİMÜLASYON GÖRSELLEŞTİRMELERİ - BASINÇ HARİTASI & STREAMLINES
# ==============================================================================
st.markdown("## 🌀 CFD Simülasyon Görselleştirmeleri")
st.caption(
    "Aşağıdaki görseller, seçilen hücum açısına karşılık gelen SimScale "
    "simülasyon çıktılarıdır (basınç haritası ve akım çizgileri)."
)

img_col1, img_col2 = st.columns(2)

pressure_path = get_pressure_image_path(aircraft_choice, angle_of_attack)
streamline_path = get_streamline_image_path(aircraft_choice, angle_of_attack)

with img_col1:
    st.markdown("#### Basınç Haritası (Pressure Contour)")
    if os.path.exists(pressure_path):
        st.image(pressure_path, use_container_width=True,
                  caption=f"{aircraft_choice} — AoA {angle_of_attack}° Basınç Dağılımı")
    else:
        st.warning(
            f"Görsel bulunamadı: `{pressure_path}`\n\n"
            "Kendi SimScale basınç haritası render'ınızı bu isimle "
            "`assets/pressure/` klasörüne ekleyin."
        )
        st.image(
            "https://placehold.co/600x400/1b263b/4fc3f7?text=Basinc+Haritasi+Placeholder",
            use_container_width=True,
        )

with img_col2:
    st.markdown("#### Akım Çizgileri (Streamlines)")
    if os.path.exists(streamline_path):
        st.image(streamline_path, use_container_width=True,
                  caption=f"{aircraft_choice} — AoA {angle_of_attack}° Akış Çizgileri")
    else:
        st.warning(
            f"Görsel bulunamadı: `{streamline_path}`\n\n"
            "Kendi SimScale streamline render'ınızı bu isimle "
            "`assets/streamlines/` klasörüne ekleyin."
        )
        st.image(
            "https://placehold.co/600x400/1b263b/42a5f5?text=Streamline+Placeholder",
            use_container_width=True,
        )

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ==============================================================================
# 6. MÜHENDİSLİK YORUMU & TASARIM KARŞILAŞTIRMASI
# ==============================================================================
st.markdown("## 🔧 Tasarım İyileştirme Karşılaştırması")
st.markdown(
    """
    Aşağıdaki tablo, orijinal kurgusal tasarım ile aerodinamik verimliliği artırmak
    amacıyla önerilen iyileştirilmiş tasarımın (ör. winglet eklenmesi, kanat profili
    optimizasyonu) performans katsayılarını karşılaştırmaktadır.
    """
)

comparison_df = get_comparison_data()
st.dataframe(
    comparison_df,
    use_container_width=True,
    hide_index=True,
)

st.markdown(
    """
    <div class="disclaimer-box">
    💡 <b>Mühendislik Yorumu:</b> Winglet eklenmesi, kanat ucu girdaplarının (wingtip
    vortices) neden olduğu indüklenmiş sürüklemeyi azaltarak L/D oranında belirgin bir
    iyileşme sağlamıştır. Bu, ticari uçaklarda da yaygın olarak kullanılan bir
    aerodinamik optimizasyon tekniğidir ve kurgusal tasarımlara uygulandığında dahi
    benzer fiziksel prensiplerin geçerli olduğunu göstermektedir.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ==============================================================================
# 7. DOKÜMANTASYON & İNDİRME
# ==============================================================================
st.markdown("## 📄 Teknik Rapor ve Kaynak Kod")

doc_col1, doc_col2 = st.columns(2)

with doc_col1:
    report_path = "technical_report.pdf"
    if os.path.exists(report_path):
        with open(report_path, "rb") as f:
            st.download_button(
                label="📥 Teknik Araştırma Raporunu İndir (PDF)",
                data=f,
                file_name="technical_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    else:
        st.button(
            "📥 Teknik Araştırma Raporunu İndir (PDF)",
            disabled=True,
            use_container_width=True,
            help="'technical_report.pdf' dosyasını proje kök dizinine ekleyin.",
        )
        st.caption(
            "⚠️ `technical_report.pdf` bulunamadı. Kendi raporunuzu proje kök "
            "dizinine bu isimle ekleyin."
        )

with doc_col2:
    st.link_button(
        "💻 GitHub Reposunu Görüntüle",
        url="https://github.com/kullanici-adiniz/proje-reponuz",
        use_container_width=True,
    )
    st.caption("⚠️ Yukarıdaki linki kendi GitHub repo adresinizle güncelleyin.")

st.markdown("---")
st.caption(
    "Bu dashboard, üniversite başvuru portfolyosu kapsamında hazırlanmış bir "
    "Havacılık ve Uzay Mühendisliği projesidir. Analiz edilen geometriler kurgusal "
    "karakterlere aittir; proje, gerçek mühendislik metodolojilerinin eğitim amaçlı "
    "ve yaratıcı bir bağlamda uygulanmasını amaçlamaktadır."
)
