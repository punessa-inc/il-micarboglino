import streamlit as st
import pandas as pd
import datetime
from sqlalchemy import text

from db import init_db, get_conn, get_engine, backup_db
from utils import parse_excel_like_yours, normalize_canonical_csv

st.set_page_config(page_title="il Micarboglino", layout="wide")
init_db()

if "backup_done" not in st.session_state:
    backup_db()
    st.session_state["backup_done"] = True

st.title("🎬 il Micarboglino")
st.caption("Francesco + Annika: il cinema come referendum domestico.")

tab3, tab2, tab4, tab1 = st.tabs(["Classifiche", "Inserisci film", "Gestisci", "Import"])


def insert_df(df: pd.DataFrame):
    cols = {
        "FILM_RAW": "film_raw",
        "TITOLO": "titolo",
        "REGISTA": "regista",
        "PAESE": "paese",
        "ANNO": "anno",
        "NOTE": "note",
        "REGIA_ANNIKA": "regia_annika",
        "REGIA_FRANCESCO": "regia_francesco",
        "FOTOGRAFIA_ANNIKA": "fotografia_annika",
        "FOTOGRAFIA_FRANCESCO": "fotografia_francesco",
        "SCENEGGIATURA_ANNIKA": "sceneggiatura_annika",
        "SCENEGGIATURA_FRANCESCO": "sceneggiatura_francesco",
        "RECITAZIONE_ANNIKA": "recitazione_annika",
        "RECITAZIONE_FRANCESCO": "recitazione_francesco",
        "GLOBALE_ANNIKA": "globale_annika",
        "GLOBALE_FRANCESCO": "globale_francesco",
        "MEDIA_ANNIKA": "media_annika",
        "MEDIA_FRANCESCO": "media_francesco",
        "VOTO FINALE": "voto_finale",
        "INDICE_CONFLITTO": "indice_conflitto",
    }

    for k in cols.keys():
        if k not in df.columns:
            df[k] = None

    df2 = df[list(cols.keys())].rename(columns=cols)

    engine = get_engine()
    existing = pd.read_sql_query("SELECT titolo, anno FROM films", engine)

    existing_titles = existing["titolo"].fillna("").astype(str).str.strip().str.lower()
    existing_years = existing["anno"].fillna(-1).astype(int)
    existing_keys = set(zip(existing_titles.tolist(), existing_years.tolist()))

    new_titles = df2["titolo"].fillna("").astype(str).str.strip().str.lower()
    new_years = df2["anno"].fillna(-1).astype(int)

    mask_new = []
    for t, y in zip(new_titles.tolist(), new_years.tolist()):
        mask_new.append((t, y) not in existing_keys)

    df_new = df2[pd.Series(mask_new, index=df2.index)]

    if len(df_new) > 0:
        df_new.to_sql("films", engine, if_exists="append", index=False)


def load_all():
    engine = get_engine()
    return pd.read_sql_query("SELECT * FROM films", engine)


def compute_scores(regia_a, regia_f, foto_a, foto_f, scen_a, scen_f, rec_a, rec_f, glob_a, glob_f):
    media_a = (regia_a + foto_a + scen_a + rec_a + glob_a) / 5
    media_f = (regia_f + foto_f + scen_f + rec_f + glob_f) / 5
    voto_finale = (media_a + media_f) / 2
    indice_conflitto = (
        abs(regia_a - regia_f)
        + abs(foto_a - foto_f)
        + abs(scen_a - scen_f)
        + abs(rec_a - rec_f)
        + abs(glob_a - glob_f)
    ) / 5
    return media_a, media_f, voto_finale, indice_conflitto


# ---------------- TAB 1: IMPORT ----------------
with tab1:
    st.subheader("Importa Excel/CSV")

    up = st.file_uploader("Carica un file", type=["xlsx", "xls", "csv"], key="import_uploader")

    if up is not None:
        try:
            import tempfile

            if up.name.lower().endswith((".xlsx", ".xls")):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp.write(up.getbuffer())
                    tmp_path = tmp.name
                df = parse_excel_like_yours(tmp_path)
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    tmp.write(up.getbuffer())
                    tmp_path = tmp.name
                df = normalize_canonical_csv(tmp_path)

            st.success(f"Letti {len(df)} film.")
            st.write("Anteprima (prime 30 righe):")
            st.dataframe(df.head(30), use_container_width=True)

            if st.button("Importa nel database", key="btn_import_db"):
                insert_df(df)
                st.success("Import completato nel database (duplicati evitati).")
                st.rerun()

        except Exception as e:
            st.error(str(e))


