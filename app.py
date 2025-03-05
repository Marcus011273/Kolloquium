import streamlit as st
import random
import os
import time
import speech_recognition as sr
from openai import OpenAI

# OpenAI API-Schlüssel holen
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("Fehlender API-Schlüssel! Bitte setze eine Umgebungsvariable OPENAI_API_KEY.")
    st.stop()

client = OpenAI(api_key=api_key)

# **📌 Einführung und Beschreibung**
st.title("🎓 Dein persönlicher Prüfungsassistent zur Simulation des Kolloquiums")
st.write(
    """
    Das System wählt eine zufällig generierte Prüfungsfrage aus.  
    Du hast dann **30 Minuten Zeit** für die Bearbeitung und kannst deine Lösung **schriftlich** oder **als Audio** eingeben.  
    Falls du dich für die Audioeingabe entscheidest, hast du **maximal 10 Minuten** Zeit zum Sprechen.  
    **Du kannst die Aufnahme jederzeit selbst beenden.**
    """
)

# **📌 Fragenpool mit 12 Fragen**
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
    st.write(f"### 📝 Deine Frage: {st.session_state['frage']}")
    st.write("⏳ Du hast 30 Minuten Zeit zur Vorbereitung. (Oder antworte sofort.)")

    # **Eingabemethode wählen**
    eingabe_modus = st.radio("Wähle deine Eingabemethode:", ("Text", "Audio"))

    if eingabe_modus == "Text":
        antwort = st.text_area("✍️ Gib deine Antwort hier ein:", height=300)
        if antwort:
            st.session_state["sprachantwort"] = antwort

    elif eingabe_modus == "Audio":
        st.write("🎙️ Antwort per Spracheingabe")
        st.write("🔹 **Wenn du fertig bist mit der Spracheingabe, dann klicke auf den Button „Antwort analysieren“.**")

        if "audio_text" not in st.session_state:
            st.session_state["audio_text"] = ""

        if "aufnahme_aktiv" not in st.session_state:
            st.session_state["aufnahme_aktiv"] = False

        if st.button("🎤 Aufnahme starten"):
            st.session_state["aufnahme_aktiv"] = True
            st.session_state["audio_text"] = ""  # Leeren

        if st.session_state["aufnahme_aktiv"]:
            st.write("🎤 **Aufnahme läuft...** (Sprich deine Antwort.)")

            if st.button("🛑 Aufnahme stoppen"):
                st.session_state["aufnahme_aktiv"] = False
                st.write("✅ **Aufnahme manuell beendet.**")

            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                start_time = time.time()
                while time.time() - start_time < 600 and st.session_state["aufnahme_aktiv"]:
                    try:
                        audio = recognizer.listen(source, timeout=None, phrase_time_limit=10)  # Mehrere kurze Segmente
                        transkription = recognizer.recognize_google(audio, language="de-DE")
                        st.session_state["audio_text"] += " " + transkription
                        st.write(f"**Zwischenergebnis:** {st.session_state['audio_text']}")
                    except sr.UnknownValueError:
                        st.write("⚠️ Audio konnte nicht erkannt werden.")
                    except sr.RequestError:
                        st.write("⚠️ Fehler bei der Spracherkennung.")

# **🔍 OpenAI Anfrage-Funktion**
def openai_anfrage(prompt):
    """Sendet die Antwort an OpenAI und gibt die GPT-4 Rückmeldung zurück."""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Fehler bei der OpenAI-Anfrage: {e}"

# **📊 Antwort analysieren & GPT-4 Feedback generieren**
if st.button("📊 Antwort analysieren"):
    nutzerantwort = st.session_state.get("sprachantwort", st.session_state.get("audio_text", ""))

    if nutzerantwort:
        zeichenanzahl = len(nutzerantwort)
        gpt_prompt = f"""
        Hier ist eine Prüfungsfrage, die eine Person in 30 Minuten beantwortet hat:  
        **Frage:** {st.session_state['frage']}  
        **Antwort:** {nutzerantwort}  

        **Bewerte die Antwort nach folgenden Kriterien und gib ein detailliertes Feedback:**  

        **📏 Umfang:**  
        - Die Antwort enthält **{zeichenanzahl} Zeichen**.  
        - Ist das angemessen für eine 30-minütige Bearbeitungszeit? Sollte sie ausführlicher oder präziser sein?  

        **📖 Struktur:**  
        - Ist die Antwort logisch aufgebaut mit Einleitung, Hauptteil und Schluss?  
        - Sind die Gedanken klar verknüpft und gut nachvollziehbar?  

        **🔬 Inhaltliche Tiefe:**  
        - Werden Fachbegriffe und relevante Theorien korrekt verwendet?  
        - Gibt es fundierte Beispiele oder Belege für die Argumentation?  

        **⚖️ Argumentation:**  
        - Sind die Argumente überzeugend entwickelt und logisch nachvollziehbar?  
        - Werden Gegenargumente einbezogen oder kritisch reflektiert?  

        **🔍 Mögliche Nachfragen:**  
        - Stelle zwei herausfordernde Nachfragen zur Reflexion.  
        """

        feedback = openai_anfrage(gpt_prompt)

        st.write("### 🔎 Mein Feedback für dich")
        st.markdown(feedback)

    else:
        st.warning("⚠️ Bitte gib eine Antwort ein!")

