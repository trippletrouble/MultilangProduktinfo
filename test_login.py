import streamlit as st
import os
from msal_streamlit_authentication import msal_authentication
from dotenv import load_dotenv

# Lade Umgebungsvariablen, falls vorhanden (für lokale Entwicklung)
load_dotenv()


def main():
    """
    Eine minimale Streamlit-App, um die Azure AD-Anmeldung zu testen.
    """
    st.set_page_config(page_title="Azure AD Login Test", layout="centered")

    st.title("Azure AD Login Tester")
    st.write("Diese App testet ausschließlich die MSAL-Authentifizierung mit Azure AD.")

    # --- WICHTIGER HINWEIS ZUR KONFIGURATION ---
    st.warning(
        "**Aktion erforderlich:** Stellen Sie sicher, dass in Ihrer Azure AD-App-Registrierung "
        "unter 'Authentifizierung' -> 'Plattformkonfigurationen' -> 'Single-Page-Anwendung (SPA)' "
        "die folgende Umleitungs-URI eingetragen ist: `http://localhost:8501`"
    )

    # --- Azure AD Konfiguration ---
    # Versucht, die Konfiguration aus den Streamlit-Secrets oder Umgebungsvariablen zu laden.
    client_id = os.getenv("AZURE_CLIENT_ID")
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    if not all([client_id, tenant_id, client_secret]):
        try:
            client_id = st.secrets["AZURE_CLIENT_ID"]
            tenant_id = st.secrets["AZURE_TENANT_ID"]
            client_secret = st.secrets["AZURE_CLIENT_SECRET"]
        except (KeyError, FileNotFoundError):
            st.error(
                "Azure AD-Konfiguration fehlt. Bitte stellen Sie sicher, dass AZURE_CLIENT_ID, AZURE_TENANT_ID und AZURE_CLIENT_SECRET in Ihren Streamlit-Secrets oder Umgebungsvariablen gesetzt sind.")
            st.stop()

    st.info(f"Konfiguration geladen. Client ID: ...{client_id[-4:]}")

    # --- Authentifizierungskomponente ---
    # Diese Komponente wird bei jedem App-Lauf aufgerufen.
    # Sie zeigt entweder einen Anmelde-Button an oder gibt bei Erfolg das Token zurück.
    login_token = msal_authentication(
        auth={
            "clientId": client_id,
            "authority": f"https://login.microsoftonline.com/{tenant_id}",
            "clientSecret": client_secret,
            # WICHTIG: Diese URI muss exakt mit der in Azure AD konfigurierten übereinstimmen.
            "redirectUri": "http://localhost:8501"
        },
        cache={
            "cacheLocation": "sessionStorage",
            "storeAuthStateInCookie": False
        },
        login_request={
            "scopes": ["User.Read"]  # Die Berechtigungen, die Ihre App anfordert
        },
        key="msal_auth_tester"  # Ein eindeutiger Schlüssel für diese Komponente
    )

    st.divider()

    # --- Ergebnis anzeigen ---
    st.header("Testergebnis")

    if login_token:
        st.success("Anmeldung erfolgreich!")
        st.write("Das folgende Token wurde von Azure AD zurückgegeben:")
        # Zeigt die Benutzerinformationen im JSON-Format an
        st.json(login_token)
    else:
        st.warning("Nicht angemeldet. Bitte verwenden Sie den Button oben, um sich anzumelden.")


if __name__ == "__main__":
    main()

