#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, re, json, argparse, logging
from typing import List, Dict, Any, Tuple
import pandas as pd

GREEK_WORD_RE = re.compile(r'([\u0370-\u03FF\u1F00-\u1FFF]+)')

def setup_logger(verbose: bool, log_file: str = None):
    logger = logging.getLogger("lemmas_json_text_only")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("[%(levelname)s] %(message)s")
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    sh.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(sh)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
    return logger

def lower_map_cols(df: pd.DataFrame) -> Dict[str, str]:
    return {c.lower(): c for c in df.columns}

def parse_lemmas_text_only(text: str, logger, fallback_ws: bool):
    if not isinstance(text, str):
        return []
    words = GREEK_WORD_RE.findall(text)
    if not words and fallback_ws:
        parts = [w for w in (text or "").split() if w.strip()]
        return [{"lemma": w} for w in parts]
    return [{"lemma": w} for w in words]

def load_verses(path: str, logger):
    df = pd.read_csv(path)
    cmap = lower_map_cols(df)
    for k in ('chapter','verse','text'):
        if k not in cmap:
            logger.error(f"CSV de versículos precisa de colunas 'chapter','verse','text'. Encontrado: {list(df.columns)}")
            sys.exit(1)
    df = df[[cmap['chapter'], cmap['verse'], cmap['text']]].rename(
        columns={cmap['chapter']:'chapter',cmap['verse']:'verse',cmap['text']:'text'}
    )
    df['chapter'] = df['chapter'].astype(int)
    df['verse'] = df['verse'].astype(int)
    df = df.sort_values(['chapter','verse'], kind='mergesort')
    return df

def load_pericopes(path: str, logger):
    df = pd.read_csv(path)
    cmap = lower_map_cols(df)
    required = ['pericope_id','title','chapter','start_verse','end_verse']
    if not all(k in cmap for k in required):
        logger.error(f"CSV de perícopes precisa de colunas {required}. Encontrado: {list(df.columns)}")
        sys.exit(1)
    cols = [cmap['pericope_id'],cmap['title'],cmap['chapter'],cmap['start_verse'],cmap['end_verse']]
    if 'order' in cmap: cols.append(cmap['order'])
    df = df[cols].rename(columns={
        cmap['pericope_id']:'pericope_id',
        cmap['title']:'title',
        cmap['chapter']:'chapter',
        cmap['start_verse']:'start_verse',
        cmap['end_verse']:'end_verse',
        **({cmap['order']:'order'} if 'order' in cmap else {})
    })
    df['chapter'] = df['chapter'].astype(int)
    df['start_verse'] = df['start_verse'].astype(int)
    df['end_verse'] = df['end_verse'].astype(int)
    if 'order' in df.columns: df['order'] = df['order'].astype(int)
    if 'order' in df.columns:
        df = df.sort_values(['chapter','order','start_verse','end_verse'], kind='mergesort')
    else:
        df = df.sort_values(['chapter','start_verse','end_verse'], kind='mergesort')
    bad = df[df['start_verse'] > df['end_verse']]
    if not bad.empty:
        logger.error(f"Perícopes com start_verse > end_verse:\n{bad}")
        sys.exit(1)
    return df

def validate_pericopes(verses_df, peris_df, logger, require_full_coverage: bool):
    ok = True
    warnings = []
    last_verse = verses_df.groupby('chapter')['verse'].max().to_dict()
    for chap, grp in peris_df.groupby('chapter'):
        grp = grp.sort_values(['start_verse','end_verse'])
        last_end = 0
        for r in grp.itertuples(index=False):
            if r.start_verse <= last_end and last_end != 0:
                ok = False
                warnings.append(f"Cap {chap}: sobreposição: início {r.start_verse} sobrepõe {last_end}.")
            if r.start_verse != last_end + 1:
                msg = f"Cap {chap}: lacuna entre {last_end} e {r.start_verse}."
                warnings.append(msg)
                if require_full_coverage:
                    ok = False
            last_end = r.end_verse
        maxv = last_verse.get(chap, last_end)
        if last_end != maxv:
            msg = f"Cap {chap}: termina em {last_end}, mas deveria terminar em {maxv}."
            warnings.append(msg)
            if require_full_coverage:
                ok = False
    for r in peris_df.itertuples(index=False):
        maxv = last_verse.get(r.chapter, None)
        if maxv is None:
            ok = False
            warnings.append(f"Cap {r.chapter}: não há versos no CSV de versículos.")
            continue
        if r.end_verse > maxv:
            ok = False
            warnings.append(f"Cap {r.chapter}: perícope {r.pericope_id} termina em {r.end_verse} > {maxv}.")
    for w in warnings:
        logger.warning(w)
    return ok, warnings

