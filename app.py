import io
import streamlit as st
from pydub import AudioSegment

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
        with st.spinner("Conversione in corso..."):
            try:
                # Forza l'estensione di input per evitare errori di lettura dello stream
                audio = AudioSegment.from_file(uploaded_file, format=input_ext)

                output_buffer = io.BytesIO()
                audio.export(output_buffer, format=target_format)
                
                base_name = uploaded_file.name.rsplit(".", 1)[0]
                
                # Salva il risultato nella sessione per evitare che il bottone sparisca
                st.session_state["converted_bytes"] = output_buffer.getvalue()
                st.session_state["new_filename"] = f"{base_name}.{target_format}"
                st.session_state["target_format"] = target_format
                
                st.success("Conversione completata con successo!")
            except Exception as e:
                st.error(f"Errore durante la conversione: {str(e)}")

    # Mostra il bottone di download fuori dall'if del pulsante di conversione
    if "converted_bytes" in st.session_state:
        mime_type = "audio/mpeg" if st.session_state["target_format"] == "mp3" else f"audio/{st.session_state['target_format']}"
        
        st.download_button(
            label=f"📥 Scarica {st.session_state['new_filename']}",
            data=st.session_state["converted_bytes"],
            file_name=st.session_state["new_filename"],
            mime=mime_type
        )
