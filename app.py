import streamlit as st
import pandas as pd
import datetime
import requests
from sqlalchemy import text

from db import init_db, get_conn, get_engine, backup_db
from utils import parse_excel_like_yours, normalize_canonical_csv

st.set_page_config(page_title="il Micarboglino", layout="wide", initial_sidebar_state="collapsed")
init_db()

if "backup_done" not in st.session_state:
    backup_db()
    st.session_state["backup_done"] = True

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background-color: #0a0a0a; color: #e8e0d0; }
.stApp { background-color: #0a0a0a; }
h1,h2,h3 { font-family: 'Playfair Display', serif; color: #e8e0d0; }
div[data-testid="stTabs"] button { font-size: 0.75rem; letter-spacing: 0.12em; text-transform: uppercase; color: #555; }
div[data-testid="stTabs"] button[aria-selected="true"] { color: #c8a96e; border-bottom-color: #c8a96e !important; }
.stTextInput input, .stTextArea textarea, .stNumberInput input { background: #141414 !important; border: 1px solid #222 !important; color: #e8e0d0 !important; border-radius: 2px !important; }
.stButton button { background: #c8a96e !important; color: #0a0a0a !important; border: none !important; border-radius: 2px !important; font-weight: 500 !important; letter-spacing: 0.05em !important; }
.stButton button:hover { background: #e8c97e !important; }
[data-testid="stMetricValue"] { color: #c8a96e !important; font-family: 'Playfair Display', serif !important; }
div[data-baseweb="select"] > div { background: #141414 !important; border-color: #222 !important; color: #e8e0d0 !important; }
img { border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

TMDB_KEY = st.secrets.get("TMDB_API_KEY", "")
TMDB_IMG = "https://image.tmdb.org/t/p/w342"

@st.cache_data(ttl=86400)
def get_poster(titolo, titolo_originale=None, anno=None):
    if not TMDB_KEY: return None
    def search(query, year=None):
        try:
            params = {"api_key": TMDB_KEY, "query": query, "language": "it-IT"}
            if year: params["year"] = int(year)
            r = requests.get("https://api.themoviedb.org/3/search/movie", params=params, timeout=5)
            results = r.json().get("results", [])
            if results and results[0].get("poster_path"):
                return TMDB_IMG + results[0]["poster_path"]
            if year:
                params.pop("year")
                r = requests.get("https://api.themoviedb.org/3/search/movie", params=params, timeout=5)
                results = r.json().get("results", [])
                if results and results[0].get("poster_path"):
                    return TMDB_IMG + results[0]["poster_path"]
        except Exception:
            pass
        return None
    if titolo:
        p = search(titolo, anno)
        if p: return p
    if titolo_originale:
        p = search(titolo_originale, anno)
        if p: return p
    return None

def insert_df(df: pd.DataFrame):
    cols = {
        "FILM_RAW": "film_raw", "TITOLO": "titolo", "TITOLO_ORIGINALE": "titolo_originale",
        "REGISTA": "regista", "PAESE": "paese", "ANNO": "anno", "NOTE": "note",
        "REGIA_ANNIKA": "regia_annika", "REGIA_FRANCESCO": "regia_francesco",
        "FOTOGRAFIA_ANNIKA": "fotografia_annika", "FOTOGRAFIA_FRANCESCO": "fotografia_francesco",
        "SCENEGGIATURA_ANNIKA": "sceneggiatura_annika", "SCENEGGIATURA_FRANCESCO": "sceneggiatura_francesco",
        "RECITAZIONE_ANNIKA": "recitazione_annika", "RECITAZIONE_FRANCESCO": "recitazione_francesco",
        "GLOBALE_ANNIKA": "globale_annika", "GLOBALE_FRANCESCO": "globale_francesco",
        "MEDIA_ANNIKA": "media_annika", "MEDIA_FRANCESCO": "media_francesco",
        "VOTO FINALE": "voto_finale", "INDICE_CONFLITTO": "indice_conflitto",
    }
    for k in cols:
        if k not in df.columns: df[k] = None
    df2 = df[list(cols.keys())].rename(columns=cols)
    engine = get_engine()
    existing = pd.read_sql_query("SELECT titolo, anno FROM films", engine)
    ex_keys = set(zip(existing["titolo"].fillna("").astype(str).str.strip().str.lower(), existing["anno"].fillna(-1).astype(int)))
    mask = [(t.lower().strip(), int(y)) not in ex_keys for t, y in zip(df2["titolo"].fillna("").astype(str), df2["anno"].fillna(-1).astype(int))]
    df_new = df2[pd.Series(mask, index=df2.index)]
    if len(df_new) > 0:
        df_new.to_sql("films", engine, if_exists="append", index=False)

def load_all():
    return pd.read_sql_query("SELECT * FROM films", get_engine())

def compute_scores(ra, rf, fa, ff, sa, sf, rea, ref_, ga, gf):
    ma = (ra + fa + sa + rea + ga) / 5
    mf = (rf + ff + sf + ref_ + gf) / 5
    return ma, mf, (ma + mf) / 2, (abs(ra-rf) + abs(fa-ff) + abs(sa-sf) + abs(rea-ref_) + abs(ga-gf)) / 5

def sv(v):
    """Convert numpy/pandas values to Python native types for SQL."""
    if v is None: return None
    try:
        if pd.isna(v): return None
    except Exception: pass
    if hasattr(v, 'item'): return v.item()
    return v

def score_color(v):
    if v is None or pd.isna(v): return "#444"
    if v >= 4: return "#c8a96e"
    if v >= 3: return "#a0b87a"
    if v >= 2: return "#8898aa"
    return "#aa6868"

st.markdown('<p style="font-family:Playfair Display,serif;font-size:2.8rem;font-weight:700;color:#e8e0d0;letter-spacing:-0.02em;margin-bottom:0">🎬 il Micarboglino</p>', unsafe_allow_html=True)
st.markdown('<p style="font-size:0.8rem;color:#555;letter-spacing:0.15em;text-transform:uppercase;margin-top:0;margin-bottom:2rem">Francesco + Annika &nbsp;·&nbsp; il cinema come referendum domestico</p>', unsafe_allow_html=True)

# PIN sessione
if "unlocked" not in st.session_state:
    st.session_state["unlocked"] = False

if not st.session_state["unlocked"]:
    with st.expander("🔒 Accesso area di modifica", expanded=False):
        pin_input = st.text_input("PIN", type="password", key="pin_input")
        if st.button("Sblocca", key="btn_unlock"):
            if pin_input == st.secrets.get("APP_PIN", ""):
                st.session_state["unlocked"] = True
                st.rerun()
            else:
                st.error("PIN errato.")

tab3, tab2, tab4, tab1 = st.tabs(["Classifiche", "Inserisci film", "Gestisci", "Import"])

with tab3:
    df = load_all()
    col_search, col_sort, col_ord = st.columns([3, 2, 1])
    with col_search:
        query = st.text_input("", placeholder="🔍  Cerca un film...", key="search_title", label_visibility="collapsed")
    with col_sort:
        metrica = st.selectbox("", ["voto_finale","regia_media","fotografia_media","sceneggiatura_media","recitazione_media","globale_media"], key="rank_metric", label_visibility="collapsed")
    with col_ord:
        ordine = st.selectbox("", ["↓ desc", "↑ asc"], key="rank_order", label_visibility="collapsed")

    if query:
        df = df[df["titolo"].astype(str).str.contains(query, case=False, na=False)]

    for col in ["fotografia_media","regia_media","sceneggiatura_media","recitazione_media","globale_media"]:
        base = col.replace("_media","")
        df[col] = df[[f"{base}_annika", f"{base}_francesco"]].mean(axis=1)

    df_sorted = df.sort_values(metrica, ascending="asc" in ordine, na_position="last").reset_index(drop=True)
    st.caption(f"{len(df_sorted)} film")

    cols_per_row = 6
    for row_start in range(0, len(df_sorted), cols_per_row):
        row_films = df_sorted.iloc[row_start:row_start+cols_per_row]
        grid_cols = st.columns(cols_per_row)
        for i, (_, film) in enumerate(row_films.iterrows()):
            with grid_cols[i]:
                t_orig = film.get("titolo_originale") if "titolo_originale" in film and pd.notna(film.get("titolo_originale")) else None
                poster_url = get_poster(film["titolo"], t_orig, film.get("anno"))
                voto = film.get("voto_finale")
                conflict = film.get("indice_conflitto")
                anno = str(int(film["anno"])) if pd.notna(film.get("anno")) else ""
                voto_str = f"{voto:.1f}" if pd.notna(voto) else "—"
                col_v = score_color(voto)
                has_conflict = pd.notna(conflict) and conflict > 1

                if poster_url:
                    st.image(poster_url, use_container_width=True)
                else:
                    st.markdown(f'<div style="aspect-ratio:2/3;background:#161616;display:flex;align-items:center;justify-content:center;padding:0.5rem;margin-bottom:4px"><span style="font-size:0.68rem;color:#444;text-align:center">{film["titolo"][:30]}</span></div>', unsafe_allow_html=True)

                conflict_icon = " ⚡" if has_conflict else ""
                st.markdown(f'<span style="font-family:Playfair Display,serif;font-size:1.5rem;font-weight:700;color:{col_v}">{voto_str}</span><span style="font-size:0.7rem;color:#cc4444">{conflict_icon}</span>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.7rem;color:#ccc;font-weight:600;line-height:1.3;margin-bottom:1px">{film["titolo"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.6rem;color:#555;margin-bottom:1.2rem">{anno}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Dettaglio film")
    labels = df_sorted.apply(lambda r: f'{r["titolo"]} ({int(r["anno"]) if pd.notna(r.get("anno")) else "?"})', axis=1).tolist()
    if labels:
        pick = st.selectbox("Scegli film", range(len(labels)), format_func=lambda i: labels[i], key="detail_pick")
        film = df_sorted.iloc[pick]
        t_orig = film.get("titolo_originale") if "titolo_originale" in film and pd.notna(film.get("titolo_originale")) else None
        poster_url = get_poster(film["titolo"], t_orig, film.get("anno"))
        dcol1, dcol2 = st.columns([1, 3])
        with dcol1:
            if poster_url: st.image(poster_url, use_container_width=True)
        with dcol2:
            st.markdown(f'<h2 style="margin-top:0;font-family:Playfair Display,serif">{film["titolo"]}</h2>', unsafe_allow_html=True)
            meta = [x for x in [film.get("regista"), str(int(film["anno"])) if pd.notna(film.get("anno")) else None, film.get("paese")] if x and pd.notna(x)]
            st.markdown(f'<div style="color:#666;font-size:0.82rem;margin-bottom:1.2rem">{" · ".join(meta)}</div>', unsafe_allow_html=True)
            m1,m2,m3,m4 = st.columns(4)
            with m1: st.metric("Voto finale", f"{film['voto_finale']:.2f}" if pd.notna(film.get('voto_finale')) else "—")
            with m2: st.metric("Annika", f"{film['media_annika']:.2f}" if pd.notna(film.get('media_annika')) else "—")
            with m3: st.metric("Francesco", f"{film['media_francesco']:.2f}" if pd.notna(film.get('media_francesco')) else "—")
            with m4: st.metric("Conflitto", f"{film['indice_conflitto']:.2f}" if pd.notna(film.get('indice_conflitto')) else "—")
            cats = [("Regia","regia"),("Fotografia","fotografia"),("Sceneggiatura","sceneggiatura"),("Recitazione","recitazione"),("Globale","globale")]
            rows = [{"Categoria": l, "Annika": f"{film.get(f'{k}_annika'):.1f}" if pd.notna(film.get(f'{k}_annika')) else "—", "Francesco": f"{film.get(f'{k}_francesco'):.1f}" if pd.notna(film.get(f'{k}_francesco')) else "—"} for l,k in cats]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            try:
                raw_note = film["note"]
                note_ok = raw_note is not None and str(raw_note).strip() not in ("", "None", "nan", "NaN")
                if note_ok:
                    st.markdown("**Note:**")
                    st.info(str(raw_note))
            except Exception:
                pass

with tab2:
    if not st.session_state.get("unlocked"):
        st.warning("🔒 Inserisci il PIN in cima alla pagina per accedere a questa sezione.")
        st.stop()
    st.subheader("Inserisci un film")
    titolo = st.text_input("Titolo", key="new_titolo")
    titolo_orig = st.text_input("Titolo originale (per la locandina, se diverso)", key="new_titolo_orig")
    regista = st.text_input("Regista (facoltativo)", key="new_regista")
    anno = st.number_input("Anno", 1800, 2100, 2000, key="new_anno")
    note = st.text_area("Note", key="new_note")
    st.markdown("### Voti (0–5)")
    def v(label, k):
        a, f = st.columns(2)
        with a: va = st.number_input(f"{label} — Annika", 0.0, 5.0, 0.0, 0.5, key=f"{k}_a")
        with f: vf = st.number_input(f"{label} — Francesco", 0.0, 5.0, 0.0, 0.5, key=f"{k}_f")
        return va, vf
    ra,rf = v("Regia","new_regia"); fa,ff = v("Fotografia","new_foto")
    sa,sf = v("Sceneggiatura","new_scen"); rea,ref_ = v("Recitazione","new_rec"); ga,gf = v("Globale","new_glob")
    ma,mf,voto_finale,ic = compute_scores(ra,rf,fa,ff,sa,sf,rea,ref_,ga,gf)
    st.info(f"Media Annika: {ma:.2f}  |  Media Francesco: {mf:.2f}  |  Voto finale: {voto_finale:.2f}")
    if st.button("Salva film", key="btn_save_new"):
        if not titolo.strip(): st.error("Metti almeno il titolo.")
        else:
            insert_df(pd.DataFrame([{"FILM_RAW": titolo, "TITOLO": titolo, "TITOLO_ORIGINALE": titolo_orig or None, "REGISTA": regista or None, "PAESE": None, "ANNO": int(anno) if anno else None, "NOTE": note or None, "REGIA_ANNIKA": ra, "REGIA_FRANCESCO": rf, "FOTOGRAFIA_ANNIKA": fa, "FOTOGRAFIA_FRANCESCO": ff, "SCENEGGIATURA_ANNIKA": sa, "SCENEGGIATURA_FRANCESCO": sf, "RECITAZIONE_ANNIKA": rea, "RECITAZIONE_FRANCESCO": ref_, "GLOBALE_ANNIKA": ga, "GLOBALE_FRANCESCO": gf, "MEDIA_ANNIKA": ma, "MEDIA_FRANCESCO": mf, "VOTO FINALE": voto_finale, "INDICE_CONFLITTO": ic}]))
            st.success("Film salvato.")
            st.rerun()

with tab4:
    if not st.session_state.get("unlocked"):
        st.warning("🔒 Inserisci il PIN in cima alla pagina per accedere a questa sezione.")
        st.stop()
    st.subheader("Gestisci archivio")
    df = load_all()
    if df.empty: st.warning("Database vuoto.")
    else:
        df_sorted = df.sort_values(["titolo","anno"], na_position="last").reset_index(drop=True)
        labels = df_sorted.apply(lambda r: f'{r["titolo"]} ({int(r["anno"]) if pd.notna(r["anno"]) else "?"})', axis=1).tolist()
        ids = df_sorted["id"].astype(int).tolist()
        pick = st.selectbox("Scegli film", range(len(labels)), format_func=lambda i: labels[i], key="manage_pick")
        film_id = int(ids[pick])
        row = df_sorted[df_sorted["id"] == film_id].iloc[0]
        st.divider()
        changed_by = st.selectbox("Chi modifica", ["Francesco","Annika"], key="manage_by")
        motivo = st.text_input("Motivo (facoltativo)", key="manage_reason")
        k = f"film_{film_id}"
        titolo_new = st.text_input("Titolo", value=row["titolo"], key=f"{k}_titolo")
        t_orig_val = str(row.get("titolo_originale") or "") if pd.notna(row.get("titolo_originale")) else ""
        titolo_orig_new = st.text_input("Titolo originale", value=t_orig_val, key=f"{k}_titolo_orig")
        anno_new = st.number_input("Anno", 1800, 2100, int(row["anno"]) if pd.notna(row["anno"]) else 2000, key=f"{k}_anno")
        note_new = st.text_area("Note", value=str(row.get("note") or "") if pd.notna(row.get("note")) else "", key=f"{k}_note")
        st.markdown("### Voti (0–5)")
        cA,cF = st.columns(2)
        with cA:
            ra = st.number_input("Regia — Annika", 0.0, 5.0, float(row["regia_annika"] or 0), 0.5, key=f"{k}_ra")
            fa = st.number_input("Fotografia — Annika", 0.0, 5.0, float(row["fotografia_annika"] or 0), 0.5, key=f"{k}_fa")
            sa = st.number_input("Sceneggiatura — Annika", 0.0, 5.0, float(row["sceneggiatura_annika"] or 0), 0.5, key=f"{k}_sa")
            rea = st.number_input("Recitazione — Annika", 0.0, 5.0, float(row["recitazione_annika"] or 0), 0.5, key=f"{k}_rea")
            ga = st.number_input("Globale — Annika", 0.0, 5.0, float(row["globale_annika"] or 0), 0.5, key=f"{k}_ga")
        with cF:
            rf = st.number_input("Regia — Francesco", 0.0, 5.0, float(row["regia_francesco"] or 0), 0.5, key=f"{k}_rf")
            ff = st.number_input("Fotografia — Francesco", 0.0, 5.0, float(row["fotografia_francesco"] or 0), 0.5, key=f"{k}_ff")
            sf = st.number_input("Sceneggiatura — Francesco", 0.0, 5.0, float(row["sceneggiatura_francesco"] or 0), 0.5, key=f"{k}_sf")
            ref_ = st.number_input("Recitazione — Francesco", 0.0, 5.0, float(row["recitazione_francesco"] or 0), 0.5, key=f"{k}_ref")
            gf = st.number_input("Globale — Francesco", 0.0, 5.0, float(row["globale_francesco"] or 0), 0.5, key=f"{k}_gf")
        ma,mf,voto_finale,ic = compute_scores(ra,rf,fa,ff,sa,sf,rea,ref_,ga,gf)
        st.info(f"Nuovo voto finale: {voto_finale:.2f}  |  Conflitto: {ic:.2f}")
        if st.button("Salva modifiche (con storico)", key=f"{k}_save"):
            with get_conn() as conn:
                conn.execute(text("""INSERT INTO film_history (film_id,changed_at,changed_by,titolo,anno,note,regia_annika,regia_francesco,fotografia_annika,fotografia_francesco,sceneggiatura_annika,sceneggiatura_francesco,recitazione_annika,recitazione_francesco,globale_annika,globale_francesco,media_annika,media_francesco,voto_finale,indice_conflitto) VALUES (:film_id,:changed_at,:changed_by,:titolo,:anno,:note,:ra,:rf,:fa,:ff,:sa,:sf,:rea,:ref_,:ga,:gf,:ma,:mf,:vf,:ic)"""),
                    {"film_id":int(film_id),"changed_at":datetime.datetime.now().isoformat(timespec="seconds"),"changed_by":f"{changed_by}{' — '+motivo if motivo else ''}","titolo":sv(row.get("titolo")),"anno":int(row["anno"]) if pd.notna(row["anno"]) else None,"note":sv(row.get("note")),"ra":sv(row.get("regia_annika")),"rf":sv(row.get("regia_francesco")),"fa":sv(row.get("fotografia_annika")),"ff":sv(row.get("fotografia_francesco")),"sa":sv(row.get("sceneggiatura_annika")),"sf":sv(row.get("sceneggiatura_francesco")),"rea":sv(row.get("recitazione_annika")),"ref_":sv(row.get("recitazione_francesco")),"ga":sv(row.get("globale_annika")),"gf":sv(row.get("globale_francesco")),"ma":sv(row.get("media_annika")),"mf":sv(row.get("media_francesco")),"vf":sv(row.get("voto_finale")),"ic":sv(row.get("indice_conflitto"))})
                conn.execute(text("""UPDATE films SET titolo=:titolo,titolo_originale=:t_orig,anno=:anno,note=:note,regia_annika=:ra,regia_francesco=:rf,fotografia_annika=:fa,fotografia_francesco=:ff,sceneggiatura_annika=:sa,sceneggiatura_francesco=:sf,recitazione_annika=:rea,recitazione_francesco=:ref_,globale_annika=:ga,globale_francesco=:gf,media_annika=:ma,media_francesco=:mf,voto_finale=:vf,indice_conflitto=:ic WHERE id=:id"""),
                    {"titolo":titolo_new,"t_orig":titolo_orig_new or None,"anno":int(anno_new) if anno_new else None,"note":note_new or None,"ra":float(ra),"rf":float(rf),"fa":float(fa),"ff":float(ff),"sa":float(sa),"sf":float(sf),"rea":float(rea),"ref_":float(ref_),"ga":float(ga),"gf":float(gf),"ma":float(ma),"mf":float(mf),"vf":float(voto_finale),"ic":float(ic),"id":int(film_id)})
            st.success("Aggiornato.")
            st.rerun()
        st.divider()
        st.markdown("### Cronologia modifiche")
        hist = pd.read_sql_query("SELECT changed_at,changed_by,titolo,anno,voto_finale,note FROM film_history WHERE film_id=%(film_id)s ORDER BY id DESC", get_engine(), params={"film_id":film_id})
        if hist.empty: st.caption("Nessuna modifica registrata.")
        else: st.dataframe(hist, use_container_width=True)

with tab1:
    if not st.session_state.get("unlocked"):
        st.warning("🔒 Inserisci il PIN in cima alla pagina per accedere a questa sezione.")
        st.stop()
    st.subheader("Importa Excel/CSV")
    up = st.file_uploader("Carica un file", type=["xlsx","xls","csv"], key="import_uploader")
    if up is not None:
        try:
            import tempfile
            if up.name.lower().endswith((".xlsx",".xls")):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp.write(up.getbuffer()); tmp_path = tmp.name
                df = parse_excel_like_yours(tmp_path)
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    tmp.write(up.getbuffer()); tmp_path = tmp.name
                df = normalize_canonical_csv(tmp_path)
            st.success(f"Letti {len(df)} film.")
            st.dataframe(df.head(30), use_container_width=True)
            if st.button("Importa nel database", key="btn_import_db"):
                insert_df(df)
                st.success("Import completato.")
                st.rerun()
        except Exception as e:
            st.error(str(e))
