import io
import os
import tempfile
import subprocess
import zipfile
import streamlit as st

st.set_page_config(page_title="Batch Audio Studio Pro", page_icon="🎵", layout="centered")

st.title("🎵 Batch Audio Studio Pro")
st.write("Converti, normalizza il volume, regola sample rate/bit-depth e modifica i metadati.")

SUPPORTED_INPUTS = [
    "wav", "mp3", "aiff", "aif", "ogg", "flac", "m4a", "wma", "aac",
    "mp4", "mkv", "avi", "mov", "webm"
]
SUPPORTED_OUTPUTS = ["mp3", "wav", "flac", "aac", "ogg"]
BITRATES = ["128k", "192k", "256k", "320k"]
SAMPLE_RATES = {"Originale": None, "44.1 kHz (CD)": "44100", "48 kHz (Video/Pro)": "48000", "96 kHz (Hi-Res)": "96000"}
BIT_DEPTHS = {"16-bit": "pcm_s16le", "24-bit": "pcm_s24le", "32-bit float": "pcm_f32le"}

uploaded_files = st.file_uploader("Carica uno o più file audio/video:", type=SUPPORTED_INPUTS, accept_multiple_files=True)

if uploaded_files:
    is_single = len(uploaded_files) == 1
    st.info(f"File caricati: **{len(uploaded_files)}**")

    st.markdown("---")
    st.subheader("⚙️ Formato & Qualità")

    col1, col2 = st.columns(2)
    with col1:
        target_format = st.selectbox("Formato di destinazione:", SUPPORTED_OUTPUTS)
    with col2:
        if target_format in ["mp3", "aac", "ogg"]:
            bitrate = st.selectbox("Bitrate:", BITRATES, index=3)
        else:
            bitrate = None
            st.caption("*(Formato lossless: bitrate non richiesto)*")

    col3, col4 = st.columns(2)
    with col3:
        sr_choice = st.selectbox("Sample Rate:", list(SAMPLE_RATES.keys()))
        sample_rate = SAMPLE_RATES[sr_choice]
    with col4:
        if target_format == "wav":
            bd_choice = st.selectbox("Profondità di Bit (WAV):", list(BIT_DEPTHS.keys()), index=0)
            codec_wav = BIT_DEPTHS[bd_choice]
        else:
            codec_wav = None

    st.markdown("---")
    st.subheader("🎛️ Moduli di Elaborazione Audio")

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        norm_volume = st.checkbox("🔊 Normalizza Volume (-14 LUFS Streaming)")
    with col_opt2:
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

    if st.button("🚀 Avvia Elaborazione"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            processed_files = []

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

                cmd = ["ffmpeg", "-y", "-i", tmp_in_path, "-vn"]

                # Costruzione filtri audio
                af_filters = []
                if remove_silence:
                    af_filters.append(
                        "silenceremove=start_periods=1:start_threshold=-45dB,"
                        "areverse,"
                        "silenceremove=start_periods=1:start_threshold=-45dB,"
                        "areverse"
                    )
                if norm_volume:
                    af_filters.append("loudnorm=I=-14:LRA=11:TP=-1.5")

                if af_filters:
                    cmd.extend(["-af", ",".join(af_filters)])

                # Sample Rate
                if sample_rate:
                    cmd.extend(["-ar", sample_rate])

                # Bit-depth WAV
                if target_format == "wav" and codec_wav:
                    cmd.extend(["-c:a", codec_wav])

                # Metadati ID3
                cmd.extend(["-metadata", f"title={track_title}"])
                if meta_artist:
                    cmd.extend(["-metadata", f"artist={meta_artist}"])
                if meta_album:
                    cmd.extend(["-metadata", f"album={meta_album}"])
                if meta_year:
                    cmd.extend(["-metadata", f"date={meta_year}"])
                if meta_genre:
                    cmd.extend(["-metadata", f"genre={meta_genre}"])
                cmd.extend(["-metadata", f"track={idx}/{len(uploaded_files)}"])

                # Bitrate
                if target_format in ["mp3", "aac", "ogg"] and bitrate:
                    cmd.extend(["-b:a", bitrate])

                cmd.append(tmp_out_path)

                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode != 0:
                    raise Exception(f"Errore su {uploaded_file.name}: {result.stderr}")

                with open(tmp_out_path, "rb") as f:
                    file_bytes = f.read()

                processed_files.append((new_filename, file_bytes))

                os.remove(tmp_in_path)
                os.remove(tmp_out_path)

                progress_bar.progress(idx / len(uploaded_files))

            status_text.text("Elaborazione completata!")

            # Gestione Download Intelligente
            if is_single:
                st.session_state["result_single"] = (processed_files[0][0], processed_files[0][1], target_format)
                st.session_state.pop("result_zip", None)
            else:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, data in processed_files:
                        zip_file.writestr(filename, data)
                zip_buffer.seek(0)
                st.session_state["result_zip"] = (f"audio_convertiti_{target_format}.zip", zip_buffer.getvalue())
                st.session_state.pop("result_single", None)

            st.success("Tutti i file sono stati elaborati correttamente!")

        except Exception as e:
            st.error(f"Si è verificato un errore: {str(e)}")

# Area Output: Player Anteprima per file singolo o ZIP per file multipli
if "result_single" in st.session_state:
    filename, data, fmt = st.session_state["result_single"]
    st.markdown("---")
    st.subheader("🎧 Anteprima & Download")
    st.audio(data, format=f"audio/{fmt}")
    
    mime_type = "audio/mpeg" if fmt == "mp3" else f"audio/{fmt}"
    st.download_button(
        label=f"📥 Scarica {filename}",
        data=data,
        file_name=filename,
        mime=mime_type
    )

elif "result_zip" in st.session_state:
    zip_name, zip_bytes = st.session_state["result_zip"]
    st.markdown("---")
    st.subheader("📦 Download Archivio")
    st.download_button(
        label=f"📦 Scarica Pacchetto ZIP ({zip_name})",
        data=zip_bytes,
        file_name=zip_name,
        mime="application/zip"
    )
