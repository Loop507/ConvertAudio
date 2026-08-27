import io
import os
import tempfile
import subprocess
import streamlit as st

st.set_page_config(page_title="Convertitore Audio Online", page_icon="🎵", layout="centered")

st.title("🎵 Convertitore Audio Multiformato")
st.write("Carica un file audio, seleziona il formato di destinazione e scarica il file convertito.")

SUPPORTED_INPUTS = ["wav", "mp3", "aiff", "aif", "ogg", "flac", "m4a", "wma", "aac"]
SUPPORTED_OUTPUTS = ["mp3", "wav", "aiff", "flac", "ogg"]

uploaded_file = st.file_uploader("Carica il tuo file audio:", type=SUPPORTED_INPUTS)

if uploaded_file is not None:
    input_ext = uploaded_file.name.split(".")[-1].lower()
    st.success(f"File caricato correttamente: **{uploaded_file.name}**")

    target_format = st.selectbox("Seleziona il formato di output:", SUPPORTED_OUTPUTS)

    if st.button("Converti Ora"):
        with st.spinner("Conversione in corso con FFmpeg..."):
            try:
                # Crea file temporanei su disco per far lavorare FFmpeg
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{input_ext}") as tmp_in:
                    tmp_in.write(uploaded_file.read())
                    tmp_in_path = tmp_in.name

                tmp_out_path = f"{tmp_in_path}_converted.{target_format}"

                # Esegue FFmpeg direttamente da sistema operativo
                cmd = ["ffmpeg", "-y", "-i", tmp_in_path, tmp_out_path]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if result.returncode != 0:
                    raise Exception(f"Errore FFmpeg: {result.stderr}")

                # Leggi il file convertito in memoria
                with open(tmp_out_path, "rb") as f:
                    converted_bytes = f.read()

                # Pulizia dei file temporanei su disco
                os.remove(tmp_in_path)
                os.remove(tmp_out_path)

                base_name = uploaded_file.name.rsplit(".", 1)[0]
                st.session_state["converted_bytes"] = converted_bytes
                st.session_state["new_filename"] = f"{base_name}.{target_format}"
                st.session_state["target_format"] = target_format

                st.success("Conversione completata con successo!")
            except Exception as e:
                st.error(f"Errore durante la conversione: {str(e)}")

if "converted_bytes" in st.session_state:
    mime_type = "audio/mpeg" if st.session_state["target_format"] == "mp3" else f"audio/{st.session_state['target_format']}"
    
    st.download_button(
        label=f"📥 Scarica {st.session_state['new_filename']}",
        data=st.session_state["converted_bytes"],
        file_name=st.session_state["new_filename"],
        mime=mime_type
    )
