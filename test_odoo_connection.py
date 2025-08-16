import os
from dotenv import load_dotenv
import sys

load_dotenv()
sys.path.append('src')

from services.odoo_service import OdooService

def main():
    print("🚀 Probando Odoo...")
    
    odoo_service = OdooService(
        url=os.getenv('ODOO_URL'),
        db=os.getenv('ODOO_DB'),
        username=os.getenv('ODOO_USERNAME'),
        password=os.getenv('ODOO_PASSWORD')
    )
    
    if odoo_service.test_connection():
        print("🎉 ¡Funciona!")
    else:
        print("😞 No funciona")

if __name__ == "__main__":
    main()