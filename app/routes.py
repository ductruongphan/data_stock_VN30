from flask import Blueprint, render_template, request, jsonify, session
from .models import Database
from .prediction import StockPredictionApp

bp = Blueprint('main', __name__)

db = Database()
prediction_app = StockPredictionApp(db)

# Hàm chung để lấy danh sách mã chứng khoán
def get_stock_symbols():
    return sorted([symbol for symbol in db.db.list_collection_names() if symbol not in ["ma_ck", "symbols_collection"]])

# Hàm trước mỗi request để kiểm tra và lưu collection_name vào session
@bp.before_request
def before_request():
    if 'collection_name' not in session:
        session['collection_name'] = 'VN30INDEX'

# Trang chủ
@bp.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html')

# Trang phân tích
@bp.route('/phantich', methods=['GET'])
def phantich():
    new_collection_name = request.args.get('collection_name', 'VN30INDEX')

    # Cập nhật session
    session['collection_name'] = new_collection_name

    # Lấy danh sách mã chứng khoán và dữ liệu mới nhất
    stock_symbols = get_stock_symbols()
    latest_data = db.get_latest_stock_data(new_collection_name)

    return render_template(
        "phantich.html",
        stock_symbols=stock_symbols,
        selected_symbol=new_collection_name,
        latest_data=latest_data
    )

# Trang phân tích theo ngày
@bp.route('/dataphantich', methods=['GET'])
def dataphantich():
    new_collection_name = request.args.get('collection_name')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not new_collection_name or not start_date or not end_date:
        return jsonify({"error": "Vui lòng cung cấp đủ thông tin (mã cổ phiếu, ngày bắt đầu và kết thúc)."}), 400

    # Lấy dữ liệu theo khoảng thời gian
    result = db.search_data(new_collection_name, start_date, end_date)
    latest_data = db.get_latest_stock_data(new_collection_name)

    return jsonify(result)

# Trang dự đoán
@bp.route('/dudoan', methods=['GET'])
def dudoan():
    stock_symbols = get_stock_symbols()
    return render_template("dudoan.html", stock_symbols=stock_symbols)

# API dự đoán
@bp.route('/predict', methods=['GET'])
def predict():
    symbol = request.args.get('symbol')
    days = request.args.get('days', default=10, type=int)

    if not symbol:
        return jsonify({"error": "Vui lòng cung cấp mã cổ phiếu (symbol)."}), 400

    # Dự đoán số ngày tiếp theo
    result = prediction_app.predict_next_days(symbol, days)
    return jsonify(result)
