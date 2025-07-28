import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ask_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def save_swift_code(code: str, library: str, context: str, directory: str = "./data/gpt_generated_swift/"):
    os.makedirs(directory, exist_ok=True)
    filename = f"{library.lower()}_{context.lower().replace(' ', '_')}.swift"
    filepath = os.path.join(directory, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"✅ Saved: {filepath}")

def load_list(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def generate_library_grammar_pairs(lib_path, grammar_path, out_path):
    libraries = load_list(lib_path)
    grammars = load_list(grammar_path)
    pairs = [
        {"library": lib, "grammar": grammar}
        for lib in libraries for grammar in grammars
    ]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pairs, f, indent=2)
    print(f"✅ Generated {len(pairs)} pairs → {out_path}")
    return pairs

if __name__ == "__main__":
    json_path = "data/library_grammar_pairs.json"

    if not os.path.exists(json_path):
        lib_path = "data/libraries.txt"
        grammar_path = "data/grammars.txt"
        pairs = generate_library_grammar_pairs(lib_path, grammar_path, json_path)
    else:
        with open(json_path, "r", encoding="utf-8") as f:
            pairs = json.load(f)

    for pair in pairs:
        test_library = pair["library"]
        swift_grammar = pair["grammar"]

        prompt = (
            f"Write a Swift source code example that uses {test_library} and includes a {swift_grammar}. "
            "Only output the code. Do not include any explanations or comments."
        )

        try:
            reply = ask_gpt(prompt)
            save_swift_code(reply, test_library, swift_grammar)
        except Exception as e:
            print(f"❌ Error with {test_library} + {swift_grammar}: {e}")


