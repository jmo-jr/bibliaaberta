#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV -> JSON (Capítulos com Perícopes)

Entrada:
  1) CSV de versículos (obrigatório): colunas case-insensitive: chapter, verse, text
     - text no formato: "<greek> <strongs> {<morph>} ..." repetido
  2) CSV de perícopes (obrigatório): colunas case-insensitive:
       pericope_id, title, chapter, start_verse, end_verse
     - Perícopes devem estar contidas em um único capítulo.
     - Opcional: coluna 'order' para ordenar perícopes dentro do capítulo.
       (se ausente, serão ordenadas por start_verse crescente)

Saída (JSON):
[
  {
    "chapter": 1,
    "pericopes": [
      {
        "id": "P001",
        "title": "Saudação",
        "start_verse": 1,
        "end_verse": 3,
        "verses": [
          {"verse": 1, "tokens": [ {"greek": "...", "strongs": "...", "morph": "..."}, ... ]},
          {"verse": 2, "tokens": [ ... ]},
          {"verse": 3, "tokens": [ ... ]}
        ]
      },
      ...
    ]
  },
  ...
]

Uso:
  python convert_csv_with_pericopes.py versos.csv pericopes.csv saida.json

Observações:
  - O script valida sobreposição e ordem de perícopes por capítulo e emite avisos.
  - Versículos fora de qualquer perícope ficam de fora por padrão (comportamento típico de edições com perícopes contínuas). 
    Se desejar incluí-los, ajuste a função build_chapter_structure para criar uma perícope "Sem Título" cobrindo lacunas.
"""
import sys
import json
import re
from typing import List, Dict, Any, Tuple
import pandas as pd

def _lower_map_cols(df: pd.DataFrame) -> Dict[str, str]:
    """Mapeia nomes de colunas (case-insensitive) para o nome real no DataFrame."""
    return {c.lower(): c for c in df.columns}

TOKEN_RE = re.compile(r'([^\s{}]+)\s+(\d+)\s+\{([^}]+)\}')

def parse_tokens(text: str) -> List[Dict[str, str]]:
    """Extrai tokens no formato '<greek> <strongs> {<morph>}'."""
    if not isinstance(text, str):
        return []
    return [{"greek": g, "strongs": s, "morph": m} for g, s, m in TOKEN_RE.findall(text)]

def load_verses(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    cmap = _lower_map_cols(df)
    required = ['chapter','verse','text']
    if not all(k in cmap for k in required):
        raise SystemExit(f"Erro: CSV de versículos precisa ter colunas: {required}. Encontrado: {list(df.columns)}")
    df = df[[cmap['chapter'], cmap['verse'], cmap['text']]].rename(columns={cmap['chapter']:'chapter', cmap['verse']:'verse', cmap['text']:'text'})
    # Tipos e ordenação
    df['chapter'] = df['chapter'].astype(int)
    df['verse'] = df['verse'].astype(int)
    df = df.sort_values(['chapter','verse'], kind='mergesort')
    return df

def load_pericopes(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    cmap = _lower_map_cols(df)
    required = ['pericope_id','title','chapter','start_verse','end_verse']
    if not all(k in cmap for k in required):
        raise SystemExit(f"Erro: CSV de perícopes precisa ter colunas: {required}. Encontrado: {list(df.columns)}")
    cols = [cmap['pericope_id'], cmap['title'], cmap['chapter'], cmap['start_verse'], cmap['end_verse']]
    if 'order' in cmap:
        cols.append(cmap['order'])
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
    if 'order' in df.columns:
        df['order'] = df['order'].astype(int)
    # Ordenação padrão
    if 'order' in df.columns:
        df = df.sort_values(['chapter','order','start_verse','end_verse'], kind='mergesort')
    else:
        df = df.sort_values(['chapter','start_verse','end_verse'], kind='mergesort')
    # Validação simples: start <= end
    bad = df[df['start_verse'] > df['end_verse']]
    if not bad.empty:
        raise SystemExit(f"Erro: há perícopes com start_verse > end_verse:\n{bad}")
    return df

def detect_overlaps(peris: pd.DataFrame) -> List[Tuple[int, str]]:
    """Retorna lista de (chapter, msg) com avisos de sobreposição de intervalos dentro do capítulo."""
    warnings = []
    for chap, g in peris.groupby('chapter'):
        intervals = g[['start_verse','end_verse']].to_records(index=False).tolist()
        intervals_sorted = sorted(intervals)
        # Checar sobreposição
        last_end = -10**9
        for (s,e) in intervals_sorted:
            if s <= last_end:
                warnings.append((chap, f"Perícopes sobrepostas em capítulo {chap}: intervalo que começa em {s} sobrepõe o final {last_end}."))
            last_end = max(last_end, e)
    return warnings

def build_chapter_structure(verses_df: pd.DataFrame, pericopes_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Constrói a estrutura final por capítulo -> perícopes -> versículos (tokenizados)."""
    chapters = []
    # Grupo de versículos por capítulo
    verses_by_chap = {chap: g.copy() for chap, g in verses_df.groupby('chapter')}
    peris_by_chap = {chap: g.copy() for chap, g in pericopes_df.groupby('chapter')}
    all_chaps = sorted(set(verses_by_chap.keys()) | set(peris_by_chap.keys()))
    for chap in all_chaps:
        chapter_block: Dict[str, Any] = {"chapter": chap, "pericopes": []}
        vdf = verses_by_chap.get(chap, pd.DataFrame(columns=['chapter','verse','text']))
        pdf = peris_by_chap.get(chap, pd.DataFrame(columns=['pericope_id','title','chapter','start_verse','end_verse']))
        # Ordenação definitiva dentro do capítulo
        if 'order' in pdf.columns:
            pdf = pdf.sort_values(['order','start_verse','end_verse'], kind='mergesort')
        else:
            pdf = pdf.sort_values(['start_verse','end_verse'], kind='mergesort')
        # Montar perícopes
        for row in pdf.itertuples(index=False):
            sid = getattr(row, 'pericope_id')
            title = getattr(row, 'title')
            start_v = int(getattr(row, 'start_verse'))
            end_v   = int(getattr(row, 'end_verse'))
            # Selecionar versículos
            sel = vdf[(vdf['verse'] >= start_v) & (vdf['verse'] <= end_v)].sort_values('verse', kind='mergesort')
            verses_payload = [{"verse": int(r.verse), "tokens": parse_tokens(r.text)} for r in sel.itertuples(index=False)]
            chapter_block["pericopes"].append({
                "id": str(sid),
                "title": str(title),
                "start_verse": start_v,
                "end_verse": end_v,
                "verses": verses_payload
            })
        chapters.append(chapter_block)
    return chapters

def main():
    if len(sys.argv) < 4:
        print("Uso: python convert_csv_with_pericopes.py <versos.csv> <pericopes.csv> <saida.json>")
        sys.exit(1)
    verses_csv, pericopes_csv, out_json = sys.argv[1], sys.argv[2], sys.argv[3]
    verses_df = load_verses(verses_csv)
    pericopes_df = load_pericopes(pericopes_csv)

    # Valida sobreposição simples e ordem
    overlaps = detect_overlaps(pericopes_df)
    for chap, msg in overlaps:
        print(f"AVISO: {msg}")

    result = build_chapter_structure(verses_df, pericopes_df)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"OK: JSON salvo em {out_json}")

if __name__ == "__main__":
    main()
