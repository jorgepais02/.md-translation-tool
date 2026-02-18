# .MD translation tool

Pipeline automático para **traducir apuntes en Markdown** a múltiples idiomas y generar documentos **Word (.docx)** con formato académico.

## Características

- **Traducción automática** a 4 idiomas (inglés, francés, árabe, chino) con la API de DeepL
- **Generación de DOCX** con formato académico (Times New Roman, márgenes, numeración de página)
- **Soporte RTL** para árabe (dirección de texto derecha-a-izquierda)
- **Tipografía CJK** (SimSun) para chino
- **Imagen de cabecera** automática en todos los documentos

## Estructura

```
├── src/
│   ├── translate_md_deepl.py   # Traductor con DeepL API
│   └── make_notes.py           # Generador de DOCX
├── sources/                    # Archivos .md de entrada
├── public/
│   └── header.png              # Imagen de cabecera para los DOCX
├── translated/                 # Salida generada (gitignored)
│   └── <nombre>/
│       ├── es.md + es.docx
│       ├── en.md + en.docx
│       ├── fr.md + fr.docx
│       ├── ar.md + ar.docx
│       └── zh.md + zh.docx
├── translate.sh                # Script de ejecución
├── requirements.txt
└── .env                        # API key de DeepL (no versionado)
```

## Instalación

```bash
# Clonar el repo
git clone <url-del-repo>
cd apuntes-script

# Crear entorno virtual e instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configurar API key de DeepL
echo 'DEEPL_API_KEY="tu-api-key"' > .env
```

## Uso

```bash
# Traducir un archivo concreto
./translate.sh sources/apuntes.md

# O ejecutar directamente con Python
source .venv/bin/activate
python src/translate_md_deepl.py sources/apuntes.md

# Traducir solo a ciertos idiomas
python src/translate_md_deepl.py sources/apuntes.md --langs EN-GB FR

# Procesar todos los .md de sources/
python src/translate_md_deepl.py
```

## API Key

Se necesita una API key de [DeepL](https://www.deepl.com/pro-api). El plan gratuito (keys que terminan en `:fx`) funciona perfectamente.

Crea un archivo `.env` en la raíz del proyecto:

```
DEEPL_API_KEY="tu-clave-aquí"
```
