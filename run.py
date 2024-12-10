from flask_wtf.csrf import CSRFProtect
from app import create_app
from app.crawl import start_background_data_collection

app = create_app()

# Kích hoạt bảo vệ CSRF
csrf = CSRFProtect(app)

if __name__ == '__main__':
    
    start_background_data_collection()

    app.run(debug=True)
