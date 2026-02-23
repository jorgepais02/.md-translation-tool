import os
import pickle
import base64
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes required for Google Drive and Docs
# Added Drive for image uploading
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive'
]

RTL_LANGS = {"ar", "he", "fa", "ur"}

class GoogleDocsManager:
    """Manages Google Docs creation, text insertion, and advanced formatting."""
    
    def __init__(self, credentials_path: str = 'secrets/credentials.json', token_path: str = 'secrets/token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = self._authenticate()
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    def _authenticate(self):
        """Standard Google API OAuth2 authentication flow."""
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"ERROR: {self.credentials_path} not found. "
                        "Please download it from Google Cloud Console and place it in secrets/credentials.json"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds

    def create_document(self, title: str) -> str:
        """Create a new Google Doc and return its ID."""
        doc = self.docs_service.documents().create(body={'title': title}).execute()
        return doc.get('documentId')

    def _upload_image_to_drive(self, image_path: Path) -> dict:
        """Upload an image to Drive, make it public, and return the file dict (id and link)."""
        file_metadata = {
            'name': image_path.name,
            'mimeType': 'image/png'
        }
        media = MediaFileUpload(str(image_path), mimetype='image/png')
        file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id, webContentLink').execute()
        
        # Make the file readable by everyone with the link (required for Docs API insertion)
        self.drive_service.permissions().create(
            fileId=file.get('id'),
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        return file

    def setup_document_layout(self, doc_id: str, header_image_path: Path | None = None, is_rtl: bool = False):
        """Setup headers, footers (page numbers), and RTL section settings."""
        requests = []
        
        # 1. Create Header
        header_resp = self.docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': [{'createHeader': {'type': 'DEFAULT'}}]}
        ).execute()
        header_id = header_resp['replies'][0]['createHeader']['headerId']
        
        uploaded_image_id = None
        
        # 2. Insert Image
        image_uri = None
        if header_image_path:
            if isinstance(header_image_path, str) and header_image_path.startswith("http"):
                image_uri = header_image_path
            elif isinstance(header_image_path, Path) and header_image_path.exists():
                file_info = self._upload_image_to_drive(header_image_path)
                image_uri = file_info.get('webContentLink')
                uploaded_image_id = file_info.get('id')
                
        if image_uri:
            requests.append({
                'insertInlineImage': {
                    'uri': image_uri,
                    'location': {'segmentId': header_id, 'index': 0},
                    'objectSize': {'width': {'magnitude': 500, 'unit': 'PT'}}
                }
            })
            requests.append({
                'updateParagraphStyle': {
                    'range': {'segmentId': header_id, 'startIndex': 0, 'endIndex': 1},
                    'paragraphStyle': {'alignment': 'CENTER'},
                    'fields': 'alignment'
                }
            })

        # 3. Create Footer with Page Number
        footer_resp = self.docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': [{'createFooter': {'type': 'DEFAULT'}}]}
        ).execute()
        footer_id = footer_resp['replies'][0]['createFooter']['footerId']
        
        # Insert simple static text instead
        requests.append({
            'insertText': {
                'location': {
                    'segmentId': footer_id,
                    'index': 0
                },
                'text': 'Página '
            }
        })
        # Align the entire footer
        requests.append({
            'updateParagraphStyle': {
                'range': {'segmentId': footer_id, 'startIndex': 0, 'endIndex': 7}, # length of "Página "
                'paragraphStyle': {'alignment': 'END' if not is_rtl else 'START'},
                'fields': 'alignment'
            }
        })

        # 4. Set Document-wide RTL at section level
        if is_rtl:
            # This is complex in Docs API as it's often a paragraph property.
            # We already set it in upload_markdown_content per paragraph.
            pass

        if requests:
            self.docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()

        # 5. Cleanup: If we uploaded an image to Drive just for this, delete it now that it's embedded.
        if uploaded_image_id:
            try:
                self.drive_service.files().delete(fileId=uploaded_image_id).execute()
            except Exception as e:
                print(f"Warning: Failed to delete temporary header image from Drive: {e}")

    def upload_markdown_content(self, doc_id: str, lines: list[str], lang: str):
        """Parse simple Markdown lines and insert into Google Doc with formatting."""
        requests = []
        is_rtl = lang in RTL_LANGS
        
        full_text = ""
        formats = [] # Store (start, end, type, level/data)
        
        current_offset = 0
        for line in lines:
            line = line.rstrip()
            if not line:
                # Skip empty lines in the text payload, relying on spaceBelow/spaceAbove for visual padding
                continue
            
            start = 1 + current_offset
            
            # Semantic parsing
            if line.startswith("#"):
                hashes = line.split(" ")[0]
                level = len(hashes)
                content = " ".join(line.split(" ")[1:]) + "\n"
                full_text += content
                formats.append((start, start + len(content), 'HEADING', level))
                current_offset += len(content)
            elif line.startswith("- "):
                content = line[2:] + "\n"
                full_text += content
                formats.append((start, start + len(content), 'BULLET', 0))
                current_offset += len(content)
            elif line.strip() and line[0].isdigit() and ". " in line:
                parts = line.split(". ", 1)
                content = parts[1] + "\n"
                full_text += content
                formats.append((start, start + len(content), 'NUMBER', 0))
                current_offset += len(content)
            else:
                content = line + "\n"
                full_text += content
                formats.append((start, start + len(content), 'NORMAL', 0))
                current_offset += len(content)

        # 1. Insert all text
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': full_text
            }
        })
        
        # 3. Apply common styles and RTL
        total_len = len(full_text)
        font_family = 'Noto Serif SC' if lang == 'zh' else 'Times New Roman'
        
        requests.append({
            'updateTextStyle': {
                'range': {'startIndex': 1, 'endIndex': 1 + total_len},
                'textStyle': {
                    'weightedFontFamily': {'fontFamily': font_family},
                    'fontSize': {'magnitude': 12, 'unit': 'PT'}
                },
                'fields': 'weightedFontFamily,fontSize'
            }
        })

        if is_rtl:
            requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': 1, 'endIndex': 1 + total_len},
                    'paragraphStyle': {
                        'direction': 'RIGHT_TO_LEFT',
                        'alignment': 'JUSTIFIED',
                        'spaceBelow': {'magnitude': 6, 'unit': 'PT'},
                        'spaceAbove': {'magnitude': 0, 'unit': 'PT'}
                    },
                    'fields': 'direction,alignment,spaceBelow,spaceAbove'
                }
            })
        else:
            # Set standard spacing and justification for LTR 
            requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': 1, 'endIndex': 1 + total_len},
                    'paragraphStyle': {
                        'alignment': 'JUSTIFIED',
                        'spaceBelow': {'magnitude': 6, 'unit': 'PT'},
                        'spaceAbove': {'magnitude': 0, 'unit': 'PT'}
                    },
                    'fields': 'alignment,spaceBelow,spaceAbove'
                }
            })

        # 4. Apply specific styles (Headings, Lists, Bolding)
        for start, end, ftype, level in formats:
            if ftype == 'HEADING':
                # Map # -> TITLE, ## -> HEADING_1, ### -> HEADING_2
                named_style = 'TITLE' if level == 1 else f'HEADING_{min(level - 1, 6)}'
                
                # Dynamic spacing: Title needs large space below, Headings need large space above to separate sections
                space_below = 36 if level == 1 else 8
                space_above = 0 if level == 1 else 36
                
                requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'paragraphStyle': {
                            'namedStyleType': named_style,
                            'alignment': 'CENTER' if level == 1 else ('END' if is_rtl else 'START'),
                            'spaceBelow': {'magnitude': space_below, 'unit': 'PT'},
                            'spaceAbove': {'magnitude': space_above, 'unit': 'PT'}
                        },
                        'fields': 'namedStyleType,alignment,spaceBelow,spaceAbove'
                    }
                })
                # Set font for headings back to base font to avoid fallback font inconsistency
                requests.append({
                    'updateTextStyle': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'textStyle': {'weightedFontFamily': {'fontFamily': font_family}},
                        'fields': 'weightedFontFamily'
                    }
                })
            
            if ftype == 'BULLET':
                requests.append({
                    'createParagraphBullets': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                    }
                })
            elif ftype == 'NUMBER':
                # Create actual lists
                requests.append({
                    'createParagraphBullets': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'bulletPreset': 'NUMBERED_DECIMAL_PAREN_THEN_ALPHA_PAREN'
                    }
                })
                
            # Force RTL direction specifically on lists because createParagraphBullets can reset it
            if is_rtl and (ftype == 'BULLET' or ftype == 'NUMBER'):
                requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'paragraphStyle': {
                            'direction': 'RIGHT_TO_LEFT',
                            'alignment': 'END'
                        },
                        'fields': 'direction,alignment'
                    }
                })

            # 5. Bold labels (text before ":")
            # We examine the content of this paragraph
            para_text = full_text[start-1:end-1]
            if ":" in para_text:
                label_len = para_text.find(":") + 1
                requests.append({
                    'updateTextStyle': {
                        'range': {'startIndex': start, 'endIndex': start + label_len},
                        'textStyle': {'bold': True},
                        'fields': 'bold'
                    }
                })

        # Execute all updates
        if requests:
            self.docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()

    def get_document_url(self, doc_id: str) -> str:
        return f"https://docs.google.com/document/d/{doc_id}/edit"
