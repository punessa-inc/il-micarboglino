import re
import pandas as pd
import numpy as np


def find_header_row(raw_df, max_scan=25):
    for i in range(min(max_scan, len(raw_df))):
        row = raw_df.iloc[i].astype(str).str.upper().tolist()
        if any("REGIA A" in c for c in row) and any("REGIA F" in c for c in row):
            return i
    return None


def parse_excel_like_yours(xlsx_path: str) -> pd.DataFrame:
    raw = pd.read_excel(xlsx_path, header=None)
    hr = find_header_row(raw)

    if hr is None:
        raise ValueError("Non trovo la riga intestazioni (REGIA A / REGIA F).")

    df = pd.read_excel(xlsx_path, header=hr)

    # Rinomina prima colonna in FILM_RAW
    first = df.columns[0]
    df = df.rename(columns={first: "FILM_RAW"})

    # Rimuove colonne Unnamed completamente vuote
    for c in list(df.columns):
        if str(c).startswith("Unnamed") and df[c].isna().all():
            df = df.drop(columns=[c])

    df = df.dropna(how="all")

    # Mappa A/F → Annika/Francesco
    rename_map = {
        "REGIA A": "REGIA_ANNIKA",
        "REGIA F": "REGIA_FRANCESCO",
        "FOTOGRAFIA A": "FOTOGRAFIA_ANNIKA",
        "FOTOGRAFIA F": "FOTOGRAFIA_FRANCESCO",
        "SCENEGGIATURA A": "SCENEGGIATURA_ANNIKA",
        "SCENEGGIATURA F": "SCENEGGIATURA_FRANCESCO",
        "RECITAZIONE A": "RECITAZIONE_ANNIKA",
        "RECITAZIONE F": "RECITAZIONE_FRANCESCO",
        "GLOBALE A": "GLOBALE_ANNIKA",
        "GLOBALE F": "GLOBALE_FRANCESCO",
        "MEDIA A": "MEDIA_ANNIKA",
        "MEDIA F": "MEDIA_FRANCESCO",
    }
    df = df.rename(columns=rename_map)

    # Parsing testo film: "TITOLO - REGISTA, PAESE 1975"
    def parse_film(s):
        if pd.isna(s):
            return (np.nan, np.nan, np.nan, np.nan)

        s = str(s).strip().replace("–", "-").replace("—", "-")
        parts = [p.strip() for p in s.split("-", 1)]

        titolo = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""

        regista = None
        paese = None
        anno = None

        if rest:
            m = re.match(r"^(.*?),(.*)$", rest)
            if m:
                regista = m.group(1).strip()
                tail = m.group(2).strip()
            else:
                regista = rest.strip()
                tail = ""

            ym = re.search(r"(19\d{2}|20\d{2})", tail)
            if ym:
                anno = int(ym.group(1))

            tail_no_year = re.sub(r"(19\d{2}|20\d{2})", "", tail)
            tail_no_year = tail_no_year.replace(",", " ").strip()
            paese = tail_no_year or None

        return (titolo, regista, paese, anno)

    parsed = df["FILM_RAW"].apply(parse_film)
    df[["TITOLO", "REGISTA", "PAESE", "ANNO"]] = pd.DataFrame(parsed.tolist(), index=df.index)

    # Conversione numerica colonne voto
    num_cols = [c for c in df.columns if any(k in c for k in [
        "REGIA_", "FOTOGRAFIA_", "SCENEGGIATURA_", "RECITAZIONE_", "GLOBALE_", "MEDIA_"
    ])]
    if "VOTO FINALE" in df.columns:
        num_cols.append("VOTO FINALE")

    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Indice conflitto
    cats = ["REGIA", "FOTOGRAFIA", "SCENEGGIATURA", "RECITAZIONE", "GLOBALE"]
    diffs = []
    for cat in cats:
        a = df.get(cat + "_ANNIKA")
        f = df.get(cat + "_FRANCESCO")
        if a is not None and f is not None:
            diffs.append((a - f).abs())
    if diffs:
        df["INDICE_CONFLITTO"] = pd.concat(diffs, axis=1).mean(axis=1)

    # NOTE sempre presente
    if "NOTE" not in df.columns:
        df["NOTE"] = None

    return df


def normalize_canonical_csv(csv_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_path)