# ---------------- TAB 2: INSERISCI FILM ----------------
with tab2:
    st.subheader("Inserisci un film")

    titolo = st.text_input("Titolo", key="new_titolo")
    regista = st.text_input("Regista (facoltativo)", key="new_regista")
    anno = st.number_input("Anno", 1800, 2100, 2000, key="new_anno")
    note = st.text_area("Note", key="new_note")

    st.markdown("### Voti (0–5)")

    def v(label, k):
        a, f = st.columns(2)
        with a:
            va = st.number_input(f"{label} — Annika", 0.0, 5.0, 0.0, 0.5, key=f"{k}_a")
        with f:
            vf = st.number_input(f"{label} — Francesco", 0.0, 5.0, 0.0, 0.5, key=f"{k}_f")
        return va, vf

    regia_a, regia_f = v("Regia", "new_regia")
    foto_a,  foto_f  = v("Fotografia", "new_foto")
    scen_a,  scen_f  = v("Sceneggiatura", "new_scen")
    rec_a,   rec_f   = v("Recitazione", "new_rec")
    glob_a,  glob_f  = v("Globale", "new_glob")

    media_a, media_f, voto_finale, indice_conflitto = compute_scores(
        regia_a, regia_f, foto_a, foto_f, scen_a, scen_f, rec_a, rec_f, glob_a, glob_f
    )

    st.info(
        f"Media Annika: {media_a:.2f} | "
        f"Media Francesco: {media_f:.2f} | "
        f"Voto finale: {voto_finale:.2f}"
    )

    if st.button("Salva film", key="btn_save_new"):
        if not titolo.strip():
            st.error("Metti almeno il titolo.")
        else:
            row = pd.DataFrame([{
                "FILM_RAW": titolo,
                "TITOLO": titolo,
                "REGISTA": regista if regista else None,
                "PAESE": None,
                "ANNO": int(anno) if anno else None,
                "NOTE": note if note else None,
                "REGIA_ANNIKA": regia_a, "REGIA_FRANCESCO": regia_f,
                "FOTOGRAFIA_ANNIKA": foto_a, "FOTOGRAFIA_FRANCESCO": foto_f,
                "SCENEGGIATURA_ANNIKA": scen_a, "SCENEGGIATURA_FRANCESCO": scen_f,
                "RECITAZIONE_ANNIKA": rec_a, "RECITAZIONE_FRANCESCO": rec_f,
                "GLOBALE_ANNIKA": glob_a, "GLOBALE_FRANCESCO": glob_f,
                "MEDIA_ANNIKA": media_a,
                "MEDIA_FRANCESCO": media_f,
                "VOTO FINALE": voto_finale,
                "INDICE_CONFLITTO": indice_conflitto
            }])
            insert_df(row)
            st.success("Film salvato.")
            st.rerun()


# ---------------- TAB 3: CLASSIFICHE ----------------
with tab3:
    st.subheader("Classifiche")

    query = st.text_input("Cerca film", key="search_title")
    df = load_all()

    if query:
        df = df[df["titolo"].astype(str).str.contains(query, case=False, na=False)]

    st.write("Totale film (dopo filtro):", len(df))

    if df.empty:
        st.warning("Nessun film trovato (o database vuoto).")
    else:
        df["fotografia_media"] = df[["fotografia_annika", "fotografia_francesco"]].mean(axis=1)
        df["regia_media"] = df[["regia_annika", "regia_francesco"]].mean(axis=1)
        df["sceneggiatura_media"] = df[["sceneggiatura_annika", "sceneggiatura_francesco"]].mean(axis=1)
        df["recitazione_media"] = df[["recitazione_annika", "recitazione_francesco"]].mean(axis=1)
        df["globale_media"] = df[["globale_annika", "globale_francesco"]].mean(axis=1)

        c1, c2, c3 = st.columns(3)

        with c2:
            metrica = st.selectbox("Classifica per", [
                "voto_finale", "fotografia_media", "regia_media",
                "sceneggiatura_media", "recitazione_media", "globale_media",
            ], key="rank_metric")

        with c3:
            ordine = st.selectbox("Ordine", ["desc", "asc"], key="rank_order")

        n = len(df)
        with c1:
            if n <= 1:
                topn = n
                st.caption("Pochi risultati: mostro tutto.")
            else:
                topn = st.slider("Quanti risultati", 1, n, min(n, 50), key="rank_topn")

        asc = (ordine == "asc")
        view = df.sort_values(by=[metrica], ascending=asc, na_position="last").head(topn)
        view = view.reset_index(drop=True)
        view.index = view.index + 1
        view = view.rename_axis("posizione")

        st.dataframe(
            view[["titolo", "anno", metrica, "media_annika", "media_francesco", "note"]],
            use_container_width=True
        )


