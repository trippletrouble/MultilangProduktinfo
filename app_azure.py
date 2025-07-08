import streamlit as st
from msal_streamlit_authentication import msal_authentication
import os
from dotenv import load_dotenv
import base64
import jinja2
import json
import time
import deepl
import re

# Lade Umgebungsvariablen für die lokale Entwicklung
load_dotenv()

# --- Globale Konstanten und Konfiguration ---
# Daten werden nur einmal beim Start der App geladen, nicht bei jeder Interaktion.
CARE_INSTRUCTIONS_LIBRARY = [
    {"text": "Waschen 30 Grad", "icon_filename": "waschen_30_grad59c8af44.svg"},
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
    {"text": "Nicht im Trommeltrockner trocknen", "icon_filename": "Nicht_trocknen59c51c3e49.svg"},
    {"text": "Schonend trocknen", "icon_filename": "trockner1.svg"},
    {"text": "Nicht schleudern", "icon_filename": "nicht-schleudern.svg"},
    {"text": "Keinen Weichspüler verwenden", "icon_filename": "kein_weichspu-ler.svg"},
    {"text": "Abwischbar", "icon_filename": "abwischbar.svg"},
    {"text": "Protektor entfernen", "icon_filename": "protektor-entfernen.svg"},
]
SIZE_CHARTS_DE = {
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
DEFAULT_TEXTS_DE = {"article_number_label": "Art.Nr.", "ean_code_label": "EAN",
                    "oeko_tex_standard_text": "OEKO-TEX® STANDARD 100",
                    "oeko_tex_logo_alt_text": "OEKO-TEX Logo Platzhalter",
                    "oeko_tex_tested_text": "Geprüft auf Schadstoffe.", "warning_label": "ACHTUNG",
                    "colors_label": "Farben", "sizes_label": "Größen",
                    "heading_product_description": "Produktbeschreibung",
                    "heading_detail_views": "Detailansichten",
                    "heading_care_instructions": "Pflegehinweise",
                    "washing_instructions_before_first_use": "",
                    "disclaimer_label": "Warnhinweis",
                    "translation_disclaimer": "Maschinell übersetzt mit DeepL. Bei Fragen kontaktieren Sie uns bitte.",
                    "package_size_weight_label": "Verpackungsgröße & Gewicht"
                    }
PRODUCT_DATA_DE = {"ean_code_value": "4051512345678", "article_number_value": "ART-12345",
                   "warning_text_value": "Ihre volle Wirkung entfalten die suprima Hüftprotektor-Systeme nur durch den Einsatz von suprima-Protektoren!",
                   "color_name_value": "Schwarz", "available_sizes_value": "S M L",
                   "disclaimer_text_value": "Hüftprotektoren können nicht in jedem Fall Sturzverletzungen verhindern. Jegliche Haftung ist deshalb ausgeschlossen."}

# --- API Key Konfiguration ---
translator = None
deepl_api_key = os.getenv("DEEPL_API_KEY")
if not deepl_api_key:
    try:
        deepl_api_key = st.secrets.get("DEEPL_API_KEY")
    except (KeyError, FileNotFoundError):
        pass
if deepl_api_key:
    translator = deepl.Translator(deepl_api_key)


# --- Hilfsfunktionen ---

def translate_text_deepl_api_call(text_to_translate: str, source_language: str, target_language: str) -> tuple[
    str, str | None]:
    if not text_to_translate: return text_to_translate, "Kein Text zum Übersetzen angegeben."
    if not target_language: return text_to_translate, "Keine Zielsprache für die Übersetzung angegeben."
    if not translator: return f"[DeepL API Fehler]", "DeepL API-Schlüssel nicht konfiguriert oder ungültig."

    lang_map = {
        "Englisch": "EN-GB", "Französisch": "FR", "Spanisch": "ES", "Italienisch": "IT",
        "Niederländisch": "NL", "Polnisch": "PL", "Portugiesisch": "PT-PT",
        "Russisch": "RU", "Japanisch": "JA", "Chinesisch (vereinfacht)": "ZH",
        "Deutsch": "DE", "Türkisch": "TR", "Schwedisch": "SV", "Dänisch": "DA",
        "Norwegisch": "NB", "Finnisch": "FI", "Isländisch": "IS",
        "Estnisch": "ET", "Lettisch": "LV", "Litauisch": "LT",
        "Griechisch": "EL", "Tschechisch": "CS", "Rumänisch": "RO",
        "Ungarisch": "HU", "Slowakisch": "SK", "Slowenisch": "SL"
    }
    target_lang_code = lang_map.get(target_language)
    if not target_lang_code: return f"[Fehler]", f"Unbekannter Sprachcode für Zielsprache: {target_language}"
    source_lang_code = lang_map.get(source_language)
    if not source_lang_code: return f"[Fehler]", f"Unbekannter Sprachcode für Quellsprache: {source_language}"

    try:
        text_with_tags = re.sub(r'(suprima)', r'<keep>\1</keep>', text_to_translate, flags=re.IGNORECASE)
        result = translator.translate_text(text_with_tags, source_lang=source_lang_code, target_lang=target_lang_code,
                                           tag_handling="xml", ignore_tags=["keep"])
        return result.text.replace('<keep>', '').replace('</keep>', '').strip(), None
    except deepl.DeepLException as e:
        return f"[DeepL API Fehler]", str(e)
    except Exception as e:
        return f"[Allgemeiner Fehler bei DeepL Übersetzung]", str(e)


def create_html_from_template(template_filename, context):
    try:
        template_dir = os.path.dirname(os.path.abspath(__file__))
        template_loader = jinja2.FileSystemLoader(searchpath=template_dir)
        template_env = jinja2.Environment(loader=template_loader)
        template = template_env.get_template(template_filename)
        return template.render(context)
    except jinja2.TemplateNotFound:
        st.error(f"Fehler: Vorlage '{template_filename}' nicht im Verzeichnis '{template_dir}' gefunden.")
        return f"<p>Fehler: Vorlage '{template_filename}' nicht gefunden.</p>"
    except Exception as e:
        st.error(f"Fehler beim Rendern der Vorlage: {e}")
        return f"<p>Fehler beim Rendern der Vorlage: {e}</p>"


def get_image_data_url(uploaded_file):
    if uploaded_file:
        return f"data:{uploaded_file.type};base64,{base64.b64encode(uploaded_file.getvalue()).decode('utf-8')}"
    return ""


def load_local_svg(filepath: str) -> str:
    try:
        with open(filepath, "rb") as f:
            return f"data:image/svg+xml;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    except FileNotFoundError:
        st.error(f"Lokale SVG-Datei nicht gefunden: {filepath}")
        return ""


def extract_language_name(selected_option_with_code: str) -> str:
    return selected_option_with_code.split(" ", 1)[-1] if selected_option_with_code else ""


def get_html_lang_code(language_name: str) -> str:
    mapping = {
        "Englisch": "en", "Französisch": "fr", "Spanisch": "es", "Italienisch": "it",
        "Niederländisch": "nl", "Polnisch": "pl", "Portugiesisch": "pt",
        "Russisch": "ru", "Japanisch": "ja", "Chinesisch (vereinfacht)": "zh-CN",
        "Deutsch": "de", "Türkisch": "tr", "Schwedisch": "sv", "Dänisch": "da",
        "Norwegisch": "no", "Finnisch": "fi", "Isländisch": "is",
        "Estnisch": "et", "Lettisch": "lv", "Litauisch": "lt",
        "Griechisch": "el", "Tschechisch": "cs", "Rumänisch": "ro",
        "Ungarisch": "hu", "Slowakisch": "sk", "Slowenisch": "sl"
    }
    return mapping.get(language_name, language_name[:2].lower())


def render_product_generator(user_info):
    """
    Zeichnet die Haupt-UI der Anwendung, nachdem der Benutzer authentifiziert ist.
    """
    st.sidebar.success(f"Angemeldet als: {user_info['account']['name']}")
    st.title("Produktseiten Generator V2 (DeepL)")
    st.markdown("Erstellen Sie mehrsprachige Produktblätter mit dem neuen PDF-Layout.")

    if not translator:
        st.sidebar.error("FEHLER: DeepL API-Schlüssel nicht konfiguriert.")
    else:
        st.sidebar.success("INFO: DeepL API-Schlüssel erfolgreich geladen.")
    st.divider()

    # Session State initialisieren
    for key, default_value in {'generated_html_content': "", 'download_filename': "produktblatt.html",
                               'error_message': "", 'is_loading': False, 'image_main_data_url': "",
                               'image_detail1_data_url': "", 'image_detail2_data_url': ""}.items():
        if key not in st.session_state: st.session_state[key] = default_value
    if 'suprima_logo_data_url' not in st.session_state:
        st.session_state.suprima_logo_data_url = load_local_svg("logo-3.svg")

    # --- UI für die Eingabe ---
    st.header("1. Produktinformationen eingeben")
    product_name_de = st.text_input("Produktname (Deutsch)", "suprima Protektor-Slip (ohne Protektoren)")
    ean_code_value_de = st.text_input("EAN Code", PRODUCT_DATA_DE.get("ean_code_value", ""))
    article_number_value_de = st.text_input("Artikelnummer", PRODUCT_DATA_DE["article_number_value"])
    product_description_de = st.text_area("Produktbeschreibung (Deutsch)",
                                          "Mit dem suprima Hüftprotektor-Slip beugen Sie effektiv Oberschenkelhalsbrüchen und Verletzungen im Falle eines Sturzes vor. Der Slip ist doté de poches de protection à droite et à gauche, qui garantissent un positionnement exact des protections de hanche.",
                                          height=100)
    product_features_de_str = st.text_area("Merkmale (jedes in eine neue Zeile)",
                                           "schützt den Oberschenkelhals\nvermeidet Sturzverletzungen\nhoher Tragekomfort\nbequem im Liegen",
                                           height=100)
    has_oeko_tex = st.checkbox("Produkt hat OEKO-TEX® STANDARD 100 Zertifikat", value=True)
    warning_text_value_de = st.text_area("Warnhinweis Text (Achtung)", PRODUCT_DATA_DE["warning_text_value"])
    color_name_value_de = st.text_input("Farbbezeichnung(en)", PRODUCT_DATA_DE["color_name_value"])
    available_sizes_value_de = st.text_input("Verfügbare Größen", PRODUCT_DATA_DE["available_sizes_value"])
    package_size_weight_de = st.text_input("Verpackungsgröße & Gewicht", "25 x 15 x 5 cm, 200g")
    care_options_de = [item["text"] for item in CARE_INSTRUCTIONS_LIBRARY]
    selected_care_instructions_de = st.multiselect("Pflegehinweise auswählen:", options=care_options_de,
                                                   default=["Nicht bleichen", "Waschen 95 Grad", "Nicht bügeln",
                                                            "Trocknen", "Nicht chemisch reinigen"])
    washing_instructions_de = st.text_input("Waschanleitung vor Erstgebrauch",
                                            DEFAULT_TEXTS_DE["washing_instructions_before_first_use"])
    disclaimer_text_de = st.text_area("Haftungsausschluss (Disclaimer)", PRODUCT_DATA_DE["disclaimer_text_value"])

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
        language_options_with_codes = ["(GB) Englisch", "(FR) Französisch", "(DE) Deutsch", "(ES) Spanisch",
                                       "(IT) Italienisch", "(NL) Niederländisch", "(PT) Portugiesisch", "(PL) Polnisch",
                                       "(TR) Türkisch", "(SE) Schwedisch", "(DK) Dänisch", "(NO) Norwegisch",
                                       "(FI) Finnisch", "(IS) Isländisch", "(EE) Estnisch", "(LV) Lettisch",
                                       "(LT) Litauisch", "(JP) Japanisch", "(CN) Chinesisch (vereinfacht)",
                                       "(GR) Griechisch", "(CZ) Tschechisch", "(RO) Rumänisch", "(HU) Ungarisch",
                                       "(SK) Slowakisch", "(SI) Slowenisch"]
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
        any_errors = False
        translated_context = {}

        with st.spinner(f"Produktblatt für {actual_target_language} wird erstellt..."):
            if actual_target_language == source_language:
                st.info("Quell- und Zielsprache sind identisch. Übersetzungen werden übersprungen.")
                translated_context = {**DEFAULT_TEXTS_DE, "product_name": product_name_de,
                                      "product_description_long": product_description_de,
                                      "warning_text": warning_text_value_de, "color_name": color_name_value_de,
                                      "washing_instructions_before_first_use": washing_instructions_de,
                                      "disclaimer_text": disclaimer_text_de,
                                      "features_list": [f.strip() for f in product_features_de_str.split("\n") if
                                                        f.strip()], "package_size_weight_value": package_size_weight_de}
                if not has_oeko_tex:
                    translated_context.update(
                        {"oeko_tex_standard_text": "", "oeko_tex_logo_alt_text": "", "oeko_tex_tested_text": ""})
            else:
                user_texts_to_translate = {"product_name": product_name_de,
                                           "product_description_long": product_description_de,
                                           "warning_text": warning_text_value_de, "color_name": color_name_value_de,
                                           "washing_instructions_before_first_use": washing_instructions_de,
                                           "disclaimer_text": disclaimer_text_de,
                                           "package_size_weight_value": package_size_weight_de}
                for key, text in user_texts_to_translate.items():
                    if text.strip():
                        trans, err = translate_text_deepl_api_call(text, source_language, actual_target_language)
                        if err: any_errors = True
                        translated_context[key] = trans
                    else:
                        translated_context[key] = ""

                features_de_list = [f.strip() for f in product_features_de_str.split("\n") if f.strip()]
                translated_context["features_list"] = [
                    translate_text_deepl_api_call(f, source_language, actual_target_language)[0] for f in
                    features_de_list]

                texts_to_translate_from_defaults = DEFAULT_TEXTS_DE.copy()
                if not has_oeko_tex:
                    texts_to_translate_from_defaults.pop("oeko_tex_standard_text", None);
                    texts_to_translate_from_defaults.pop("oeko_tex_logo_alt_text", None);
                    texts_to_translate_from_defaults.pop("oeko_tex_tested_text", None)
                    translated_context.update(
                        {"oeko_tex_standard_text": "", "oeko_tex_logo_alt_text": "", "oeko_tex_tested_text": ""})
                for key, text in texts_to_translate_from_defaults.items():
                    trans, err = translate_text_deepl_api_call(text, source_language, actual_target_language)
                    if err: any_errors = True
                    translated_context[key] = trans

            # Verarbeitung nach der Übersetzung (unabhängig von der Sprache)
            translated_care_items = []
            for text in selected_care_instructions_de:
                icon_filename = next(
                    (item["icon_filename"] for item in CARE_INSTRUCTIONS_LIBRARY if item["text"] == text), None)
                if icon_filename:
                    trans_text = text if actual_target_language == source_language else \
                    translate_text_deepl_api_call(text, source_language, actual_target_language)[0]
                    icon_path = os.path.join("Waschlabellen", icon_filename)
                    icon_data_url = load_local_svg(icon_path)
                    if icon_data_url: translated_care_items.append({"icon_url": icon_data_url, "text": trans_text})
            translated_context["care_instructions"] = translated_care_items

            if product_type != "Keine":
                chart_data = SIZE_CHARTS_DE[product_type]
                translated_chart = {"type": chart_data["type"], "rows": chart_data.get("rows", []),
                                    "groups": chart_data.get("groups", []), "tables": []}

                def translate_if_needed(text):
                    return text if actual_target_language == source_language else \
                    translate_text_deepl_api_call(text, source_language, actual_target_language)[0]

                translated_chart["title"] = translate_if_needed(chart_data["title"])
                if "footer" in chart_data: translated_chart["footer"] = translate_if_needed(chart_data["footer"])
                if "headers" in chart_data: translated_chart["headers"] = [translate_if_needed(h) for h in
                                                                           chart_data["headers"]]
                if "tables" in chart_data:
                    for sub_table_data in chart_data["tables"]:
                        translated_sub_table = {"rows": sub_table_data["rows"]}
                        translated_sub_table["subtitle"] = translate_if_needed(sub_table_data["subtitle"])
                        if "title_full" in sub_table_data: translated_sub_table["title_full"] = translate_if_needed(
                            sub_table_data["title_full"])
                        if "headers" in sub_table_data: translated_sub_table["headers"] = [translate_if_needed(h) for h
                                                                                           in sub_table_data["headers"]]
                        translated_chart["tables"].append(translated_sub_table)
                translated_context["size_chart"] = translated_chart

        if any_errors:
            st.session_state.error_message = "Einige Texte konnten nicht übersetzt werden. Prüfen Sie die Konsole für Details."
        else:
            st.session_state.error_message = "Produktblatt erfolgreich generiert!"

        final_context = {**translated_context, "ean_code_value": ean_code_value_de,
                         "article_number_value": article_number_value_de,
                         "available_sizes_value": available_sizes_value_de,
                         "lang_code": get_html_lang_code(actual_target_language),
                         "image_main_url": st.session_state.image_main_data_url or 'https://placehold.co/400x400/e2e8f0/a0aec0?text=Hauptbild',
                         "image_detail1_url": st.session_state.image_detail1_data_url or 'https://placehold.co/300x200/e2e8f0/a0aec0?text=Detail+1',
                         "image_detail2_url": st.session_state.image_detail2_data_url or 'https://placehold.co/300x200/e2e8f0/a0aec0?text=Detail+2',
                         "suprima_logo_url": st.session_state.suprima_logo_data_url}
        st.session_state.generated_html_content = create_html_from_template("produkt_vorlage_v2.html", final_context)
        st.session_state.download_filename = f"{article_number_value_de}_{final_context['lang_code']}.html"
        st.session_state.is_loading = False
        st.rerun()

    if st.session_state.error_message:
        if "Fehler" in st.session_state.error_message or "konnten nicht übersetzt werden" in st.session_state.error_message:
            st.warning(st.session_state.error_message)
        else:
            st.success(st.session_state.error_message)

    st.divider()

    if st.session_state.generated_html_content:
        if 'target_language_selectbox' in st.session_state:
            display_language = extract_language_name(st.session_state.target_language_selectbox)
            st.subheader(f"Vorschau: Produktseite ({display_language})")
        st.components.v1.html(st.session_state.generated_html_content, height=700, scrolling=True)
        st.download_button(label="HTML-Seite herunterladen", data=st.session_state.generated_html_content,
                           file_name=st.session_state.download_filename, mime="text/html", key="download_button")


def main():
    """
    Hauptfunktion: Erzwingt die Authentifizierung und ruft dann die Hauptanwendung auf.
    """
    st.set_page_config(page_title="Produktseiten Generator", layout="wide")

    # --- Azure AD Konfiguration ---
    client_id = os.getenv("AZURE_CLIENT_ID")
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    if not all([client_id, tenant_id, client_secret]):
        try:
            client_id = st.secrets["AZURE_CLIENT_ID"]
            tenant_id = st.secrets["AZURE_TENANT_ID"]
            client_secret = st.secrets["AZURE_CLIENT_SECRET"]
        except (KeyError, FileNotFoundError):
            st.error("Azure AD-Konfiguration fehlt. Bitte fügen Sie die Secrets hinzu.")
            st.stop()

    # --- ROBUSTERE AUTHENTIFIZIERUNGS-LOGIK ---
    # Rufen Sie die Komponente bei jeder Ausführung auf. Sie liest den Status aus dem Session-Speicher des Browsers.
    login_token = msal_authentication(
        auth={"clientId": client_id, "authority": f"https://login.microsoftonline.com/{tenant_id}",
              "clientSecret": client_secret},
        cache={"cacheLocation": "sessionStorage", "storeAuthStateInCookie": False},
        login_request={"scopes": ["User.Read"]},
        key="1"
    )

    # Verwenden Sie den Rückgabewert der Komponente, um den Status der App zu bestimmen
    if login_token:
        # Wenn ein Token vorhanden ist, ist der Benutzer angemeldet. Zeigen Sie die App an.
        render_product_generator(login_token)
        if st.sidebar.button("Logout"):
            # Um sich abzumelden, müssen wir den Status in der Sitzung löschen und die App neu ausführen.
            st.session_state['login_token'] = None
            st.rerun()
    else:
        # Wenn kein Token vorhanden ist, zeigen Sie die Anmeldeaufforderung an.
        st.info("Bitte melden Sie sich an, um die Anwendung zu nutzen.")


if __name__ == "__main__":
    main()
