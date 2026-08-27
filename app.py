import io
import os
import tempfile
import subprocess
import zipfile
import streamlit as st

st.set_page_config(page_title="Batch Audio Converter & Tag Editor", page_icon="🎵", layout="centered")

st.title("🎵 Conversione Multipla, Rinomina e Metadati")
st.write("Carica più file WAV, imposta i metadati, la struttura dei nomi e scarica l'archivio ZIP convertito.")

SUPPORTED_OUTPUTS = ["mp3", "wav", "flac", "aac", "ogg"]
BITRATES = ["128k", "192k", "256k", "320k"]

# Caricamento multiplo dei file WAV
uploaded_files = st.file_uploader("Carica i tuoi file WAV:", type=["wav"], accept_multiple_files=True)

if uploaded_files:
    st.info(f"File caricati: **{len(uploaded_files)}**")

    st.markdown("---")
    st.subheader("⚙️ Configurazione Conversione & Rinomina")

    col1, col2 = st.columns(2)
    with col1:
        target_format = st.selectbox("Formato di destinazione:", SUPPORTED_OUTPUTS)
    with col2:
        bitrate = st.selectbox("Qualità / Bitrate:", BITRATES, index=3)

    # Opzioni di Rinomina
    st.markdown("**Rinomina File**")
    rename_option = st.radio(
        "Scegli lo schema per i nomi file:",
        ["Mantieni nome originale", "Personalizzato con numerazione (es. Traccia_01)"]
    )
    
    custom_prefix = "Traccia"
    if rename_option == "Personalizzato con numerazione (es. Traccia_01)":
        custom_prefix = st.text_input("Prefisso nome file:", value="Brano")

    # Opzioni Metadati ID3
    st.markdown("---")
    st.subheader("🏷️ Tag Metadati (ID3)")
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        meta_artist = st.text_input("Artista:", placeholder="Es. Mario Rossi")
        meta_album = st.text_input("Album:", placeholder="Es. Il Mio Album")
    with col_m2:
        meta_year = st.text_input("Anno:", placeholder="Es. 2026")
        meta_genre = st.text_input("Genere:", placeholder="Es. Techno / Ambient")

    if st.button("Converti e Scarica ZIP"):
        with st.spinner("Elaborazione batch in corso..."):
            try:
                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for idx, uploaded_file in enumerate(uploaded_files, start=1):
                        
                        # Definizione nuovo nome file
                        if rename_option == "Mantieni nome originale":
                            base_name = uploaded_file.name.rsplit(".", 1)[0]
                            new_filename = f"{base_name}.{target_format}"
                            track_title = base_name
                        else:
                            new_filename = f"{custom_prefix}_{idx:02d}.{target_format}"
                            track_title = f"{custom_prefix} {idx:02d}"

                        # Scrittura input temporaneo
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_in:
                            tmp_in.write(uploaded_file.read())
                            tmp_in_path = tmp_in.name

                        tmp_out_path = f"{tmp_in_path}_out.{target_format}"

                        # Costruzione comando FFmpeg con metadati
                        cmd = ["ffmpeg", "-y", "-i", tmp_in_path]

                        # Inserimento metadati
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

                        # Bitrate per formati compressi
                        if target_format in ["mp3", "aac", "ogg"]:
                            cmd.extend(["-b:a", bitrate])

                        cmd.append(tmp_out_path)

                        # Esecuzione conversione
                        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        if result.returncode != 0:
                            raise Exception(f"Errore su {uploaded_file.name}: {result.stderr}")

                        # Aggiunta file convertito all'archivio ZIP
                        with open(tmp_out_path, "rb") as f:
                            zip_file.writestr(new_filename, f.read())

                        # Pulizia file temporanei
                        os.remove(tmp_in_path)
                        os.remove(tmp_out_path)

                zip_buffer.seek(0)
                st.session_state["zip_bytes"] = zip_buffer.getvalue()
                st.session_state["zip_name"] = f"audio_convertiti_{target_format}.zip"

                st.success(f"Tutti i {len(uploaded_files)} file sono stati convertiti e confezionati nello ZIP!")

            except Exception as e:
                st.error(f"Si è verificato un errore: {str(e)}")

# Bottone Download ZIP
if "zip_bytes" in st.session_state:
    st.download_button(
        label=f"📦 Scarica Pacchetto ZIP ({st.session_state['zip_name']})",
        data=st.session_state["zip_bytes"],
        file_name=st.session_state["zip_name"],
        mime="application/zip"
    )
