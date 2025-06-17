import streamlit as st
import requests
import os
from dotenv import load_dotenv
import base64
import jinja2
import json
import time

# Lade Umgebungsvariablen aus der .env Datei
load_dotenv()

GEMINI_API_KEY_FROM_ENV = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY_FROM_ENV:
    GEMINI_API_KEY = GEMINI_API_KEY_FROM_ENV
else:
    GEMINI_API_KEY = ""

GEMINI_API_URL_GENERATE_CONTENT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"


def translate_text_gemini_api_call(text_to_translate: str, source_language: str, target_language: str) -> tuple[
    str, str | None]:
    if not text_to_translate:
        return text_to_translate, "Kein Text zum Übersetzen angegeben."
    if not target_language:
        return text_to_translate, "Keine Zielsprache für die Übersetzung angegeben."

    prompt = (
        f"Du bist ein reiner Textübersetzer. Deine einzige Aufgabe ist es, den gegebenen Text zu übersetzen. "
        f"Übersetze den folgenden Text von {source_language} nach {target_language}. "
        f"WICHTIG: Das Wort 'suprima' ist ein Markenname und darf NICHT übersetzt werden. Behalte 'suprima' exakt so bei, wie es im Originaltext steht. "
        f"Deine Antwort darf AUSSCHLIESSLICH den übersetzten Text in {target_language} enthalten. "
        f"Gib KEINE Einleitungen, KEINE Erklärungen, KEINE Formatierungen (wie Markdown), KEINE alternativen Übersetzungen und KEINE zusätzlichen Informationen oder Kommentare aus. "
        f"Nur der reine, direkt übersetzte Text in {target_language}, wobei 'suprima' unverändert bleibt. "
        f"Der zu übersetzende Text lautet: \"{text_to_translate}\""
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(GEMINI_API_URL_GENERATE_CONTENT, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        response_json = response.json()

        if response_json.get("candidates") and \
                response_json["candidates"][0].get("content") and \
                response_json["candidates"][0]["content"].get("parts") and \
                response_json["candidates"][0]["content"]["parts"][0].get("text"):

            translated_text = response_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            if translated_text.startswith('"') and translated_text.endswith('"'):
                translated_text = translated_text[1:-1]
            if translated_text.startswith("'") and translated_text.endswith("'"):
                translated_text = translated_text[1:-1]
            return translated_text.strip(), None
        else:
            error_detail = f"Unerwartete Antwortstruktur von Gemini: {response_json}"
            print(f"DEBUG: Unerwartete Gemini-Antwortstruktur: {error_detail}")
            return f"[Gemini Antwort-Verarbeitungsfehler]", error_detail
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Gemini API Request Fehler: {str(e)}")
        return f"[Gemini API Fehler]", str(e)
    except Exception as e:
        print(f"DEBUG: Allgemeiner Fehler bei Gemini Übersetzung: {str(e)}")
        return f"[Allgemeiner Fehler bei Gemini Übersetzung]", str(e)


def create_html_from_template(template_filename, context):
    try:
        template_dir = os.path.dirname(os.path.abspath(__file__))
        template_loader = jinja2.FileSystemLoader(searchpath=template_dir)
        template_env = jinja2.Environment(loader=template_loader)
        template = template_env.get_template(template_filename)
        return template.render(context)
    except jinja2.TemplateNotFound:
        return f"<p>Fehler: Vorlage '{template_filename}' nicht im Verzeichnis '{template_dir}' gefunden.</p>"
    except Exception as e:
        return f"<p>Fehler beim Rendern der Vorlage: {e}</p>"


def get_image_data_url(uploaded_file):
    if uploaded_file is not None:
        contents = uploaded_file.getvalue()
        b64_str = base64.b64encode(contents).decode("utf-8")

        if 'svg' in uploaded_file.type:
            return f"data:image/svg+xml;base64,{b64_str}"

        mime_type = uploaded_file.type
        return f"data:{mime_type};base64,{b64_str}"
    return ""


def load_local_svg(filepath: str) -> str:
    """Lädt eine lokale SVG-Datei und kodiert sie als Base64 Data URL."""
    try:
        with open(filepath, "rb") as f:
            contents = f.read()
        b64_str = base64.b64encode(contents).decode("utf-8")
        return f"data:image/svg+xml;base64,{b64_str}"
    except FileNotFoundError:
        st.error(f"Logo-Datei nicht gefunden unter: {filepath}")
        return ""


def extract_language_name(selected_option_with_flag: str) -> str:
    if selected_option_with_flag:
        return selected_option_with_flag.split(" ", 1)[-1]
    return ""


def get_html_lang_code(language_name: str) -> str:
    mapping = {
        "Englisch": "en", "Französisch": "fr", "Spanisch": "es", "Italienisch": "it",
        "Niederländisch": "nl", "Polnisch": "pl", "Portugiesisch": "pt",
        "Russisch": "ru", "Japanisch": "ja", "Chinesisch (vereinfacht)": "zh-CN",
        "Deutsch": "de", "Türkisch": "tr", "Schwedisch": "sv", "Dänisch": "da",
        "Norwegisch": "no", "Finnisch": "fi", "Isländisch": "is",
        "Estnisch": "et", "Lettisch": "lv", "Litauisch": "lt"
    }
    return mapping.get(language_name, language_name[:2].lower())


def main():
    st.set_page_config(page_title="Produktseiten Generator V2", layout="wide")
    st.title("Produktseiten Generator V2")
    st.markdown("Erstellen Sie mehrsprachige Produktblätter mit dem neuen PDF-Layout.")

    if not GEMINI_API_KEY_FROM_ENV and not GEMINI_API_KEY:
        st.sidebar.warning(
            "INFO: Kein expliziter GEMINI_API_KEY in der .env Datei gefunden. Die API-Aufrufe könnten fehlschlagen.")
    elif GEMINI_API_KEY_FROM_ENV:
        st.sidebar.success("INFO: Gemini API Key erfolgreich aus der .env Datei geladen.")

    st.divider()

    # Deutsche Standardtexte, die übersetzt werden sollen
    default_texts_de = {
        "ean_code_label": "EAN",  # HINZUGEFÜGT
        "article_number_label": "Art.Nr.",
        "oeko_tex_standard_text": "OEKO-TEX® STANDARD 100",
        "oeko_tex_logo_alt_text": "OEKO-TEX Logo Platzhalter",
        "oeko_tex_tested_text": "Geprüft auf Schadstoffe.",
        "warning_label": "ACHTUNG",
        "colors_label": "Farben",
        "sizes_label": "Größen",
        "heading_product_description": "Produktbeschreibung",
        "heading_detail_views": "Detailansichten",
        "heading_care_instructions": "Pflegehinweise",
        "washing_instructions_before_first_use": "Bitte vor dem ersten Tragen waschen.",
        "disclaimer_label": "Warnhinweis",
    }

    # Produktdaten, die vom Benutzer eingegeben werden
    product_data_de = {
        "ean_code_value": "4051512345678",  # HINZUGEFÜGT
        "article_number_value": "ART-12345",
        "warning_text_value": "Ihre volle Wirkung entfalten die suprima Hüftprotektor-Systeme nur durch den Einsatz von suprima-Protektoren!",
        "color_name_value": "Schwarz",
        "available_sizes_value": "S M L",
        "disclaimer_text_value": "Hüftprotektoren können nicht in jedem Fall Sturzverletzungen verhindern. Jegliche Haftung ist deshalb ausgeschlossen."
    }

    # Initialisiere Session State
    for key, default_value in {
        'generated_html_content': "", 'download_filename': "produktblatt.html",
        'error_message': "", 'is_loading': False,
        'image_main_data_url': "", 'image_detail1_data_url': "", 'image_detail2_data_url': "",
        'selected_target_language_with_flag': "🇫🇷 Französisch"
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    if 'suprima_logo_data_url' not in st.session_state:
        st.session_state.suprima_logo_data_url = load_local_svg("logo-3.svg")

    # UI für die Eingabe
    st.header("1. Produktinformationen eingeben")

    product_name_de = st.text_input("Produktname (Deutsch)", value=st.session_state.get("product_name_de",
                                                                                        "suprima Protektor-Slip (ohne Protektoren)"),
                                    key="product_name_de_input")
    ean_code_value_de = st.text_input("EAN Code", value=st.session_state.get("ean_code_value_de",
                                                                             product_data_de["ean_code_value"]),
                                      key="ean_code_input")  # HINZUGEFÜGT
    article_number_value_de = st.text_input("Artikelnummer", value=st.session_state.get("article_number_value_de",
                                                                                        product_data_de[
                                                                                            "article_number_value"]),
                                            key="article_number_input")
    product_description_de = st.text_area("Produktbeschreibung (Deutsch)",
                                          value=st.session_state.get("product_description_de",
                                                                     "Mit dem suprima Hüftprotektor-Slip beugen Sie effektiv Oberschenkelhalsbrüchen und Verletzungen im Falle eines Sturzes vor. Der Slip ist doté de poches de protection à droite et à gauche, qui garantissent un positionnement exact des protections de hanche."),
                                          height=100, key="product_description_de_input")
    product_features_de_str = st.text_area("Merkmale (jedes in eine neue Zeile)",
                                           value=st.session_state.get("product_features_de_str",
                                                                      "schützt den Oberschenkelhals\nvermeidet Sturzverletzungen\nhoher Tragekomfort\nbequem im Liegen"),
                                           height=100, key="product_features_de_str_input")
    warning_text_value_de = st.text_area("Warnhinweis Text (Attention)",
                                         value=st.session_state.get("warning_text_value_de",
                                                                    product_data_de["warning_text_value"]),
                                         key="warn_text_val_input")
    color_name_value_de = st.text_input("Farbbezeichnung(en)", value=st.session_state.get("color_name_value_de",
                                                                                          product_data_de[
                                                                                              "color_name_value"]),
                                        key="color_name_input")
    available_sizes_value_de = st.text_input("Verfügbare Größen", value=st.session_state.get("available_sizes_value_de",
                                                                                             product_data_de[
                                                                                                 "available_sizes_value"]),
                                             key="sizes_value_input")

    care_instructions_de_str = st.text_area("Pflegehinweis-Texte (jeder in eine neue Zeile)",
                                            value=st.session_state.get("care_instructions_de_str",
                                                                       "Nicht bleichen\nNicht chemisch reinigen\nWaschen 95 Grad\nNicht bügeln\nTrocknen"),
                                            height=120, key="care_instructions_de_str_input")

    washing_instructions_de = st.text_input("Waschanleitung vor Erstgebrauch",
                                            value=st.session_state.get("washing_instructions_de", default_texts_de[
                                                "washing_instructions_before_first_use"]),
                                            key="washing_instructions_input")
    disclaimer_text_de = st.text_area("Haftungsausschluss (Disclaimer)",
                                      value=st.session_state.get("disclaimer_text_de",
                                                                 product_data_de["disclaimer_text_value"]),
                                      key="disclaimer_text_input")

    st.header("Bilder hochladen")
    col1, col2, col3 = st.columns(3)
    with col1:
        uploaded_image_main = st.file_uploader("Hauptbild", type=["png", "jpg", "jpeg"], key="img_main")
    with col2:
        uploaded_image_detail1 = st.file_uploader("Detailbild 1", type=["png", "jpg", "jpeg"], key="img_detail1")
    with col3:
        uploaded_image_detail2 = st.file_uploader("Detailbild 2", type=["png", "jpg", "jpeg"], key="img_detail2")

    if uploaded_image_main: st.session_state.image_main_data_url = get_image_data_url(uploaded_image_main)
    if uploaded_image_detail1: st.session_state.image_detail1_data_url = get_image_data_url(uploaded_image_detail1)
    if uploaded_image_detail2: st.session_state.image_detail2_data_url = get_image_data_url(uploaded_image_detail2)

    st.divider()

    st.header("2. Zielsprache auswählen")
    language_options_with_flags = ["🇫🇷 Französisch", "🇬🇧 Englisch", "🇪🇸 Spanisch", "🇮🇹 Italienisch", "🇩🇪 Deutsch",
                                   "🇳🇱 Niederländisch", "🇵🇹 Portugiesisch", "🇵🇱 Polnisch", "🇹🇷 Türkisch",
                                   "🇸🇪 Schwedisch", "🇩🇰 Dänisch", "🇳🇴 Norwegisch", "🇫🇮 Finnisch", "🇮🇸 Isländisch",
                                   "🇪🇪 Estnisch", "🇱🇻 Lettisch", "🇱🇹 Litauisch"]
    selected_target_language_with_flag = st.selectbox("Zielsprache auswählen:", options=language_options_with_flags,
                                                      key="target_language_selectbox")

    st.divider()

    st.header("3. Produktseite generieren")
    if st.button("Produktblatt generieren", key="generate_button", type="primary", use_container_width=True,
                 disabled=st.session_state.is_loading):
        st.session_state.is_loading = True
        st.session_state.error_message = ""

        actual_target_language = extract_language_name(selected_target_language_with_flag)
        source_language = "Deutsch"

        with st.spinner("Übersetzungen werden erstellt..."):
            translated_context = {}
            any_errors = False

            user_texts_to_translate = {
                "product_name": product_name_de,
                "product_description_long": product_description_de,
                "warning_text": warning_text_value_de,
                "color_name": color_name_value_de,
                "washing_instructions_before_first_use": washing_instructions_de,
                "disclaimer_text": disclaimer_text_de,
            }
            for key, text in user_texts_to_translate.items():
                if text.strip():
                    trans, err = translate_text_gemini_api_call(text, source_language, actual_target_language)
                    if err: any_errors = True
                    translated_context[key] = trans
                    time.sleep(0.5)
                else:
                    translated_context[key] = ""

            features_de_list = [f.strip() for f in product_features_de_str.split("\n") if f.strip()]
            translated_features_list = []
            if features_de_list:
                for feature in features_de_list:
                    trans_feat, err_feat = translate_text_gemini_api_call(feature, source_language,
                                                                          actual_target_language)
                    if err_feat: any_errors = True
                    translated_features_list.append(trans_feat)
                    time.sleep(0.5)
            translated_context["features_list"] = translated_features_list

            for key, text in default_texts_de.items():
                trans, err = translate_text_gemini_api_call(text, source_language, actual_target_language)
                if err: any_errors = True
                translated_context[key] = trans
                time.sleep(0.5)

            care_de_list = [f.strip() for f in care_instructions_de_str.split("\n") if f.strip()]
            translated_care_items = []
            if care_de_list:
                default_icons = ["https://placehold.co/30x30/ffffff/000000?text=🧺",
                                 "https://placehold.co/30x30/ffffff/000000?text=🚫",
                                 "https://placehold.co/30x30/ffffff/000000?text=🌡️",
                                 "https://placehold.co/30x30/ffffff/000000?text=💨",
                                 "https://placehold.co/30x30/ffffff/000000?text=뽀"]
                for i, item_text in enumerate(care_de_list):
                    trans_care_text, err_care = translate_text_gemini_api_call(item_text, source_language,
                                                                               actual_target_language)
                    if err_care: any_errors = True
                    icon = default_icons[i] if i < len(
                        default_icons) else "https://placehold.co/30x30/ffffff/000000?text=🧼"
                    translated_care_items.append({"icon_url": icon, "text": trans_care_text})
                    time.sleep(0.5)
            translated_context["care_instructions"] = translated_care_items

            if any_errors:
                st.session_state.error_message = "Einige Texte konnten nicht übersetzt werden. Bitte überprüfen Sie die Ausgabe."
            else:
                st.session_state.error_message = "Übersetzung erfolgreich!"

            final_context = {
                **translated_context,
                "ean_code_value": ean_code_value_de,  # HINZUGEFÜGT
                "article_number_value": article_number_value_de,
                "available_sizes_value": available_sizes_value_de,
                "lang_code": get_html_lang_code(actual_target_language),
                "image_main_url": st.session_state.image_main_data_url or 'https://placehold.co/400x400/e2e8f0/a0aec0?text=Hauptbild',
                "image_detail1_url": st.session_state.image_detail1_data_url or 'https://placehold.co/300x200/e2e8f0/a0aec0?text=Detail+1',
                "image_detail2_url": st.session_state.image_detail2_data_url or 'https://placehold.co/300x200/e2e8f0/a0aec0?text=Detail+2',
                "suprima_logo_url": st.session_state.suprima_logo_data_url,
            }

            template_file = "produkt_vorlage_v2.html"
            st.session_state.generated_html_content = create_html_from_template(template_file, final_context)
            st.session_state.download_filename = f"{product_name_de.replace(' ', '_')}_{final_context['lang_code']}.html"

        st.session_state.is_loading = False
        st.rerun()

    if st.session_state.error_message:
        if "Fehler" in st.session_state.error_message or "konnten nicht übersetzt werden" in st.session_state.error_message:
            st.warning(st.session_state.error_message)
        else:
            st.success(st.session_state.error_message)

    st.divider()

    if st.session_state.generated_html_content:
        st.subheader(f"Vorschau: Produktseite ({selected_target_language_with_flag})")
        st.components.v1.html(st.session_state.generated_html_content, height=700, scrolling=True)
        st.download_button(
            label="HTML-Seite herunterladen",
            data=st.session_state.generated_html_content,
            file_name=st.session_state.download_filename,
            mime="text/html",
            key="download_button"
        )


if __name__ == "__main__":
    main()
