# .MD Translation Tool

Pipeline automático para **traducir apuntes en Markdown** a múltiples idiomas y generar documentos **Word (.docx)** y **PDF** con formato académico.

## Características

- **Traducción automática** multi-idioma con soporte para múltiples proveedores (DeepL API, Azure AI Translator).
- **Generación en Google Docs** directamente a tu Google Drive, con formato nativo, listas reales, y RTL/BiDi perfecto.
- **Generación de DOCX local** con formato académico (Times New Roman, márgenes, numeración).
- **Generación de PDF local** vía LibreOffice (sin APIs externas).
- **CLI Interactivo** súper fácil de usar para seleccionar origen, proveedor, formato de salida e idiomas.
- **Soporte RTL robusto** para árabe y tipografía CJK para chino.

## Estructura

```
├── src/
│   ├── translation_pipeline.py   # Orquestador: traduce y envía a generadores
│   ├── translators.py            # Interfaces de DeepL y Azure Translator
│   ├── document_generator.py     # Generador de DOCX local
│   ├── google_docs_manager.py    # Integración con Google Drive/Docs API
│   └── pdf_converter.py          # Script de LibreOffice
├── sources/                      # Archivos .md de entrada
├── public/
│   └── header.png                # Imagen de cabecera para los documentos
├── secrets/                      # Credenciales de Google Auth y Tokens (gitignored)
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

# Configurar API keys copiando el archivo de ejemplo
cp .env.example .env
# Edita el .env con tu clave de DeepL o Azure
nano .env
```

## Configuración de Google Docs (Opcional)

Si quieres que el sistema genere documentos con formato perfecto (especialmente útil para la alineación RTL del Árabe) directamente en tu Google Drive:

1. Ve a [Google Cloud Console](https://console.cloud.google.com/).
2. Habilita "Google Docs API" y "Google Drive API".
3. Crea credenciales de tipo "OAuth client ID" para aplicación de escritorio.
4. Descarga el JSON y guárdalo como `secrets/credentials.json`.
5. La primera vez que lo ejecutes con Google Docs activado se abrirá tu navegador para pedirte permiso y se generará el `token.json` automático.

## Uso

La forma más sencilla y recomendada de lanzar el sistema es usando la interfaz interactiva `run_pipeline.sh`. Te hará unas preguntas rápidas antes de empezar:

```bash
# Iniciar la interfaz interactiva
./run_pipeline.sh

# O pasarle directamente el archivo y que te pregunte lo demás:
./run_pipeline.sh sources/apuntes.md
```

También puedes saltarte la interfaz interactiva y llamar al pipeline de Python directamente si quieres integrarlo en otros scripts:

```bash
source .venv/bin/activate

# Modo local + DeepL (por defecto)
python src/translation_pipeline.py sources/apuntes.md

# Generar solo en Google Drive usando Azure
python src/translation_pipeline.py sources/apuntes.md --provider azure --google --no-local

# Traducir solo a ciertos idiomas
python src/translation_pipeline.py sources/apuntes.md --langs EN-GB FR AR
```

## API Keys

Consulta el archivo `.env.example` para la lista completa de variables. 
- Puedes usar **DeepL** (plan gratuito o Pro).
- Puedes usar **Azure AI Translator** (necesitas Key y Región en el `.env`).

## Generación de PDF

Los PDF se generan localmente con LibreOffice en modo headless. Si LibreOffice no está instalado, el pipeline continúa sin interrumpirse (solo se genera `.md` y `.docx`).

```bash
# Instalar LibreOffice en macOS
brew install --cask libreoffice
```
