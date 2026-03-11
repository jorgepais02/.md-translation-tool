"""AI Refiner module using Gemini to naturalize translations."""

import os
import sys
from google import genai
from google.genai import types

def refine_translation(markdown_lines: list[str], lang_code: str) -> list[str]:
    """
    Refine auto-translated markdown lines to sound more natural and humanized
    while strictly preserving markdown structure.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found in environment. Skipping refinement.")
        return markdown_lines

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Warning: Failed to initialize Gemini client: {e}. Skipping refinement.")
        return markdown_lines

    system_instruction = (
        f"You are an expert native linguist and editor. The following text has been "
        f"auto-translated into {lang_code.upper()} and may sound stiff, literal, or unnatural. "
        f"Your task is to humanize and naturalize the text so it sounds completely fluent "
        f"and native, suited for academic or professional notes. "
        f"CRITICAL INSTRUCTION: You must preserve the existing Markdown structure "
        f"(headers (#), lists (- or 1.), bold (**), italics (*), links ([]()), and code blocks (```)) "
        f"as much as possible. However, if humanizing the text absolutely requires adapting "
        f"the formatting or syntax slightly to make sense organically in {lang_code.upper()}, "
        f"you are permitted to make those necessary adjustments. "
        f"Return ONLY the refined markdown text, without any conversational filler or explanations."
    )

    markdown_text = "\n".join(markdown_lines)

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=markdown_text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3, # Low temperature for more deterministic, focused editing
            ),
        )
        if response.text:
            return response.text.split("\n")
        else:
            print("Warning: Gemini returned an empty response. Using unrefined text.")
            return markdown_lines
    except Exception as e:
        print(f"Warning: Gemini refinement failed: {e}. Using unrefined text.")
        return markdown_lines
