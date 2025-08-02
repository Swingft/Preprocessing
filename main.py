import os
import json
from gpt_handler import GPTHandler
from claude_handler import ClaudeHandler

def main():
    json_path = "data/library_grammar_pairs.json"
    if not os.path.exists(json_path):
        lib_path = "data/libraries.txt"
        grammar_path = "data/grammars.txt"
        pairs = GPTHandler.generate_library_grammar_pairs(lib_path, grammar_path, json_path)
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

        # GPT
        try:
            print(f"🔹 GPT generating for {test_library} + {swift_grammar}")
            gpt_reply = GPTHandler.ask(prompt)
            GPTHandler.save_swift_code(gpt_reply, test_library, swift_grammar)
        except Exception as e:
            print(f"❌ GPT error for {test_library} + {swift_grammar}: {e}")

        # Claude
        try:
            print(f"🔹 Claude generating for {test_library} + {swift_grammar}")
            claude_reply = ClaudeHandler.ask(prompt)
            ClaudeHandler.save_swift_code(claude_reply, test_library, swift_grammar)
        except Exception as e:
            print(f"❌ Claude error for {test_library} + {swift_grammar}: {e}")

if __name__ == "__main__":
    main()

