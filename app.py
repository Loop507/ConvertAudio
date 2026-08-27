import io
import os
import tempfile
import subprocess
import streamlit as st

st.set_page_config(page_title="Convertitore & Editor Audio", page_icon="🎵", layout="centered")

st.title("🎵 Convertitore Audio & Estrazione da Video")
st.write("Carica file audio o video, regola la qualità, rimuovi il silenzio ed esporta il tuo file.")

SUPPORTED_INPUTS = [
    "wav", "mp3", "aiff", "aif", "ogg", "flac", "m4a", "wma", "aac",
    "mp4", "mkv", "avi", "mov", "webm"
]
SUPPORTED_OUTPUTS = ["mp3", "wav", "flac", "aac", "ogg"]
BITRATES = ["128k", "192k", "256k", "320k"]

uploaded_file = st.file_uploader("Carica un file audio o video:", type=SUPPORTED_INPUTS)

if uploaded_file is not None:
    input_ext = uploaded_file.name.split(".")[-1].lower()
    st.success(f"File caricato correttamente: **{uploaded_file.name}**")

    col1, col2 = st.columns(2)
    with col1:
        target_format = st.selectbox("Formato di destinazione:", SUPPORTED_OUTPUTS)
    with col2:
        bitrate = st.selectbox("Qualità / Bitrate:", BITRATES, index=3)

    st.markdown("---")
    st.subheader("⚙️ Opzioni di Editing")

    # Nuova funzione: Rimozione Automatica Silenzio
    remove_silence = st.checkbox("🔇 Rimuovi vuoto/silenzio automatico (inizio e fine)")

    # Taglio Manuale Opzionale
    enable_trim = st.checkbox("✂️ Taglia traccia manualmente (per secondi)")
    start_time, end_time = 0, 0
    if enable_trim:
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            start_time = st.number_input("Inizio (secondi):", min_value=0, value=0, step=1)
        with col_t2:
            end_time = st.number_input("Fine (secondi, 0 = disattivato):", min_value=0, value=0, step=1)

    if st.button("Converti ed Elabora"):
        with st.spinner("Elaborazione in corso con FFmpeg..."):
            try:
                # Scrittura del file temporaneo di input
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{input_ext}") as tmp_in:
                    tmp_in.write(uploaded_file.read())
                    tmp_in_path = tmp_in.name

                tmp_out_path = f"{tmp_in_path}_converted.{target_format}"

                cmd = ["ffmpeg", "-y"]

                # Taglio manuale di inizio
                if enable_trim and start_time > 0:
                    cmd.extend(["-ss", str(start_time)])

                cmd.extend(["-i", tmp_in_path])

                # Taglio manuale di fine
                if enable_trim and end_time > start_time:
                    cmd.extend(["-to", str(end_time)])

                # Elimina la traccia video se l'input è un file video
                cmd.append("-vn")

                # Costruzione dei filtri audio
                af_filters = []

                if remove_silence:
                    # Rimuove il silenzio iniziale (-45dB), inverte l'audio, rimuove il silenzio finale e reinverte
                    silence_filter = (
                        "silenceremove=start_periods=1:start_threshold=-45dB,"
                        "areverse,"
                        "silenceremove=start_periods=1:start_threshold=-45dB,"
                        "areverse"
                    )
                    af_filters.append(silence_filter)

                if af_filters:
                    cmd.extend(["-af", ",".join(af_filters)])

                # Imposta bitrate per MP3, AAC e OGG
                if target_format in ["mp3", "aac", "ogg"]:
                    cmd.extend(["-b:a", bitrate])

                cmd.append(tmp_out_path)

                # Esecuzione del processo FFmpeg
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if result.returncode != 0:
                    raise Exception(f"Errore FFmpeg: {result.stderr}")

                # Lettura file finale
                with open(tmp_out_path, "rb") as f:
                    converted_bytes = f.read()

                # Pulizia file temporanei
                os.remove(tmp_in_path)
                os.remove(tmp_out_path)

                base_name = uploaded_file.name.rsplit(".", 1)[0]
                st.session_state["converted_bytes"] = converted_bytes
                st.session_state["new_filename"] = f"{base_name}_converted.{target_format}"
                st.session_state["target_format"] = target_format

                st.success("Elaborazione completata con successo!")
            except Exception as e:
                st.error(f"Errore durante l'elaborazione: {str(e)}")

# Bottone Download persistente
if "converted_bytes" in st.session_state:
    mime_type = "audio/mpeg" if st.session_state["target_format"] == "mp3" else f"audio/{st.session_state['target_format']}"
    
    st.download_button(
        label=f"📥 Scarica {st.session_state['new_filename']}",
        data=st.session_state["converted_bytes"],
        file_name=st.session_state["new_filename"],
        mime=mime_type
    )