# ---------------- TAB 4: GESTISCI ----------------
with tab4:
    st.subheader("Gestisci archivio (modifica + storico)")

    df = load_all()

    if df.empty:
        st.warning("Database vuoto.")
    else:
        df_sorted = df.sort_values(["titolo", "anno"], na_position="last").reset_index(drop=True)

        labels = df_sorted.apply(
            lambda r: f'{r["titolo"]} ({int(r["anno"]) if pd.notna(r["anno"]) else "?"})',
            axis=1
        ).tolist()
        ids = df_sorted["id"].astype(int).tolist()

        pick = st.selectbox("Scegli film", range(len(labels)), format_func=lambda i: labels[i], key="manage_pick")
        film_id = int(ids[pick])
        row = df_sorted[df_sorted["id"] == film_id].iloc[0]

        st.divider()

        changed_by = st.selectbox("Chi sta modificando", ["Francesco", "Annika"], key="manage_by")
        motivo = st.text_input("Motivo (facoltativo)", key="manage_reason")

        k = f"film_{film_id}"

        st.markdown("### Dati film")
        titolo_new = st.text_input("Titolo", value=row["titolo"], key=f"{k}_titolo")
        anno_default = int(row["anno"]) if pd.notna(row["anno"]) else 2000
        anno_new = st.number_input("Anno", 1800, 2100, anno_default, key=f"{k}_anno")
        note_new = st.text_area("Note", value=row.get("note") or "", key=f"{k}_note")

        st.markdown("### Voti (0–5)")
        cA, cF = st.columns(2)

        with cA:
            regia_a = st.number_input("Regia — Annika", 0.0, 5.0, float(row["regia_annika"] or 0), 0.5, key=f"{k}_regia_a")
            foto_a  = st.number_input("Fotografia — Annika", 0.0, 5.0, float(row["fotografia_annika"] or 0), 0.5, key=f"{k}_foto_a")
            scen_a  = st.number_input("Sceneggiatura — Annika", 0.0, 5.0, float(row["sceneggiatura_annika"] or 0), 0.5, key=f"{k}_scen_a")
            rec_a   = st.number_input("Recitazione — Annika", 0.0, 5.0, float(row["recitazione_annika"] or 0), 0.5, key=f"{k}_rec_a")
            glob_a  = st.number_input("Globale — Annika", 0.0, 5.0, float(row["globale_annika"] or 0), 0.5, key=f"{k}_glob_a")

        with cF:
            regia_f = st.number_input("Regia — Francesco", 0.0, 5.0, float(row["regia_francesco"] or 0), 0.5, key=f"{k}_regia_f")
            foto_f  = st.number_input("Fotografia — Francesco", 0.0, 5.0, float(row["fotografia_francesco"] or 0), 0.5, key=f"{k}_foto_f")
            scen_f  = st.number_input("Sceneggiatura — Francesco", 0.0, 5.0, float(row["sceneggiatura_francesco"] or 0), 0.5, key=f"{k}_scen_f")
            rec_f   = st.number_input("Recitazione — Francesco", 0.0, 5.0, float(row["recitazione_francesco"] or 0), 0.5, key=f"{k}_rec_f")
            glob_f  = st.number_input("Globale — Francesco", 0.0, 5.0, float(row["globale_francesco"] or 0), 0.5, key=f"{k}_glob_f")

        media_a, media_f, voto_finale, indice_conflitto = compute_scores(
            regia_a, regia_f, foto_a, foto_f, scen_a, scen_f, rec_a, rec_f, glob_a, glob_f
        )

        st.info(f"Nuovo voto finale: {voto_finale:.2f} | Conflitto: {indice_conflitto:.2f}")

        if st.button("Salva modifiche (con storico)", key=f"{k}_save"):
            with get_conn() as conn:
                conn.execute(text("""
                    INSERT INTO film_history (
                        film_id, changed_at, changed_by,
                        titolo, anno, note,
                        regia_annika, regia_francesco,
                        fotografia_annika, fotografia_francesco,
                        sceneggiatura_annika, sceneggiatura_francesco,
                        recitazione_annika, recitazione_francesco,
                        globale_annika, globale_francesco,
                        media_annika, media_francesco,
                        voto_finale, indice_conflitto
                    ) VALUES (
                        :film_id, :changed_at, :changed_by,
                        :titolo, :anno, :note,
                        :regia_annika, :regia_francesco,
                        :fotografia_annika, :fotografia_francesco,
                        :sceneggiatura_annika, :sceneggiatura_francesco,
                        :recitazione_annika, :recitazione_francesco,
                        :globale_annika, :globale_francesco,
                        :media_annika, :media_francesco,
                        :voto_finale, :indice_conflitto
                    )
                """), {
                    "film_id": film_id,
                    "changed_at": datetime.datetime.now().isoformat(timespec="seconds"),
                    "changed_by": f"{changed_by}{' — ' + motivo if motivo else ''}",
                    "titolo": row.get("titolo"),
                    "anno": int(row["anno"]) if pd.notna(row["anno"]) else None,
                    "note": row.get("note"),
                    "regia_annika": row.get("regia_annika"), "regia_francesco": row.get("regia_francesco"),
                    "fotografia_annika": row.get("fotografia_annika"), "fotografia_francesco": row.get("fotografia_francesco"),
                    "sceneggiatura_annika": row.get("sceneggiatura_annika"), "sceneggiatura_francesco": row.get("sceneggiatura_francesco"),
                    "recitazione_annika": row.get("recitazione_annika"), "recitazione_francesco": row.get("recitazione_francesco"),
                    "globale_annika": row.get("globale_annika"), "globale_francesco": row.get("globale_francesco"),
                    "media_annika": row.get("media_annika"), "media_francesco": row.get("media_francesco"),
                    "voto_finale": row.get("voto_finale"), "indice_conflitto": row.get("indice_conflitto"),
                })

                conn.execute(text("""
                    UPDATE films SET
                        titolo=:titolo, anno=:anno, note=:note,
                        regia_annika=:regia_annika, regia_francesco=:regia_francesco,
                        fotografia_annika=:fotografia_annika, fotografia_francesco=:fotografia_francesco,
                        sceneggiatura_annika=:sceneggiatura_annika, sceneggiatura_francesco=:sceneggiatura_francesco,
                        recitazione_annika=:recitazione_annika, recitazione_francesco=:recitazione_francesco,
                        globale_annika=:globale_annika, globale_francesco=:globale_francesco,
                        media_annika=:media_annika, media_francesco=:media_francesco,
                        voto_finale=:voto_finale, indice_conflitto=:indice_conflitto
                    WHERE id=:id
                """), {
                    "titolo": titolo_new,
                    "anno": int(anno_new) if anno_new else None,
                    "note": note_new,
                    "regia_annika": regia_a, "regia_francesco": regia_f,
                    "fotografia_annika": foto_a, "fotografia_francesco": foto_f,
                    "sceneggiatura_annika": scen_a, "sceneggiatura_francesco": scen_f,
                    "recitazione_annika": rec_a, "recitazione_francesco": rec_f,
                    "globale_annika": glob_a, "globale_francesco": glob_f,
                    "media_annika": media_a, "media_francesco": media_f,
                    "voto_finale": voto_finale, "indice_conflitto": indice_conflitto,
                    "id": film_id,
                })

            st.success("Aggiornato. Versione precedente salvata in cronologia.")
            st.rerun()

        st.divider()
        st.markdown("### Cronologia modifiche")

        engine = get_engine()
        hist = pd.read_sql_query(
            "SELECT changed_at, changed_by, titolo, anno, voto_finale, note FROM film_history WHERE film_id=%(film_id)s ORDER BY id DESC",
            engine,
            params={"film_id": film_id}
        )

        if hist.empty:
            st.caption("Nessuna modifica registrata per questo film.")
        else:
            st.dataframe(hist, use_container_width=True)
