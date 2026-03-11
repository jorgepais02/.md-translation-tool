"""Generate clean Markdown from raw text transcriptions using Google Gemini API.

Usage:
    python generate_markdown.py sources/transcription.txt
    python generate_markdown.py sources/transcription.txt -o sources/formatted.md
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Try to import the new google-genai package
try:
    from google import genai
except ImportError:
    print("ERROR: google-genai package not found.", file=sys.stderr)
    print("Please run: pip install google-genai", file=sys.stderr)
    sys.exit(1)

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Convert raw text to structured Markdown using Gemini API.")
    parser.add_argument("input_file", type=Path, help="Path to the raw text or markdown file to format.")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output path for the generated Markdown file.")
    args = parser.parse_args()
    
    input_path: Path = args.input_file
    
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)
        
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env.", file=sys.stderr)
        print("Please obtain a free key from https://aistudio.google.com/ and add it to your .env file.", file=sys.stderr)
        sys.exit(1)
        
    # Configure Gemini API Client
    client = genai.Client(api_key=api_key)
    
    # Read the content
    content = input_path.read_text(encoding="utf-8").strip()
    if not content:
        print(f"ERROR: File '{input_path}' is empty.", file=sys.stderr)
        sys.exit(1)
        
    # Determine output path
    output_path = args.output
    if not output_path:
        # Default behavior: input "note.txt" -> output "note.md" in the same directory
        # If input is already .md, we append _formatted
        if input_path.suffix.lower() == '.md':
            output_path = input_path.with_name(f"{input_path.stem}_formatted.md")
        else:
            output_path = input_path.with_suffix('.md')

    print(f"▸ Analyzing and formatting with Gemini... (Input: {input_path.name})")
    
    # We use gemini-2.5-flash as it's the current default fast model
    try:
        system_instruction = (
            "Eres un asistente experto en crear apuntes académicos.\n"
            "# Contexto para generación de apuntes en Markdown\n"
            "## Objetivo\n"
            "Convertir transcripciones o textos largos en **apuntes académicos claros en Markdown**, listos para integrarse en un repositorio de estudio.\n"
            "El estilo debe ser **técnico, sintético y neutral**, evitando el tono de transcripción.\n"
            "--- \n"
            "# Reglas de formato\n"
            "## Título y Enlaces (ESTRICTO)\n"
            "1. **MANTENER EL TÍTULO EXACTO (SIN NÚMEROS):** Respetar el Título Principal (`#`) original, PERO si el texto original empieza con un número de capítulo seguido de un punto (ej. `4. Título` o `12. Tema`), DEBES ELIMINAR ESE NÚMERO y dejar solo el texto (ej. `# Título`). No lo resumas ni cambies sus palabras.\n"
            "2. **ELIMINAR AUTOR/ENLACES:** Elimina cualquier nombre de autor, fecha, y enlaces de origen que suelan colarse al principio o al final de la transcripción original.\n"
            "--- \n"
            "## Estructura de Encabezados\n"
            "Usar jerarquía Markdown clara:\n"
            "* `#` Título principal\n"
            "* `##` Secciones\n"
            "* `###` Subsecciones (para temas específicos)\n"
            "IMPORTANTE: NUNCA conviertas subtítulos en bullet points con texto en negrita (ej. `* **Título:**`). Usa la estructura de encabezados (`###`).\n"
            "Reglas clave para encabezados:\n"
            "1. **Cada subsección debe desarrollar una idea:** Después de un encabezado (`###` o superior) debe haber siempre al menos un párrafo explicativo normal antes de cualquier lista.\n"
            "2. **Evitar encabezados excesivos:** No crees encabezados si el contenido que les sigue es demasiado corto (solo 1 o 2 líneas breves). En ese caso, usa texto normal dentro del apartado anterior.\n"
            "No usar separadores visuales (`---`) ni elementos decorativos.\n"
            "--- \n"
            "## Listas (Reglas Estrictas)\n"
            "- **LAS LISTAS NO DEBEN USARSE POR DEFECTO** para explicar todo, prioriza los párrafos, PERO sí debes usarlas cuando el texto original pida a gritos enumerar algo.\n"
            "- DEBES usar **bullet points** (`-`) para enumerar cosas como: listas de proyectos (ej. BrightID, Decentraland, etc.), características cortas, o ventajas/desventajas claras.\n"
            "- DEBES usar **listas numeradas** (`1.`, `2.`) para indicar secuencias o pasos de un proceso.\n"
            "- **NO** uses listas para dar explicaciones complejas ni desarrollar argumentos analíticos enteros. Para eso, usa siempre párrafos normales.\n"
            "- NUNCA inicies un elemento de lista con texto en negrita para simular un clave-valor o título.\n"
            "- Mantén los elementos limpios y directos.\n"
            "--- \n"
            "# Estilo de redacción\n"
            "El contenido debe tener formato de **apuntes técnicos**.\n"
            "Requisitos:\n"
            "* frases claras y concisas\n"
            "* evitar redundancias\n"
            "* eliminar introducciones tipo \"hola\" o \"bienvenidos\"\n"
            "* no usar tono conversacional\n"
            "* no añadir opiniones\n"
            "--- \n"
            "# Flujo de trabajo\n"
            "1. Yo te paso **una transcripción o texto**.\n"
            "2. Tú lo conviertes en **Markdown académico limpio**.\n"
            "3. El resultado se entrega **solo en Markdown**.\n"
            "Después puedo pedir la **versión en árabe**, que debe:\n"
            "* estar en árabe estándar moderno (MSA)\n"
            "* mantener estilo académico\n"
            "* corregir literalismos\n"
            "* mantener la estructura Markdown.\n"
            "--- \n"
            "# Ejemplo de salida esperada\n"
            "```md\n"
            "# DAOs: Gobernanza Descentralizada\n"
            "\n"
            "## El Proyecto Aragon\n"
            "\n"
            "Aragon proporciona herramientas para crear DAOs de forma sencilla, permitiendo configurar estructuras de gobernanza, votaciones y gestión de fondos mediante contratos inteligentes.\n"
            "\n"
            "Más de 1.700 organizaciones utilizan su tecnología. Entre los proyectos que han empleado Aragon se encuentran:\n"
            "- BrightID\n"
            "- la DAO de Decentraland\n"
            "- P DAO\n"
            "\n"
            "## Desafíos Clave de las DAOs\n"
            "\n"
            "### Seguridad del Código\n"
            "\n"
            "Los contratos inteligentes controlan el funcionamiento de la organización. Las vulnerabilidades en el código pueden generar pérdidas económicas significativas, por lo que requiere programación de alta calidad.\n"
            "```\n"
            "\n"
            "El resultado final debe ser **Markdown limpio, estructurado con `#`, `##`, `###`, uso muy limitado de listas y predominancia de párrafos normales para explicar ideas**. Devuelve SOLO el contenido Markdown generado.\n"
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=content,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2, # Low temperature for more deterministic academic styling
            ),
        )
        
        # Strip potential markdown code block markers that the model might add 
        # (e.g., ```markdown ... ```)
        formatted_text = response.text.strip()
        if formatted_text.startswith("```markdown"):
            formatted_text = formatted_text[11:]
        if formatted_text.startswith("```"):
            formatted_text = formatted_text[3:]
        if formatted_text.endswith("```"):
            formatted_text = formatted_text[:-3]
            
        formatted_text = formatted_text.strip()
        
        # Save output
        output_path.write_text(formatted_text + "\n", encoding="utf-8")
        
        print(f"✓ Formatted Markdown saved to: {output_path}")
        
    except Exception as e:
        print(f"ERROR: Failed to reach Gemini API: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
