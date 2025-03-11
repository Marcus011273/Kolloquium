import streamlit as st
import random
import os
import speech_recognition as sr
from openai import OpenAI
import io
import re

# 🔒 OpenAI API-Schlüssel laden
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("Fehlender API-Schlüssel! Bitte setze eine Umgebungsvariable OPENAI_API_KEY in Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

# **📌 Einführung und Beschreibung**
st.title("🎓 Dein persönlicher Prüfungsassistent zur Simulation des Kolloquiums")
st.write(
    """
    Das System wählt eine zufällig generierte Prüfungsfrage aus.  
    Du hast dann **30 Minuten Zeit** für die Bearbeitung und kannst deine Lösung **schriftlich** oder **als Audio-Datei** eingeben.  
    Falls du eine Audiodatei hochlädst, wird sie automatisch transkribiert und ausgewertet. Bitte beachte, dass die Transkription und die Auswertung einige Zeit in Anspruch nehmen können. 
    
    **Ich wünsche Ihnen ein erfolgreiches Kolloquium!**  
    
    Marcus Müller
    """
)

# **📌 Fragenpool**
fragenpool = [
    "Durch sein Verhalten bringt ein Schüler oder eine Schülerin seine bzw. ihre Mitschülerinnen und Mitschüler in Gefahr.",
    "Ein Schüler oder eine Schülerin äußert den Wunsch, lieber allein als in der Gruppe zu arbeiten.",
    "Ein Schüler oder eine Schülerin lehnt es ab, mit einer bestimmten Person in der Gruppe zusammenzuarbeiten.",
    "Ein Kind in Ihrer Klasse sorgt wiederholt für Unruhe und reagiert auf Ermahnungen mit unangemessenen Kommentaren.",
    "Eine durchdachte Strukturierung des Unterrichts spielt eine entscheidende Rolle für Ihre Planung.",
    "Sie übernehmen eine Klasse, in der viele Schülerinnen und Schüler einen Migrationshintergrund haben.",
    "Ihre Klasse ist geprägt durch eine große Bandbreite an individuellen Lernvoraussetzungen.",
    "Innerhalb des Kollegiums gibt es unterschiedliche Meinungen zu offenen und gebundenen Unterrichtsformen.",
    "Ihnen fällt auf, dass ein Schüler oder eine Schülerin im offenen Unterricht regelmäßig Aufgaben wählt, die nicht seinem oder ihrem Leistungsniveau entsprechen.",
    "Ein Schüler oder eine Schülerin kommt häufig ohne vollständige oder gar keine Hausaufgaben in den Unterricht.",
    "Sie stehen vor einem anspruchsvollen Gespräch mit Eltern.",
    "Lernstandserhebungen und Lernzielkontrollen helfen Ihnen, den weiteren Unterricht gezielt zu planen."
]

# **📌 Session State für Fragenrotation**
if "verwendete_fragen" not in st.session_state:
    st.session_state["verwendete_fragen"] = []

def neue_frage_ziehen():
    """Zieht eine neue Frage, die noch nicht gestellt wurde."""
    verbleibende_fragen = list(set(fragenpool) - set(st.session_state["verwendete_fragen"]))
    
    if not verbleibende_fragen:  # Falls alle Fragen durch sind, setze zurück
        st.session_state["verwendete_fragen"] = []
        verbleibende_fragen = fragenpool.copy()

    frage = random.choice(verbleibende_fragen)
    st.session_state["verwendete_fragen"].append(frage)
    st.session_state["frage"] = frage

# **Frage generieren**
if st.button("🔄 Zufällige Frage generieren"):
    neue_frage_ziehen()

if "frage" in st.session_state:
    st.markdown("### 📌 **Deine Frage:**")
    st.info(f"**{st.session_state['frage']}**")
    st.write("⏳ Du hast 30 Minuten Zeit zur Vorbereitung. (Oder antworte sofort.)")

    # **Eingabemethode wählen**
    eingabe_modus = st.radio("Wähle deine Eingabemethode:", ("Text", "Audio-Datei hochladen"))

    if eingabe_modus == "Text":
        antwort = st.text_area("✍️ Gib deine Antwort hier ein:", height=300)
        if antwort:
            st.session_state["sprachantwort"] = antwort

    elif eingabe_modus == "Audio-Datei hochladen":
        st.write("🎙️ Lade eine Audiodatei hoch (nur WAV) **(Sprechdauer ca. 10 Minuten)**")

        uploaded_file = st.file_uploader("Datei hochladen", type=["wav"])

        if uploaded_file is not None:
            st.audio(uploaded_file, format="audio/wav")

            audio_bytes = uploaded_file.read()

            recognizer = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio = recognizer.record(source)

            try:
                text = recognizer.recognize_google(audio, language="de-DE")
                st.write("📝 **Transkribierte Antwort:**", text)
                st.session_state["audio_text"] = text
            except sr.UnknownValueError:
                st.write("❌ Konnte die Sprache nicht erkennen.")
            except sr.RequestError:
                st.write("❌ Fehler bei der Spracherkennung.")

# **📊 Antwort analysieren & GPT-4 Feedback generieren**
if st.button("📊 Antwort analysieren"):
    nutzerantwort = st.session_state.get("sprachantwort", st.session_state.get("audio_text", ""))

    if nutzerantwort:
        frage_wörter = re.findall(r"\b\w+\b", st.session_state["frage"].lower())
        relevante_wörter = [wort for wort in frage_wörter if len(wort) > 3]
        antwort_wörter = re.findall(r"\b\w+\b", nutzerantwort.lower())
        fehlende_wörter = [wort for wort in relevante_wörter if wort not in antwort_wörter]

        gpt_prompt = f"""
        **Prüfungsfrage:** {st.session_state['frage']}  
        **Antwort:** {nutzerantwort}  

        **Begriffsprüfung:**  
        - Diese wichtigen Begriffe fehlen in der Antwort: {', '.join(fehlende_wörter)}  

        📏 **Umfang:**  
        - Ist die Antwort angemessen für eine 30-minütige Bearbeitungszeit?  

        📖 **Struktur:**  
        - Ist die Antwort klar gegliedert? (Einleitung, Hauptteil, Schluss)  

        🔬 **Inhaltliche Tiefe & Genauigkeit:**  
        - Sind die wichtigsten Aspekte der Frage abgedeckt?  

        ⚖️ **Argumentation:**  
        - Sind die Argumente fundiert und nachvollziehbar?  

        💡 **Verbesserungsvorschläge:**  
        - Welche Anpassungen würden die Antwort verbessern?  

        🔍 **Mögliche Nachfragen:**  
        - Formuliere zwei anspruchsvolle Nachfragen zur Reflexion der Argumentation.  
        """

        feedback = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": gpt_prompt}],
            max_tokens=1000
        ).choices[0].message.content.strip()

        st.write("### 🔎 Mein Feedback für dich")
        st.markdown(feedback)

    else:
        st.warning("⚠️ Bitte gib eine Antwort ein!")






