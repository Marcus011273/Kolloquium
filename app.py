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
    "Ein Schüler/eine Schülerin stellt durch sein/ihr Verhalten eine Gefährdung für seine/ihre Mitschüler dar.",
    "Ein Schüler/eine Schülerin erklärt Ihnen, dass er/sie nicht in der Gruppe, sondern lieber alleine arbeiten möchte.",
    "Ein Schüler/eine Schülerin weigert sich, in der Gruppe mit einem/einer bestimmten Mitschüler/Mitschülerin zusammenzuarbeiten.",
    "Ein Junge/ein Mädchen in Ihrer Klasse stört ständig den Unterricht. Auf Ihre Ermahnungen reagiert er/sie mit unangemessenen Kommentaren.",
    "Rhythmisierung ist ein wichtiges Prinzip für die Planung Ihres Unterrichts.",
    "Sie übernehmen eine Klasse mit einem hohen Anteil von Schülerinnen und Schülern mit Migrationshintergrund.",
    "In Ihrer Klasse befinden sich Schülerinnen und Schüler mit unterschiedlichen Lernvoraussetzungen.",
    "In Ihrem Kollegium werden offene und gebundene Unterrichtsformen kontrovers diskutiert.",
    "In Phasen offenen Unterrichts fällt Ihnen ein Schüler/eine Schülerin auf, der/die stets Aufgaben auswählt, die nicht seinem/ihrem Leistungsvermögen entsprechen.",
    "In Ihrer Klasse ist ein Schüler/eine Schülerin, der/die die Hausaufgaben unvollständig oder überhaupt nicht erledigt.",
    "Sie stellen sich auf ein schwieriges Elterngespräch ein.",
    "Lernstandserhebungen und Lernzielkontrollen sind Grundlage für Ihre weitere Unterrichtsplanung."
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






