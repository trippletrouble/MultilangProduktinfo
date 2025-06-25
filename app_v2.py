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
        print(f"Fehler beim Rendern der Vorlage: {e}")
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
    try:
        with open(filepath, "rb") as f:
            contents = f.read()
        b64_str = base64.b64encode(contents).decode("utf-8")
        return f"data:image/svg+xml;base64,{b64_str}"
    except FileNotFoundError:
        st.error(f"Datei nicht gefunden: {filepath}")
        return ""


def extract_language_name(selected_option_with_code: str) -> str:
    if selected_option_with_code:
        return selected_option_with_code.split(" ", 1)[-1]
    return ""


def get_html_lang_code(language_name: str) -> str:
    # GEÄNDERT: Neue Sprachen hinzugefügt
    mapping = {
        "Englisch": "en", "Französisch": "fr", "Spanisch": "es", "Italienisch": "it",
        "Niederländisch": "nl", "Polnisch": "pl", "Portugiesisch": "pt",
        "Russisch": "ru", "Japanisch": "ja", "Chinesisch (vereinfacht)": "zh-CN",
        "Deutsch": "de", "Türkisch": "tr", "Schwedisch": "sv", "Dänisch": "da",
        "Norwegisch": "no", "Finnisch": "fi", "Isländisch": "is",
        "Estnisch": "et", "Lettisch": "lv", "Litauisch": "lt",
        "Griechisch": "el", "Tschechisch": "cs", "Rumänisch": "ro", "Ungarisch": "hu",
        "Slowakisch": "sk", "Slowenisch": "sl", "Serbisch": "sr", "Kroatisch": "hr"
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

    # DATEN FÜR GRÖSSENTABELLEN
    size_charts_de = {
        "Briefs": {
            "type": "simple", "title": "Maßtabelle Damen und Herren",
            "footer": "* Die suprima-Größe entspricht der Damen-Konfektionsgröße.",
            "headers": ["Größe", "suprima-Größe*", "Wäschegröße (Herren)", "Hüftumfang (cm)"],
            "groups": [{"size_category": "S", "rows": [["36", "4", "90-92"], ["38", "4", "93-96"]]},
                       {"size_category": "M", "rows": [["40", "5", "97-100"], ["42", "5", "101-104"]]},
                       {"size_category": "L", "rows": [["44", "6", "105-108"], ["46", "6", "109-112"]]},
                       {"size_category": "XL", "rows": [["48", "7", "113-116"], ["50", "7", "117-121"]]},
                       {"size_category": "XXL", "rows": [["52", "8", "122-126"], ["54", "8", "127-132"]]},
                       {"size_category": "XXXL",
                        "rows": [["56", "9", "133-138"], ["58", "9", "139-144"], ["60", "10", "145-150"]]}]
        },
        "Overall": {
            "type": "complex", "title": "Maßtabelle Overalls",
            "tables": [{"subtitle": "für Damen", "headers": ["S", "M", "L", "XL", "XXL"],
                        "rows": [["36/38", "40/42", "44/46", "48/50", "52/54/56"]]},
                       {"subtitle": "für Herren", "headers": ["S", "M", "L", "XL", "XXL"],
                        "rows": [["44", "46/48", "50/52", "54/56", "58/60"]]},
                       {"subtitle": "für Kinder", "title_full": "Angaben entsprechen der Körpergröße des Kindes",
                        "rows": [["110/116", "122/128", "134/140", "146/152", "158/164"]]}]
        }
    }

    # Deutsche Standardtexte, die übersetzt werden sollen
    default_texts_de = {"article_number_label": "Art.Nr.", "ean_code_label": "EAN",
                        "oeko_tex_standard_text": "OEKO-TEX® STANDARD 100",
                        "oeko_tex_logo_alt_text": "OEKO-TEX Logo Platzhalter",
                        "oeko_tex_tested_text": "Geprüft auf Schadstoffe.", "warning_label": "ACHTUNG",
                        "colors_label": "Farben", "sizes_label": "Größen",
                        "heading_product_description": "Produktbeschreibung", "heading_detail_views": "Detailansichten",
                        "heading_care_instructions": "Pflegehinweise",
                        "washing_instructions_before_first_use": "Bitte vor dem ersten Tragen waschen.",
                        "disclaimer_label": "Warnhinweis"}
    product_data_de = {"ean_code_value": "4051512345678", "article_number_value": "ART-12345",
                       "warning_text_value": "Ihre volle Wirkung entfalten die suprima Hüftprotektor-Systeme nur durch den Einsatz von suprima-Protektoren!",
                       "color_name_value": "Schwarz", "available_sizes_value": "S M L",
                       "disclaimer_text_value": "Hüftprotektoren können nicht in jedem Fall Sturzverletzungen verhindern. Jegliche Haftung ist deshalb ausgeschlossen."}
    CARE_INSTRUCTIONS_LIBRARY = [{"text": "Waschen 30 Grad", "icon_filename": "waschen_30_grad59c8af44.svg"},
                                 {"text": "Waschen 40 Grad", "icon_filename": "waschen_40_grad.svg"},
                                 {"text": "Waschen 60 Grad", "icon_filename": "waschen60.svg"},
                                 {"text": "Waschen 95 Grad", "icon_filename": "waschen_95_grad.svg"},
                                 {"text": "Handwäsche", "icon_filename": "handwaesche.svg"},
                                 {"text": "Nicht bleichen", "icon_filename": "bleichenNein.svg"},
                                 {"text": "Nicht bügeln", "icon_filename": "nicht_buegeln.svg"},
                                 {"text": "Mäßig heiss bügeln", "icon_filename": "maessig_Buegeln.svg"},
                                 {"text": "Heiss bügeln", "icon_filename": "buegeln_normal.svg"},
                                 {"text": "Chemisch reinigen", "icon_filename": "chemisch_reinigen.svg"},
                                 {"text": "Nicht chemisch reinigen", "icon_filename": "chemischNein.svg"},
                                 {"text": "Schonend reinigen", "icon_filename": "schonend_reinigen.svg"},
                                 {"text": "Trocknen", "icon_filename": "trocknen.svg"},
                                 {"text": "Nicht im Trommeltrockner trocknen",
                                  "icon_filename": "Nicht_trocknen59c51c3e49.svg"},
                                 {"text": "Schonend trocknen", "icon_filename": "trockner1.svg"},
                                 {"text": "Nicht schleudern", "icon_filename": "nicht-schleudern.svg"},
                                 {"text": "Keinen Weichspüler verwenden", "icon_filename": "kein_weichspu-ler.svg"},
                                 {"text": "Abwischbar", "icon_filename": "abwischbar.svg"},
                                 {"text": "Protektor entfernen", "icon_filename": "protektor-entfernen.svg"}]

    # Session State initialisieren
    for key, default_value in {'generated_html_content': "", 'download_filename': "produktblatt.html",
                               'error_message': "", 'is_loading': False, 'image_main_data_url': "",
                               'image_detail1_data_url': "", 'image_detail2_data_url': "",
                               'selected_target_language_with_code': "(FR) Französisch"}.items():
        if key not in st.session_state: st.session_state[key] = default_value
    if 'suprima_logo_data_url' not in st.session_state: st.session_state.suprima_logo_data_url = load_local_svg(
        "logo-3.svg")

    # --- UI für die Eingabe ---
    st.header("1. Produktinformationen eingeben")

    product_name_de = st.text_input("Produktname (Deutsch)", "suprima Protektor-Slip (ohne Protektoren)")
    ean_code_value_de = st.text_input("EAN Code", product_data_de.get("ean_code_value", ""))
    article_number_value_de = st.text_input("Artikelnummer", product_data_de["article_number_value"])
    product_description_de = st.text_area("Produktbeschreibung (Deutsch)",
                                          "Mit dem suprima Hüftprotektor-Slip beugen Sie effektiv Oberschenkelhalsbrüchen und Verletzungen im Falle eines Sturzes vor. Der Slip ist doté de poches de protection à droite et à gauche, qui garantissent un positionnement exact des protections de hanche.",
                                          height=100)
    product_features_de_str = st.text_area("Merkmale (jedes in eine neue Zeile)",
                                           "schützt den Oberschenkelhals\nvermeidet Sturzverletzungen\nhoher Tragekomfort\nbequem im Liegen",
                                           height=100)
    warning_text_value_de = st.text_area("Warnhinweis Text (Attention)", product_data_de["warning_text_value"])
    color_name_value_de = st.text_input("Farbbezeichnung(en)", product_data_de["color_name_value"])
    available_sizes_value_de = st.text_input("Verfügbare Größen", product_data_de["available_sizes_value"])

    care_options_de = [item["text"] for item in CARE_INSTRUCTIONS_LIBRARY]
    selected_care_instructions_de = st.multiselect("Pflegehinweise auswählen:", options=care_options_de,
                                                   default=["Nicht bleichen", "Waschen 95 Grad", "Nicht bügeln",
                                                            "Trocknen", "Nicht chemisch reinigen"])

    washing_instructions_de = st.text_input("Waschanleitung vor Erstgebrauch",
                                            default_texts_de["washing_instructions_before_first_use"])
    disclaimer_text_de = st.text_area("Haftungsausschluss (Disclaimer)", product_data_de["disclaimer_text_value"])

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

    st.header("2. Zielsprache & Optionen auswählen")
    col1_options, col2_options = st.columns(2)
    with col1_options:
        # GEÄNDERT: Erweiterte Sprachliste
        language_options_with_codes = [
            "(GB) Englisch", "(FR) Französisch", "(DE) Deutsch", "(ES) Spanisch", "(IT) Italienisch",
            "(NL) Niederländisch", "(PT) Portugiesisch", "(PL) Polnisch", "(TR) Türkisch",
            "(SE) Schwedisch", "(DK) Dänisch", "(NO) Norwegisch", "(FI) Finnisch", "(IS) Isländisch",
            "(EE) Estnisch", "(LV) Lettisch", "(LT) Litauisch",
            "(GR) Griechisch", "(CZ) Tschechisch", "(RO) Rumänisch", "(HU) Ungarisch",
            "(SK) Slowakisch", "(SI) Slowenisch", "(RS) Serbisch", "(HR) Kroatisch",
            "(JP) Japanisch", "(CN) Chinesisch (vereinfacht)"
        ]
        selected_target_language_with_code = st.selectbox("Zielsprache auswählen:", options=language_options_with_codes,
                                                          key="target_language_selectbox")
    with col2_options:
        product_type = st.selectbox("Produkttyp für Größentabelle:", options=["Keine", "Briefs", "Overall"],
                                    key="product_type_select")

    st.divider()

    st.header("3. Produktseite generieren")
    if st.button("Produktblatt generieren", key="generate_button", type="primary", use_container_width=True,
                 disabled=st.session_state.is_loading):
        st.session_state.is_loading = True
        st.session_state.error_message = ""

        actual_target_language = extract_language_name(selected_target_language_with_code)
        source_language = "Deutsch"

        with st.spinner("Übersetzungen werden erstellt..."):
            translated_context = {}
            any_errors = False

            user_texts_to_translate = {"product_name": product_name_de,
                                       "product_description_long": product_description_de,
                                       "warning_text": warning_text_value_de, "color_name": color_name_value_de,
                                       "washing_instructions_before_first_use": washing_instructions_de,
                                       "disclaimer_text": disclaimer_text_de}
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

            translated_care_items = []
            for selected_text in selected_care_instructions_de:
                icon_filename = next(
                    (item["icon_filename"] for item in CARE_INSTRUCTIONS_LIBRARY if item["text"] == selected_text),
                    None)
                trans_care_text, err_care = translate_text_gemini_api_call(selected_text, source_language,
                                                                           actual_target_language)
                if err_care: any_errors = True
                if icon_filename:
                    icon_data_url = load_local_svg(f"waschlabellen/{icon_filename}")
                    translated_care_items.append({"icon_url": icon_data_url, "text": trans_care_text})
                time.sleep(0.5)
            translated_context["care_instructions"] = translated_care_items

            if product_type != "Keine":
                chart_data = size_charts_de[product_type]
                translated_chart = {"type": chart_data["type"], "rows": chart_data.get("rows", []),
                                    "groups": chart_data.get("groups", []), "tables": []}
                trans_title, err_title = translate_text_gemini_api_call(chart_data["title"], source_language,
                                                                        actual_target_language);
                time.sleep(0.5)
                translated_chart["title"] = trans_title
                if err_title: any_errors = True
                if "footer" in chart_data:
                    trans_footer, err_footer = translate_text_gemini_api_call(chart_data["footer"], source_language,
                                                                              actual_target_language);
                    time.sleep(0.5)
                    translated_chart["footer"] = trans_footer
                    if err_footer: any_errors = True
                if "headers" in chart_data:
                    translated_headers = [translate_text_gemini_api_call(h, source_language, actual_target_language)[0]
                                          for h in chart_data["headers"]]
                    translated_chart["headers"] = translated_headers
                if "tables" in chart_data:
                    for sub_table_data in chart_data["tables"]:
                        translated_sub_table = {"rows": sub_table_data["rows"]}
                        trans_subtitle, err_subtitle = translate_text_gemini_api_call(sub_table_data["subtitle"],
                                                                                      source_language,
                                                                                      actual_target_language);
                        time.sleep(0.5)
                        translated_sub_table["subtitle"] = trans_subtitle
                        if err_subtitle: any_errors = True
                        if "title_full" in sub_table_data:
                            trans_title_full, err_tf = translate_text_gemini_api_call(sub_table_data["title_full"],
                                                                                      source_language,
                                                                                      actual_target_language);
                            time.sleep(0.5)
                            translated_sub_table["title_full"] = trans_title_full
                            if err_tf: any_errors = True
                        if "headers" in sub_table_data:
                            translated_sub_headers = [
                                translate_text_gemini_api_call(h, source_language, actual_target_language)[0] for h in
                                sub_table_data["headers"]]
                            translated_sub_table["headers"] = translated_sub_headers
                        translated_chart["tables"].append(translated_sub_table)
                translated_context["size_chart"] = translated_chart

            if any_errors:
                st.session_state.error_message = "Einige Texte konnten nicht übersetzt werden."
            else:
                st.session_state.error_message = "Übersetzung erfolgreich!"

            final_context = {**translated_context, "ean_code_value": ean_code_value_de,
                             "article_number_value": article_number_value_de,
                             "available_sizes_value": available_sizes_value_de,
                             "lang_code": get_html_lang_code(actual_target_language),
                             "image_main_url": st.session_state.image_main_data_url or 'https://placehold.co/400x400/e2e8f0/a0aec0?text=Hauptbild',
                             "image_detail1_url": st.session_state.image_detail1_data_url or 'https://placehold.co/300x200/e2e8f0/a0aec0?text=Detail+1',
                             "image_detail2_url": st.session_state.image_detail2_data_url or 'https://placehold.co/300x200/e2e8f0/a0aec0?text=Detail+2',
                             "suprima_logo_url": st.session_state.suprima_logo_data_url}

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
        st.subheader(f"Vorschau: Produktseite ({selected_target_language_with_code})")
        st.components.v1.html(st.session_state.generated_html_content, height=700, scrolling=True)
        st.download_button(label="HTML-Seite herunterladen", data=st.session_state.generated_html_content,
                           file_name=st.session_state.download_filename, mime="text/html", key="download_button")


if __name__ == "__main__":
    main()