def build_json(verses_df, pericopes_df, logger, fallback_ws: bool):
    chapters = []
    verses_by_chap = {c: g.copy() for c,g in verses_df.groupby('chapter')}
    peris_by_chap = {c: g.copy() for c,g in pericopes_df.groupby('chapter')}
    for chap in sorted(set(verses_by_chap) | set(peris_by_chap)):
        vdf = verses_by_chap.get(chap, pd.DataFrame(columns=['chapter','verse','text']))
        pdf = peris_by_chap.get(chap, pd.DataFrame(columns=['pericope_id','title','chapter','start_verse','end_verse']))
        if 'order' in pdf.columns:
            pdf = pdf.sort_values(['order','start_verse','end_verse'], kind='mergesort')
        else:
            pdf = pdf.sort_values(['start_verse','end_verse'], kind='mergesort')
        chapter_obj = {"chapter": int(chap), "pericopes": []}
        for row in pdf.itertuples(index=False):
            sel = vdf[(vdf['verse'] >= row.start_verse) & (vdf['verse'] <= row.end_verse)].sort_values('verse', kind='mergesort')
            verses_payload = []
            for r in sel.itertuples(index=False):
                tokens = parse_lemmas_text_only(r.text, logger, fallback_ws)
                if not tokens:
                    logger.warning(f"Nenhuma palavra grega detectada: cap {r.chapter}, v{r.verse}. Texto (início): {str(r.text)[:60]}")
                verses_payload.append({"verse": int(r.verse), "tokens": tokens})
            chapter_obj["pericopes"].append({
                "id": str(row.pericope_id),
                "title": str(row.title),
                "start_verse": int(row.start_verse),
                "end_verse": int(row.end_verse),
                "verses": verses_payload
            })
        chapters.append(chapter_obj)
    return chapters

def main():
    ap = argparse.ArgumentParser(description="CSV texto (chapter,verse,text) + perícopes -> JSON (lemmas)")
    ap.add_argument("verses_csv")
    ap.add_argument("pericopes_csv")
    ap.add_argument("out_json")
    ap.add_argument("--verbose","-v", action="store_true")
    ap.add_argument("--require-full-coverage", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--log-file")
    ap.add_argument("--fallback-whitespace", action="store_true")
    args = ap.parse_args()

    logger = setup_logger(args.verbose, args.log_file)
    logger.info("Lendo arquivos...")
    verses_df = load_verses(args.verses_csv, logger)
    pericopes_df = load_pericopes(args.pericopes_csv, logger)

    logger.info("Validando perícopes...")
    ok, warnings = validate_pericopes(verses_df, pericopes_df, logger, args.require_full_coverage)
    logger.info(f"Resumo: capítulos={verses_df['chapter'].nunique()}, versos={len(verses_df)}, perícopes={len(pericopes_df)}, avisos={len(warnings)}")
    if args.strict and warnings:
        logger.error("Modo --strict: falhando devido a avisos.")
        sys.exit(2)

    logger.info("Construindo JSON...")
    data = build_json(verses_df, pericopes_df, logger, args.fallback_whitespace)
    with open(args.out_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"OK: JSON salvo em {args.out_json}")

if __name__ == "__main__":
    main()
