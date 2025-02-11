import streamlit as st
import pandas as pd
import os
import json
from apify_client import ApifyClient
from datetime import datetime, timedelta
from openai import OpenAI
from io import BytesIO

# Path folder untuk token
APIFY_TOKEN_FOLDER = "./Token Apify"
GPT_TOKEN_FOLDER = "./Token GPT"

# Fungsi memuat token dari file JSON
def load_tokens(folder_path):
    tokens = {}
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "r") as file:
                data = json.load(file)
                tokens[filename] = data["api_key"]
    return tokens

# Muat token Apify dan GPT
apify_tokens = load_tokens(APIFY_TOKEN_FOLDER)
gpt_tokens = load_tokens(GPT_TOKEN_FOLDER)

# Sidebar untuk memilih token
st.sidebar.title("Pengaturan Token")
selected_apify_token_file = st.sidebar.selectbox("Pilih Token Apify", list(apify_tokens.keys()))
selected_gpt_token_file = st.sidebar.selectbox("Pilih Token AI", list(gpt_tokens.keys()))

# Token yang dipilih
apify_token = apify_tokens[selected_apify_token_file]
gpt_token = gpt_tokens[selected_gpt_token_file]

st.sidebar.markdown(
    "⚠️ **Jika terjadi error atau limit token, coba ganti token yang dipilih di atas.**"
)

# Inisialisasi klien OpenAI dan Apify
client_apify = ApifyClient(apify_token)
client_gpt = OpenAI(api_key=gpt_token)

# Fungsi untuk scraping dan analisis
def scrape_and_analyze():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    run_input = {
        "username": ["infokejadian_semarang", "infokejadian_genuk", "infokejadiansemarang.new",
                     "infokejadiansemarang_atas", "infokriminalsemarang", "relawangabungansemarang",
                     "informasiseputarsemarang", "hangoutsemarang"],
        "resultsLimit": 100,
        "onlyPostsNewerThan": yesterday,
        "skipPinnedPosts": True
    }

    # Jalankan Apify actor
    run = client_apify.actor("nH2AHrwxeTRJoN5hX").call(run_input=run_input)

    # Ambil hasil scraping
    data_items = [item for item in client_apify.dataset(run["defaultDatasetId"]).iterate_items()]
    df = pd.DataFrame(data_items)

    if not df.empty:
        df = df[['ownerUsername', 'caption', 'url', 'commentsCount', 'likesCount', 'timestamp']]
        df = df.sort_values(by='timestamp', ascending=False)

        # Gabungkan caption
        all_captions = " ".join(df['caption'].dropna())
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        data_summary = df[['ownerUsername', 'url', 'timestamp', 'caption']].dropna()

        prompt = f"""
        Analisislah data caption berikut yang dikumpulkan dari akun-akun Instagram tentang kejadian di Semarang:
        {all_captions}

        Data pendukung untuk analisis tersedia dalam tabel berikut:
        {data_summary.to_string(index=False)}

        Tugas Anda adalah:
        1. Identifikasi beberapa topik yang paling sering dibahas.
        2. Pastikan untuk memisahkan konten serius dari konten yang bersifat komedi, satire, atau hoaks.
        3. Berikan ide artikel menarik untuk setiap topik yang valid, berdasarkan caption yang benar-benar relevan.
        4. Jelaskan alasan pemilihan topik dan dukungan datanya (berapa jumlah caption terkait, dari akun mana saja).
        5. Sertakan contoh judul ,pengantar singkat artikel, dan bagan/struktur penulisan untuk setiap topik tersebut.
        6. Tampilkan URL dan waktu kejadian (dalam format lengkap beserta jam) yang mendukung setiap topik tersebut, pastikan semua postingan yang mendukung ditampilkan.
        Berikan jawaban dalam bahasa Indonesia yang profesional dan lengkap.
        Pada hasilnya tidak perlu diberi bold maupun header tapi susun dengan rapih.
        """

        completion = client_gpt.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        hasil_analisis = completion.choices[0].message.content
        return df, hasil_analisis
    else:
        return pd.DataFrame(), "Tidak ada data yang diperoleh dari proses scraping."

# UI Streamlit
st.title("Analisis Kejadian Instagram")

st.markdown("""
Pantau kejadian terkini di Semarang dengan mudah menggunakan aplikasi ini. Pastikan Anda mengganti token di bagian samping jika mengalami masalah.

#### Cara Menggunakan 🚀
1. Pilih token Apify dan AI di sidebar.
2. Klik tombol "Mulai Scraping dan Analisis".
3. Lihat hasil analisis dan ekspor data sesuai kebutuhan.

---
""")

if st.button("Mulai Scraping dan Analisis"):
    with st.spinner("Sedang melakukan scraping dan analisis data... Mohon tunggu..."):
        df_result, analysis_result = scrape_and_analyze()

    if not df_result.empty:
        st.subheader("📑 Data Hasil Scraping")
        st.dataframe(df_result)

        # Ekspor data ke dalam format Excel
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_result.to_excel(writer, index=False)
        excel_data = excel_buffer.getvalue()

        # Tombol unduh data Excel
        st.download_button(
            label="Unduh Data dalam Format Excel",
            data=excel_data,
            file_name="hasil_scraping.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


    if analysis_result:
        st.subheader("📋 Hasil Analisis")
        st.write(analysis_result)
    else:
        st.error("Tidak ada data yang diperoleh dari proses scraping.")

