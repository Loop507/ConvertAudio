import io
import os
import tempfile
import subprocess
import zipfile
from datetime import datetime
import numpy as np
import librosa
import streamlit as st

st.set_page_config(page_title="Batch Audio Studio Pro", page_icon="🎵", layout="centered")

st.title("🎵 Batch Audio Studio Pro + BPM & Key")
st.write("Converti, analizza il ritmo/tonalità, gestisci i canali e scarica file e report in ZIP.")

SUPPORTED_INPUTS = [
    "wav", "mp3", "aiff", "aif", "ogg", "flac", "m4a", "wma", "aac",
    "mp4", "mkv", "avi", "mov", "webm"
]
SUPPORTED_OUTPUTS = ["mp3", "wav", "flac", "aac", "ogg"]
BITRATES = ["128k", "192k", "256k", "320k"]
SAMPLE_RATES = {"Originale": None, "44.1 kHz (CD)": "44100", "48 kHz (Video/Pro)": "48000"}
CHANNELS = {"Originale": None, "Mono (1 Canale)": "1", "Stereo (2 Canali)": "2"}

# Funzione per analizzare BPM e Tonalità con Librosa
def detect_bpm_and_key(audio_path):
    try:
        # Carica i primi 90 secondi dell'audio per velocizzare l'analisi
        y, sr = librosa.load(audio_path, sr=22050, duration=90)
        
        # Calcolo BPM
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = int(round(float(tempo)))

        # Calcolo Tonalità (Chromagram + Krumhansl-Schmuckler)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_vals = np.mean(chroma, axis=1)
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        # Individua la nota dominante
        key_idx = np.argmax(chroma_vals)
        estimated_key = notes[key_idx]

        return bpm, estimated_key
    except Exception:
        return "N/D", "N/D"

uploaded_files = st.file_uploader("Carica uno o più file audio/video:", type=SUPPORTED_INPUTS, accept_multiple_files=True)

