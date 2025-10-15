# Script para reordenar gntlemmas.json

import json

# Carregar o arquivo JSON
with open('gntlemmas.json', 'r') as file:
    data = json.load(file)

# Ordenar os dados
# Se o JSON contém um objeto (dicionário), ordene pelas chaves
if isinstance(data, dict):
    # ordered_data = {k: data[k] for k in sorted(data)}
		ordered_data = {k: v for k, v in sorted(data.items(), key=lambda item: int(item[1].get('strongs', 0)))}
# Se o JSON contém uma lista, você pode ordenar os elementos da lista
elif isinstance(data, list):
    ordered_data = sorted(data)

# Salvar o arquivo JSON reordenado
with open('gntlemmas.json', 'w') as file:
    json.dump(ordered_data, file, ensure_ascii=False, indent=4)

print("Arquivo JSON reordenado com sucesso!")
