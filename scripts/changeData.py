from bs4 import BeautifulSoup
import json
import sys
import os

# Substituir por chamada pelo terminal
# Verifica se o argumento do caminho do arquivo HTML foi fornecido
if len(sys.argv) < 2:
    sys.exit(1)

# Caminho do arquivo HTML a partir do argumento da linha de comando
# html_file_path = 'nt-interlinear/src/nt/lucas/03.html'
file_url = sys.argv[1]

with open(file_url, 'r', encoding='utf-8') as html_file:
    html_content = html_file.read()

with open('data/gntlemmas.json', 'r', encoding='utf-8') as json_file:
    dictionary = json.load(json_file)

# Parse do HTML
soup = BeautifulSoup(html_content, 'lxml')

# Encontrar todas as spans com a classe 'greek'
term_container = soup.find_all('span', class_='greek')

# Percorrer cada span.greek encontrada
for term_span in term_container:
    term = term_span.get_text(strip=True)
    
    # Verificar se o texto está no dicionário
    if term in dictionary:
        term_meta = dictionary[term]
        
        # Encontrar o elemento-pai (table com a classe 'tablefloatleft')
        parent_table = term_span.find_parent('table', class_='tablefloatleft')
        
        # Verificar se o elemento-pai existe
        if parent_table:
            # Encontrar os elementos específicos dentro do elemento-pai
            strong_parent = parent_table.find('span', class_='pos')
            definition = strong_parent.find('a') if strong_parent else None
            
            translit_parent = parent_table.find('span', class_='translit')
            translit = translit_parent.find('a') if translit_parent else None
            
            translation = parent_table.find('span', class_='eng')

            grammar_parent = parent_table.find('span', class_='strongsnt')
            grammar = grammar_parent.find('a') if grammar_parent else None
            
            # Substitui o conteúdo de cada item pelo dado apontado do json 
            # span.pos > a
            if definition:
                definition['href'] = '/greek/' + term_meta.get('strongs') + '.html'
                definition['title'] = term_meta.get('verbete', definition.get('title'))
                definition.string = term_meta.get('strongs', definition.string)
            # span.translit > a
            if translit:
                translit['title'] = term_meta.get('ocorrencia', translit.get('title'))
                translit.string = term_meta.get('transliteracao', translit.string)
            # span.eng
            if translation:
                translation.string = term_meta.get('traducao', translation.string)
            # span.strongsnt > a
            if grammar:
                grammar['title'] = term_meta.get('desgram', grammar.get('title'))
                grammar.string = term_meta.get('classegram', grammar.string)	

# Salvar as mudanças no HTML
with open(file_url, 'w', encoding='utf-8') as updated_html_file:
    updated_html_file.write(str(soup))
