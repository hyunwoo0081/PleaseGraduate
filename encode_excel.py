import os
import base64

# 단일 파일 후보 경로들
CANDIDATES = [
    "./test_data/database_data.xlsx",
    "./dev/update_table/database_data.xlsx",
    "./database_data.xlsx"
]

OUTPUT_DIR = "./render_secrets"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "database_data_base64.txt")

def encode_file():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    excel_path = None
    for path in CANDIDATES:
        if os.path.exists(path):
            excel_path = path
            break
            
    if not excel_path:
        print("[-] 'database_data.xlsx' file not found in candidates:")
        for path in CANDIDATES:
            print(f"  - {path}")
        print("Please place your single Excel file in one of the locations above and run again.")
        return

    print(f"[+] Found single Excel file at: {excel_path}")
    print(f"[+] Encoding {excel_path} to Base64 text...")
    try:
        with open(excel_path, "rb") as f:
            binary_data = f.read()
            
        b64_data = base64.b64encode(binary_data)
        
        with open(OUTPUT_FILE, "wb") as f:
            f.write(b64_data)
            
        print(f"[+] Success! Saved to {OUTPUT_FILE}")
        print("\n=== Next Steps ===")
        print("1. Upload './render_secrets/database_data_base64.txt' to Render Secret Files.")
        print("2. Set the Filename in Render Dashboard as: database_data_base64.txt")
    except Exception as e:
        print(f"[!] Error encoding file: {e}")

if __name__ == '__main__':
    encode_file()
