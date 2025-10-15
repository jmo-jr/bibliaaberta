# -*- coding: utf-8 -*-
# Script para gerar o arquivo nti.json (?)
# EXECUTAR NO TERMINAL ANTES DE EXEC O SCRIPT
# virtualenv venv
# source venv/bin/activate
import json
import sys
from bs4 import BeautifulSoup
import os

# Função para carregar o JSON existente
def load_existing_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Função para salvar o JSON atualizado
def save_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Caminho do arquivo JSON
json_file_path = 'nti.json'

# Carregar o JSON existente
jsonNT = load_existing_json(json_file_path)

# Verifica se o argumento do caminho do arquivo HTML foi fornecido
if len(sys.argv) < 2:
    sys.exit(1)

# Caminho do arquivo HTML a partir do argumento da linha de comando
# html_file_path = 'nt-interlinear/src/nt/lucas/03.html'
html_file_path = sys.argv[1]

# Ler o conteúdo do arquivo HTML
with open(html_file_path, 'r', encoding='utf-8') as file:
    html_content = file.read()

# Faz o parsing do HTML com BeautifulSoup
soup = BeautifulSoup(html_content, 'html.parser')

# Encontra todos os tds com a classe indicada
for td in soup.find_all("table", class_="tablefloatleft"):
    #print(td)
    pos_span = td.find("span", class_="pos")
    a_pos = pos_span.find("a") if pos_span else None

    if a_pos:
        numero_strong = a_pos.text
        title = a_pos.get('title')
    
        # Verifica se a chave já existe no dicionário
        if numero_strong not in jsonNT:
            # Busca a transliteração de maneira segura
            transliteracao = None
            translit_span = td.find("span", class_="translit")
            if translit_span:
                a_translit = translit_span.find("a")
                if a_translit:
                    transliteracao = a_translit.text
                    translit_title = a_translit.get('title')
                    
            # Continua com as outras buscas
            greek = None
            greek_span = td.find("span", class_="greek")
            if greek_span:
              greek = greek_span.text
            
            traducao = td.find("span", class_="eng").text

            strongsnt = None
            gnt_span = td.find("span", class_="strongsnt")
            if gnt_span:
              a_gnt = gnt_span.find("a")
              if a_gnt:
                strongsnt = a_gnt.text
                strongsnt_title = a_gnt.get('title')

            # Adiciona os dados ao dicionário
            jsonNT[numero_strong] = {
                "strongs": numero_strong,
                "grego": greek,
                "transliteracao": transliteracao,
                "traducao": traducao,
                "verbete": title,
                "ocorrencia": translit_title,
                "classegram": strongsnt,
                "desgram": strongsnt_title,
            }

# Salvar o JSON atualizado de volta no arquivo
save_json(jsonNT, json_file_path)
