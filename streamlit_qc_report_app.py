import os
import tempfile
import streamlit as st
from dotenv import load_dotenv
import pdfplumber
from openai import AzureOpenAI

# -----------------------------------------------------------------------------
# 1) Ortam Değişkenlerini Yükle ------------------------------------------------
# -----------------------------------------------------------------------------
load_dotenv()

# -----------------------------------------------------------------------------
# 2) Sayfa Konfigürasyonu & Renk Paleti ----------------------------------------
# -----------------------------------------------------------------------------
PRIMARY      = "#008fe5"   # Buton ve vurgu – daha açık mavi
SIDEBAR_BG   = "#1976d2"   # Sidebar arka plan – açık mavi
BG_COLOR     = "#2d3134"   # Ana arka plan (açık gri)
TEXT_DARK    = "#003366"   # Başlık koyu lacivert

st.set_page_config(
    page_title="Netaş Denetim Rapor Analiz",
    page_icon="netas.png",
    layout="wide",
)

CUSTOM_CSS = f"""
<style>
/************************** Genel Arka Plan ***********************************/
.reportview-container {{ background-color: {BG_COLOR}; }}

/************************** Sidebar *******************************************/
[data-testid="stSidebar"] > div:first-child {{ background-color: {SIDEBAR_BG}; }}
/* Sidebar’daki TÜM yazıları beyaz yap */
[data-testid="stSidebar"] * {{ color:#ffffff !important; }}

/************************** Başlıklar *****************************************/
h1, h2, h3, h4 {{ color: {TEXT_DARK} !important; }}

/************************** Butonlar ******************************************/
.stButton>button {{
    background-color: {PRIMARY};
    color: #ffffff !important;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    border: none;
}}
.stButton>button:hover {{ filter: brightness(1.05); }}

/************************** TextArea ******************************************/
.stTextArea textarea {{ background-color:#ffffff; color:#333333; }}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3) Yardımcı Fonksiyonlar -----------------------------------------------------
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def extract_text(path: str) -> str:
    """PDF veya TXT dosyasından metin çıkar."""
    if path.lower().endswith(".pdf"):
        with pdfplumber.open(path) as pdf:
            return "\n\n".join(page.extract_text() or "" for page in pdf.pages)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@st.cache_resource(show_spinner=False)
def get_client() -> AzureOpenAI:
    """Azure OpenAI istemcisini döndürür."""
    return AzureOpenAI(
        api_key       = os.getenv("AZURE_OPENAI_KEY"),
        api_version   = "2024-12-01-preview",
        azure_endpoint= os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

def analyse_report(text: str) -> str:
    client = get_client()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a Quality Assurance Director with 15 years of experience, "
                "a Six Sigma Master Black Belt, and an ISO 9001 Lead Auditor. "
                "Provide concise, data‑driven, and actionable recommendations in Turkish."
            ),
        },
        {
            "role": "user",
            "content": (
                "Aşağıdaki haftalık denetim raporunu incele ve:\n"
                "1) 3 maddede kısa özet\n"
                "2) 2 kritik problem\n"
                "3) 3 aksiyon önerisi\n\n" + text
            ),
        },
    ]
    resp = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=800,
        temperature=0.0,
        top_p=1.0,
    )
    return resp.choices[0].message.content.strip()

def ask_about_report(text: str, question: str) -> str:
    client = get_client()
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Answer in Turkish."},
        {"role": "user",   "content": f"Rapor:\n\n{text}\n\nSORU: {question}"},
    ]
    resp = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=600,
        temperature=0.0,
        top_p=1.0,
    )
    return resp.choices[0].message.content.strip()

# -----------------------------------------------------------------------------
# 4) Üst Logo & Başlık ---------------------------------------------------------
# -----------------------------------------------------------------------------
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("netas.png", width=200)
with col_title:
    st.title("Denetim Rapor Analiz Asistanı 📊")
    st.subheader("Netaş R&D Innovation Group için özel arayüz")

# -----------------------------------------------------------------------------
# 5) Sidebar – Dosya & Mod Seçimi ---------------------------------------------
# -----------------------------------------------------------------------------
st.sidebar.header("Ayarlar")
uploaded_file = st.sidebar.file_uploader("Rapor seç (.pdf /.txt)", type=["pdf", "txt"])
mode = st.sidebar.radio("Mod Seç", ["Özet + Aksiyon", "Soru‑Cevap"], horizontal=False)

# -----------------------------------------------------------------------------
# 6) İş Akışı ------------------------------------------------------------------
# -----------------------------------------------------------------------------
if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    text = extract_text(tmp_path)
    if not text.strip():
        st.error("❗Dosyadan metin alınamadı. PDF taranmış görüntü olabilir veya boş.")
    else:
        if mode == "Özet + Aksiyon":
            if st.sidebar.button("Analiz Et 🧐"):
                with st.spinner("Rapor analiz ediliyor..."):
                    result = analyse_report(text)
                st.text_area("GPT‑4 Özet & Aksiyonlar", value=result, height=420)
        else:
            question = st.sidebar.text_input("Sorunuzu yazın")
            if st.sidebar.button("Sor ✔️") and question:
                with st.spinner("Yanıt aranıyor..."):
                    answer = ask_about_report(text, question)
                st.text_area("Cevap", value=answer, height=420)
else:
    st.info("📄 Rapor dosyanızı yükleyin veya sürükleyip bırakın.")
