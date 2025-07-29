import os
import json
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
class GPTHandler:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    @staticmethod
    def get_credentials():
        SCOPES = ['https://www.googleapis.com/auth/drive.file']

        # 루트 디렉토리 기준 경로
        root_dir = Path(__file__).resolve().parents[1]
        token_path = root_dir / "token.json"
        creds_path = root_dir / "credentials.json"

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return creds

    @staticmethod
    def upload_to_drive(local_file_path, file_name, folder_name="gpt_generated_swift"):
        creds = GPTHandler.get_credentials()
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

    @classmethod
    def ask(cls, prompt):
        response = cls.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    def save_swift_code(code: str, library: str, context: str, local_dir: str = "./data/gpt_generated_swift/"):
        os.makedirs(local_dir, exist_ok=True)
        filename = f"{library.lower()}_{context.lower().replace(' ', '_')}.swift"
        filepath = os.path.join(local_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"📄 Saved locally: {filepath}")

        GPTHandler.upload_to_drive(filepath, filename)

    @staticmethod
    def load_list(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    @staticmethod
    def generate_library_grammar_pairs(lib_path, grammar_path, out_path):
        libraries = GPTHandler.load_list(lib_path)
        grammars = GPTHandler.load_list(grammar_path)
        pairs = [{"library": lib, "grammar": grammar} for lib in libraries for grammar in grammars]
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(pairs, f, indent=2)
        print(f"✅ Generated {len(pairs)} pairs → {out_path}")
        return pairs
