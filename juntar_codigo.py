import os

IGNORAR = ['entorno', 'venv', '__pycache__', 'migrations', '.git', 'static', 'media']

with open('mi_codigo_completo.txt', 'w', encoding='utf-8') as outfile:
    for root, dirs, files in os.walk('.'):
        # Saltamos las carpetas ignoradas
        if any(ignorado in root for ignorado in IGNORAR):
            continue

        for file in files:
            # Solo leemos Python y HTML
            if file.endswith(('.py', '.html')):
                filepath = os.path.join(root, file)
                outfile.write(f'\n\n{"="*60}\n')
                outfile.write(f'ARCHIVO: {filepath}\n')
                outfile.write(f'{"="*60}\n\n')
                try:
                    with open(filepath, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"Error leyendo archivo: {e}\n")

print("¡Listo! Se creó el archivo mi_codigo_completo.txt")
