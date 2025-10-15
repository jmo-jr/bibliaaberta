#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# > python3 convert_to_lemmas_json.py brutos/text/versos.csv brutos/indices/pericopes.csv saida.json
import sys, re, json
from typing import List, Dict, Any
import pandas as pd

def _lower_map_cols(df: pd.DataFrame) -> Dict[str, str]:
    return {c.lower(): c for c in df.columns}

TOKEN_RE = re.compile(r'([^\s{}]+)\s+\d+\s+\{[^}]+\}')

def parse_lemmas(text: str) -> List[Dict[str, str]]:
    if not isinstance(text, str):
        return []
    lemmas = TOKEN_RE.findall(text)
    return [{"lemma": w} for w in lemmas]

def load_verses(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    cmap = _lower_map_cols(df)
    for k in ('chapter','verse','text'):
        if k not in cmap:
            raise SystemExit(f"CSV de versículos precisa de colunas 'chapter','verse','text'. Encontrado: {list(df.columns)}")
    df = df[[cmap['chapter'], cmap['verse'], cmap['text']]].rename(columns={cmap['chapter']:'chapter',cmap['verse']:'verse',cmap['text']:'text'})
    df['chapter'] = df['chapter'].astype(int)
    df['verse'] = df['verse'].astype(int)
    df = df.sort_values(['chapter','verse'], kind='mergesort')
    return df

def load_pericopes(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    cmap = _lower_map_cols(df)
    required = ['pericope_id','title','chapter','start_verse','end_verse']
    if not all(k in cmap for k in required):
        raise SystemExit(f"CSV de perícopes precisa de colunas {required}. Encontrado: {list(df.columns)}")
    cols = [cmap['pericope_id'],cmap['title'],cmap['chapter'],cmap['start_verse'],cmap['end_verse']]
    if 'order' in cmap: cols.append(cmap['order'])
    rename_map = {
        cmap['pericope_id']:'pericope_id',
        cmap['title']:'title',
        cmap['chapter']:'chapter',
        cmap['start_verse']:'start_verse',
        cmap['end_verse']:'end_verse',
    }
    if 'order' in cmap:
        rename_map[cmap['order']] = 'order'
    df = df[cols].rename(columns=rename_map)
    df['chapter'] = df['chapter'].astype(int)
    df['start_verse'] = df['start_verse'].astype(int)
    df['end_verse'] = df['end_verse'].astype(int)
    if 'order' in df.columns: df['order'] = df['order'].astype(int)
    if 'order' in df.columns:
        df = df.sort_values(['chapter','order','start_verse','end_verse'], kind='mergesort')
    else:
        df = df.sort_values(['chapter','start_verse','end_verse'], kind='mergesort')
    return df

def build_json(verses_df: pd.DataFrame, pericopes_df: pd.DataFrame) -> List[Dict[str, Any]]:
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
            verses_payload = [{"verse": int(r.verse), "tokens": parse_lemmas(r.text)} for r in sel.itertuples(index=False)]
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
    if len(sys.argv) < 4:
        print("Uso: python convert_to_lemmas_json.py <versos.csv> <pericopes.csv> <saida.json>")
        sys.exit(1)
    verses_csv, pericopes_csv, out_json = sys.argv[1], sys.argv[2], sys.argv[3]
    verses_df = load_verses(verses_csv)
    pericopes_df = load_pericopes(pericopes_csv)
    data = build_json(verses_df, pericopes_df)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"OK: JSON salvo em {out_json}")
