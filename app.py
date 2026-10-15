import streamlit as st
import os
import io
import zipfile
import tempfile
from datetime import datetime
from groq import Groq
from supabase import create_client, Client

st.set_page_config(page_title="Bea", page_icon="logo.png", layout="wide", initial_sidebar_state="collapsed")

# --- SECRETS / CLIENTS ---
# Dans Streamlit Cloud : Settings > Secrets
# GROQ_API_KEY = "gsk_..."
# SUPABASE_URL = "https://xxx.supabase.co"
# SUPABASE_KEY = "eyJ..."

def get_groq():
    key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if not key:
        return None
    return Groq(api_key=key)

def get_supabase() -> Client | None:
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

groq_client = get_groq()
supabase = get_supabase()

if "logged" not in st.session_state:
    st.session_state.logged = False
if "user" not in st.session_state:
    st.session_state.user = None
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "current_ia" not in st.session_state:
    st.session_state.current_ia = "dashboard"
if "forge_files" not in st.session_state:
    st.session_state.forge_files = {}

st.markdown("""
<style>
.stApp {background:#0a0a12}
.card-login {background:#12121f; border-radius:24px; padding:40px; border:1.5px solid #2a2a3f; max-width:440px; margin:auto; position:relative}
.card-login::before {content:''; position:absolute; inset:0; border-radius:24px; padding:1.5px; background:linear-gradient(135deg,#7c3aed,#c026d3); -webkit-mask:linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); -webkit-mask-composite:xor; mask-composite:exclude; pointer-events:none}
.ia-card {background:#12121f; border-radius:20px; padding:24px; border:1.5px solid #2a2a3f}
.stButton>button {background:linear-gradient(135deg,#7c3aed,#c026d3)!important; color:white!important; border:none!important; border-radius:12px!important; font-weight:600!important; height:48px}
</style>
""", unsafe_allow_html=True)

def groq_generate(prompt, system):
    if not groq_client:
        return f"[GROQ_API_KEY manquante] - Mode démo pour : {prompt[:100]}"
    try:
        chat = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        return chat.choices[0].message.content
    except Exception as e:
        return f"Erreur Groq: {e}"

