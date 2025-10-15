#!/usr/bin/env python3
"""
CSV -> Nested JSON converter for Greek NT tokens
Input CSV must have columns: chapter, verse, text
Where text is a sequence like: "<greek> <strongs> {<morph>} ..." per token.
Output JSON shape:
[
  {
    "1": [
      {"1": [ {"greek": "...", "strongs":"...", "morph":"..."} ]},
      {"2": [ ... ]}
    ]
  },
  ...
]
> python3 convert_csv_to_nested_json.py caminho/entrada.csv caminho/saida.json
"""
import re, json, csv, sys
import pandas as pd
import itertools

def parse_tokens(text: str):
    pattern = re.compile(r'([^\s{}]+)\s+(\d+)\s+\{([^}]+)\}')
    return [{"greek": g, "strongs": s, "morph": m} for g, s, m in pattern.findall(text or "")]

def convert_csv_to_json(input_csv: str, output_json: str):
    df = pd.read_csv(input_csv)
    # map columns case-insensitively
    lower = {c.lower(): c for c in df.columns}
    try:
        df = df[[lower['chapter'], lower['verse'], lower['text']]].rename(columns={lower['chapter']:'chapter', lower['verse']:'verse', lower['text']:'text'})
    except KeyError:
        raise SystemExit(f"Erro: CSV precisa conter colunas chapter, verse e text (insensíveis a maiúsculas). Encontrado: {list(df.columns)}")
    df = df.sort_values(['chapter','verse'], kind='mergesort')
    result = []
    for chap, group in itertools.groupby(df.itertuples(index=False), key=lambda r: int(r.chapter)):
        verses_list = []
        for row in group:
            verses_list.append({str(int(row.verse)): parse_tokens(row.text)})
        result.append({str(int(chap)): verses_list})
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python convert_csv_to_nested_json.py <entrada.csv> <saida.json>")
        sys.exit(1)
    convert_csv_to_json(sys.argv[1], sys.argv[2])
    print(f"OK: arquivo JSON salvo em {sys.argv[2]}")
