import io
import streamlit as st
from pydub import AudioSegment

st.set_page_config(page_title="Convertitore Audio Online", page_icon="🎵", layout="centered")

st.title("🎵 Convertitore Audio Multiformato")
st.write("Carica un file audio, seleziona il formato di destinazione e scarica il file convertito.")

# Formati audio supportati in input
SUPPORTED_INPUTS = ["wav", "mp3", "aiff", "aif", "ogg", "flac", "m4a", "wma", "aac"]
# Formati di output selezionabili
SUPPORTED_OUTPUTS = ["mp3", "wav", "aiff", "flac", "ogg"]

uploaded_file = st.file_uploader("Carica il tuo file audio:", type=SUPPORTED_INPUTS)

if uploaded_file is not None:
    input_ext = uploaded_file.name.split(".")[-1].lower()
    st.success(f"File caricato correttamente: **{uploaded_file.name}**")

    # Seleziona il formato di destinazione
    target_format = st.selectbox("Seleziona il formato di output:", SUPPORTED_OUTPUTS)

    if st.button("Converti Ora"):
        with st.spinner("Conversione in corso..."):
            try:
                # Carica l'audio tramite Pydub
                audio = AudioSegment.from_file(uploaded_file)

                # Export del file in memoria (BytesIO)
                output_buffer = io.BytesIO()
                audio.export(output_buffer, format=target_format)
                output_buffer.seek(0)

                # Preparazione nome file di output
                base_name = uploaded_file.name.rsplit(".", 1)[0]
                new_filename = f"{base_name}.{target_format}"

                st.success("Conversione completata con successo!")
                
                # Bottone di download
                st.download_button(
                    label=f"📥 Scarica {new_filename}",
                    data=output_buffer,
                    file_name=new_filename,
                    mime=f"audio/{target_format}"
                )
            except Exception as e:
                st.error(f"Errore durante la conversione: {str(e)}")
