import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_credentials():
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def upload_to_drive(local_file_path, file_name, folder_name="gpt_generated_swift"):
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    folder = response.get('files', [])

    if folder:
        folder_id = folder[0]['id']
    else:
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')
        print(f"📁 Created Google Drive folder: {folder_name}")

    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(local_file_path, mimetype='text/x-swift')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"✅ Uploaded to Google Drive: {file_name} (ID: {file.get('id')})")

def ask_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def save_swift_code(code: str, library: str, context: str, local_dir: str = "./data/gpt_generated_swift/"):
    os.makedirs(local_dir, exist_ok=True)
    filename = f"{library.lower()}_{context.lower().replace(' ', '_')}.swift"
    filepath = os.path.join(local_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"📄 Saved locally: {filepath}")

    upload_to_drive(filepath, filename)

def load_list(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def generate_library_grammar_pairs(lib_path, grammar_path, out_path):
    libraries = load_list(lib_path)
    grammars = load_list(grammar_path)
    pairs = [{"library": lib, "grammar": grammar} for lib in libraries for grammar in grammars]
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