if uploaded_files:
    is_single = len(uploaded_files) == 1
    st.info(f"File caricati: **{len(uploaded_files)}**")

    st.markdown("---")
    st.subheader("⚙️ Formato & Canali Audio")

    col1, col2 = st.columns(2)
    with col1:
        target_format = st.selectbox("Formato di destinazione:", SUPPORTED_OUTPUTS)
    with col2:
        channel_choice = st.selectbox("Canali Audio (Mono/Stereo):", list(CHANNELS.keys()))
        channels = CHANNELS[channel_choice]

    col3, col4 = st.columns(2)
    with col3:
        if target_format in ["mp3", "aac", "ogg"]:
            bitrate = st.selectbox("Bitrate:", BITRATES, index=3)
        else:
            bitrate = None
    with col4:
        sr_choice = st.selectbox("Sample Rate:", list(SAMPLE_RATES.keys()))
        sample_rate = SAMPLE_RATES[sr_choice]

    st.markdown("---")
    st.subheader("🎛️ Moduli di Analisi & Elaborazione")

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        calc_bpm = st.checkbox("🔍 Analizza BPM e Tonalità Musicale", value=True)
    with col_opt2:
        norm_volume = st.checkbox("🔊 Normalizza Volume (-14 LUFS)")

    remove_silence = st.checkbox("🔇 Rimuovi vuoto inizio/fine")

    st.markdown("---")
    st.subheader("🏷️ Tag Metadati (ID3)")

    if not is_single:
        rename_option = st.radio("Schema nomi file:", ["Mantieni nome originale", "Personalizzato (es. Brano_01)"])
        custom_prefix = st.text_input("Prefisso nome:", value="Brano") if rename_option != "Mantieni nome originale" else ""
    else:
        rename_option = "Mantieni nome originale"
        custom_prefix = ""

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        meta_artist = st.text_input("Artista:", placeholder="Es. Mario Rossi")
        meta_album = st.text_input("Album:", placeholder="Es. Il Mio Album")
    with col_m2:
        meta_year = st.text_input("Anno:", placeholder="Es. 2026")
        meta_genre = st.text_input("Genere:", placeholder="Es. Techno / Ambient")

    if st.button("🚀 Avvia Elaborazione & Analisi"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            processed_files = []
            
            report_lines = [
                "==========================================",
                "       REPORT CONVERSIONE & ANALISI       ",
                "==========================================",
                f"Data elaborazione: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Totale file: {len(uploaded_files)}",
                f"Formato Output: {target_format.upper()}",
                "------------------------------------------",
                "DETTAGLIO TRACCE:\n"
            ]

            for idx, uploaded_file in enumerate(uploaded_files, start=1):
                status_text.text(f"Elaborazione traccia {idx} di {len(uploaded_files)}: {uploaded_file.name}")
                
                input_ext = uploaded_file.name.split(".")[-1].lower()

                if is_single or rename_option == "Mantieni nome originale":
                    base_name = uploaded_file.name.rsplit(".", 1)[0]
                    new_filename = f"{base_name}.{target_format}"
                    track_title = base_name
                else:
                    new_filename = f"{custom_prefix}_{idx:02d}.{target_format}"
                    track_title = f"{custom_prefix} {idx:02d}"

                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{input_ext}") as tmp_in:
                    tmp_in.write(uploaded_file.read())
                    tmp_in_path = tmp_in.name

                tmp_out_path = f"{tmp_in_path}_out.{target_format}"

                # Analisi BPM e Key
                bpm_val, key_val = "Disattivato", "Disattivato"
                if calc_bpm:
                    status_text.text(f"Analisi BPM/Tonalità {idx} di {len(uploaded_files)}...")
                    bpm_val, key_val = detect_bpm_and_key(tmp_in_path)

                cmd = ["ffmpeg", "-y", "-i", tmp_in_path, "-vn"]

                if channels:
                    cmd.extend(["-ac", channels])

                af_filters = []
                if remove_silence:
                    af_filters.append("silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse")
                if norm_volume:
                    af_filters.append("loudnorm=I=-14:LRA=11:TP=-1.5")

                if af_filters:
                    cmd.extend(["-af", ",".join(af_filters)])

                if sample_rate:
                    cmd.extend(["-ar", sample_rate])

                cmd.extend(["-metadata", f"title={track_title}"])
                if meta_artist:
                    cmd.extend(["-metadata", f"artist={meta_artist}"])
                if meta_album:
                    cmd.extend(["-metadata", f"album={meta_album}"])
                if meta_year:
                    cmd.extend(["-metadata", f"date={meta_year}"])
                if meta_genre:
                    cmd.extend(["-metadata", f"genre={meta_genre}"])
                
                # Inserisci il BPM nei metadati ufficiali dell'audio
                if calc_bpm and bpm_val != "N/D":
                    cmd.extend(["-metadata", f"bpm={bpm_val}"])

                if target_format in ["mp3", "aac", "ogg"] and bitrate:
                    cmd.extend(["-b:a", bitrate])

                cmd.append(tmp_out_path)

                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode != 0:
                    raise Exception(f"Errore su {uploaded_file.name}: {result.stderr}")

                with open(tmp_out_path, "rb") as f:
                    file_bytes = f.read()

                processed_files.append((new_filename, file_bytes))
                
                report_lines.append(f"Traccia #{idx:02d}: {uploaded_file.name} -> {new_filename} | BPM: {bpm_val} | Tonalità stimata: {key_val}")

                os.remove(tmp_in_path)
                os.remove(tmp_out_path)

                progress_bar.progress(idx / len(uploaded_files))

            status_text.text("Elaborazione e Analisi Completate!")

            report_content = "\n".join(report_lines)

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for filename, data in processed_files:
                    zip_file.writestr(filename, data)
                zip_file.writestr("info_conversione.txt", report_content)

            zip_buffer.seek(0)
            
            if is_single:
                st.session_state["result_single"] = (processed_files[0][0], processed_files[0][1], target_format)
            
            st.session_state["result_zip"] = (f"audio_convertiti_{target_format}.zip", zip_buffer.getvalue(), report_content)

            st.success("Analisi e Conversione completate!")

        except Exception as e:
            st.error(f"Si è verificato un errore: {str(e)}")

# Area Output
if "result_zip" in st.session_state:
    zip_name, zip_bytes, report_txt = st.session_state["result_zip"]
    
    st.markdown("---")
    st.subheader("🎧 Risultati & Download")

    if "result_single" in st.session_state:
        filename, data, fmt = st.session_state["result_single"]
        st.audio(data, format=f"audio/{fmt}")

    st.text_area("📄 Report Analisi (BPM & Key):", report_txt, height=200)

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            label="📦 Scarica ZIP (Audio + info.txt)",
            data=zip_bytes,
            file_name=zip_name,
            mime="application/zip"
        )
    with col_d2:
        st.download_button(
            label="📄 Scarica solo Report TXT",
            data=report_txt,
            file_name="info_conversione.txt",
            mime="text/plain"
        )