# --- 1. LOGIN SUPABASE ---
def show_login():
    c1,c2,c3 = st.columns([1,1.3,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo.png"):
            st.image("logo.png", width=70)
        st.markdown("### Connexion")
        st.caption("Connexion Supabase requise.")
        email = st.text_input("Adresse e-mail", key="l_email")
        pwd = st.text_input("Mot de passe", type="password", key="l_pwd")

        if st.button("Se connecter", use_container_width=True):
            if not email or not pwd:
                st.error("Renseigner e-mail et mot de passe")
            else:
                if supabase:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                        if res.user:
                            st.session_state.logged = True
                            st.session_state.user = res.user
                            # Récupère le nom dans profiles si existe
                            try:
                                prof = supabase.table("profiles").select("*").eq("id", res.user.id).execute()
                                if prof.data and prof.data[0].get("full_name"):
                                    st.session_state.user_name = prof.data[0]["full_name"]
                            except:
                                pass
                            st.rerun()
                    except Exception as e:
                        # Si login fail, tente signup
                        try:
                            res2 = supabase.auth.sign_up({"email": email, "password": pwd})
                            if res2.user:
                                st.success("Compte créé, tu peux te connecter")
                        except Exception as e2:
                            st.error(f"Erreur Supabase: {e}")
                else:
                    # Mode sans supabase (dev local)
                    st.session_state.logged = True
                    st.session_state.user = {"email": email}
                    st.rerun()

def show_name():
    c1,c2,c3 = st.columns([1,1.3,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### Bienvenue")
        st.caption("Quel nom doit être utilisé?")
        name = st.text_input("Prénom", key="n_name")
        if st.button("Continuer", use_container_width=True):
            if name.strip():
                st.session_state.user_name = name.strip()
                if supabase and st.session_state.user:
                    try:
                        user_id = st.session_state.user.id if hasattr(st.session_state.user, 'id') else st.session_state.user.get('id')
                        if user_id:
                            supabase.table("profiles").upsert({"id": user_id, "full_name": name.strip(), "email": st.session_state.user.email if hasattr(st.session_state.user, 'email') else ""}).execute()
                    except Exception as e:
                        st.warning(f"Supabase profiles: {e}")
                st.rerun()

def dashboard():
    top1, top2 = st.columns([4,1])
    with top1:
        st.markdown(f"### Bonjour {st.session_state.user_name} — 3 IA disponibles")
    with top2:
        if st.button("Déconnexion"):
            if supabase:
                try:
                    supabase.auth.sign_out()
                except:
                    pass
            st.session_state.logged = False
            st.session_state.user = None
            st.session_state.user_name = ""
            st.session_state.current_ia = "dashboard"
            st.rerun()

    c1,c2,c3 = st.columns(3)
    with c1:
        if os.path.exists("logo_forge.png"): st.image("logo_forge.png", width=52)
        st.markdown("#### De l'idée au projet")
        st.markdown("**Transformer une idée vague en projet structuré et exécutable.**")
        st.caption("À partir d'une intention de départ, construire un plan, des systèmes et des outils qui fonctionnent.")
        st.info("Avantages: plan complet ordonné, systèmes réutilisables, passage direct conception à exécution. Pourquoi payer: évite des mois de dispersion et livre un résultat utilisable tout de suite.")
        if st.button("Ouvrir De l'idée au projet", key="o1", use_container_width=True):
            st.session_state.current_ia = "forge"; st.rerun()
    with c2:
        if os.path.exists("logo_bea.png"): st.image("logo_bea.png", width=52)
        st.markdown("#### Analyse comportementale")
        st.markdown("**L'analyse des comportements quotidiens qui déterminent la réussite sur le long terme.**")
        st.caption("Repérer les schémas qui freinent puis les corriger.")
        st.info("Avantages: détection habitudes contre-objectifs, proposition comportements de remplacement, mise en place routines discipline. Pourquoi payer: blocages remplacés par comportements de réussite mesurables.")
        if st.button("Ouvrir Analyse", key="o2", use_container_width=True):
            st.session_state.current_ia = "bea"; st.rerun()
    with c3:
        if os.path.exists("logo_nova.png"): st.image("logo_nova.png", width=52)
        st.markdown("#### Montage vidéo professionnel")
        st.markdown("**L'ensemble des fonctions de montage vidéo professionnel réuni dans un seul outil.**")
        st.caption("Production vidéos prêtes à diffuser: sous-titrage, découpe, effets automatisés.")
        st.info("Avantages: sous-titres stylisés synchronisés, suppression arrière-plan / découpe silences / nettoyage audio, bibliothèque modèles/effets/transitions, export optimisé. Pourquoi payer: remplace plusieurs logiciels et heures de montage.")
        if st.button("Ouvrir Montage vidéo", key="o3", use_container_width=True):
            st.session_state.current_ia = "nova"; st.rerun()

def ia_forge():
    if st.button("← Retour"): st.session_state.current_ia="dashboard"; st.rerun()
    st.markdown("## De l'idée au projet — Générateur de Sites & Apps")
    prompt = st.text_area("Décris ce que tu veux construire", height=150, placeholder="Ex: SaaS de prise de notes avec auth, dashboard, paiement Stripe...")
    type_site = st.selectbox("Type", ["Site vitrine moderne", "Application SaaS / Dashboard", "Landing page", "Portfolio"])

    if st.button("Construire avec Groq", type="primary", use_container_width=True):
        if not prompt:
            st.warning("Décris l'idée")
        else:
            system = f"""Tu es un expert développeur fullstack. Tu génères un site complet en 1 seul fichier index.html avec Tailwind CDN, design sombre #0a0a12 et accent violet #7c3aed -> #c026d3, moderne, prêt à vendre. Type demandé: {type_site}. Tu dois répondre UNIQUEMENT avec le code HTML complet du site, sans explication, sans markdown, code directement utilisable. Le site doit être fonctionnel avec JS inline pour {prompt}."""
            with st.spinner("Groq génère le site..."):
                code = groq_generate(prompt, system)
                # Nettoie si Groq met ```html
                if "```" in code:
                    code = code.split("```")[1] if "```" in code else code
                    code = code.replace("html","").strip()
                st.session_state.forge_files = {"index.html": code}

            st.success("Site généré par Groq!")
            st.components.v1.html(code, height=700, scrolling=True)
            st.code(code, language="html")

            # Sauvegarde Supabase
            if supabase:
                try:
                    supabase.table("projects").insert({"user_id": st.session_state.user.id if hasattr(st.session_state.user,'id') else None, "type": "forge", "prompt": prompt, "code": code[:5000]}).execute()
                except:
                    pass

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("index.html", code)
            st.download_button("Télécharger site.zip", buf.getvalue(), file_name="site_forge.zip", mime="application/zip", use_container_width=True)

def ia_bea():
    if st.button("← Retour"): st.session_state.current_ia="dashboard"; st.rerun()
    st.markdown("## Analyse comportementale — IA Comportementale Groq")
    txt = st.text_area("Décris la situation bloquante", height=140)
    if st.button("Analyser avec Groq", type="primary", use_container_width=True):
        system = """Tu es BEA, IA d'analyse comportementale. Tu analyses les comportements quotidiens qui déterminent la réussite. Format:
        1. DÉTECTION des habitudes contre-objectifs
        2. COMPORTEMENTS DE REMPLACEMENT alignés réussite
        3. ROUTINES discipline et décision
        Ton ton est direct, sans parler à la 2e personne, tu listes avantages et pourquoi payer est justifié. Réponse courte et applicable."""
        res = groq_generate(txt, system)
        st.markdown(res)
        if supabase:
            try:
                supabase.table("analyses").insert({"user_id": st.session_state.user.id if hasattr(st.session_state.user,'id') else None, "type": "bea", "input": txt, "output": res}).execute()
            except:
                pass

def ia_nova():
    if st.button("← Retour"): st.session_state.current_ia="dashboard"; st.rerun()
    st.markdown("## Montage vidéo professionnel — Groq + Montage")

    uploaded = st.file_uploader("Vidéo brute", type=["mp4","mov","webm","avi"])
    script = st.text_area("Script / paroles pour sous-titres", height=100)

    colA,colB = st.columns(2)
    with colA: fmt = st.selectbox("Format export", ["9:16 TikTok", "16:9 YouTube", "1:1 Feed"])
    with colB: style_sub = st.selectbox("Style sous-titres", ["Viral pop", "Minimal", "Hormozi"])

    if uploaded:
        st.video(uploaded)

    if st.button("Générer montage avec Groq", type="primary", use_container_width=True):
        system = f"""Tu es NOVA, IA de montage vidéo pro. Tu as toutes les fonctions de montage. Format: {fmt}, Style: {style_sub}.
        À partir du script, génère:
        - Sous-titres stylisés synchronisés (format SRT)
        - Plan de découpe (où couper silences)
        - Liste effets/transitions/modèles à appliquer
        - Instructions export optimisé
        Réponse structurée et directement utilisable. Si vidéo fournie, donne les timecodes.
        """
        full_prompt = f"Script: {script}\nFormat: {fmt}\nStyle: {style_sub}\nTâches: sous-titres, suppression arrière-plan, découpe silences, nettoyage audio, modèles, effets, transitions, export."
        res = groq_generate(full_prompt, system)
        st.markdown(res)

        # Génération SRT démo
        if script:
            words = script.split()
            srt = ""
            for i in range(0, len(words), 7):
                chunk = words[i:i+7]
                srt += f"{i//7+1}\\n00:00:{i//2:02d},000 --> 00:00:{i//2+2:02d},500\\n{' '.join(chunk)}\\n\\n"
            st.code(srt, language="text")
            st.download_button("Télécharger.srt", srt, file_name="sous_titres.srt")

        if supabase:
            try:
                supabase.table("montages").insert({"user_id": st.session_state.user.id if hasattr(st.session_state.user,'id') else None, "script": script, "output": res, "format": fmt}).execute()
            except:
                pass

# ROUTER
if not st.session_state.logged:
    show_login()
elif not st.session_state.user_name:
    show_name()
else:
    if st.session_state.current_ia == "dashboard":
        dashboard()
    elif st.session_state.current_ia == "forge":
        ia_forge()
    elif st.session_state.current_ia == "bea":
        ia_bea()
    elif st.session_state.current_ia == "nova":
        ia_nova()
