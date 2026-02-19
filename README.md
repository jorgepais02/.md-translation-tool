# .MD Translation Tool

Pipeline automático para **traducir apuntes en Markdown** a múltiples idiomas y generar documentos **Word (.docx)** y **PDF** con formato académico.

## Características

- **Traducción automática** a 4 idiomas (inglés, francés, árabe, chino) con la API de DeepL
- **Generación de DOCX** con formato académico (Times New Roman, márgenes, numeración de página)
- **Generación de PDF** local vía LibreOffice (sin APIs externas)
- **Soporte RTL** para árabe (dirección de texto derecha-a-izquierda)
- **Tipografía CJK** (SimSun) para chino
- **Imagen de cabecera** automática en todos los documentos

## Estructura

```
├── src/
│   ├── translation_pipeline.py   # Orquestador: traduce con DeepL + genera documentos
│   └── document_generator.py     # Generador de DOCX con formato académico
├── sources/                      # Archivos .md de entrada
├── public/
│   └── header.png                # Imagen de cabecera para los documentos
├── translated/                   # Salida generada (gitignored)
│   ├── es/es.md + es.docx + es.pdf
│   ├── en/en.md + en.docx + en.pdf
│   ├── fr/fr.md + fr.docx + fr.pdf
│   ├── ar/ar.md + ar.docx + ar.pdf
│   └── zh/zh.md + zh.docx + zh.pdf
├── run_pipeline.sh               # Script de ejecución
├── requirements.txt
└── .env                          # API key de DeepL (no versionado)
```

## Instalación

```bash
# Clonar el repo
git clone <url-del-repo>
cd .md-translation-tool

# Crear entorno virtual e instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configurar API key de DeepL
echo 'DEEPL_API_KEY="tu-api-key"' > .env

# (Opcional) Instalar LibreOffice para generación de PDF
brew install --cask libreoffice
```

## Uso

```bash
# Traducir un archivo concreto
./run_pipeline.sh sources/apuntes.md

# O ejecutar directamente con Python
source .venv/bin/activate
python src/translation_pipeline.py sources/apuntes.md

# Traducir solo a ciertos idiomas
python src/translation_pipeline.py sources/apuntes.md --langs EN-GB FR

# Procesar todos los .md de sources/
python src/translation_pipeline.py
```

## API Key

Se necesita una API key de [DeepL](https://www.deepl.com/pro-api). El plan gratuito (keys que terminan en `:fx`) funciona perfectamente.

Crea un archivo `.env` en la raíz del proyecto:

```
DEEPL_API_KEY="tu-clave-aquí"
```

## Generación de PDF

Los PDF se generan localmente con LibreOffice en modo headless. Si LibreOffice no está instalado, el pipeline continúa sin interrumpirse (solo se genera `.md` y `.docx`).

```bash
# Instalar LibreOffice en macOS
brew install --cask libreoffice
```
