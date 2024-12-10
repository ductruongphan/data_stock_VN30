import re
import logging
import time  # Thêm time để đo hiệu suất
from flask_pymongo import PyMongo
from flask import current_app
from markupsafe import escape
from datetime import datetime
import pandas as pd  # Cần sử dụng để tính toán MACD và RSI

class Database:
    def __init__(self):
        self.db = PyMongo(current_app).db
        logging.basicConfig(level=logging.INFO)

    @staticmethod
    def sanitize_data(data):
        """Làm sạch chuỗi để ngăn chặn các cuộc tấn công XSS."""
        if isinstance(data, str):
            return escape(data)
        return data

    @staticmethod
    def is_valid_date(date_string):
        """Xác thực xem chuỗi ngày có đúng định dạng YYYY-MM-DD không."""
        try:
            datetime.strptime(date_string, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_collection_name(name):
        """Đảm bảo tên collection chỉ chứa ký tự hợp lệ."""
        valid_pattern = re.compile(r"^[a-zA-Z0-9_]+$")
        return bool(valid_pattern.match(name))

    @staticmethod
    def error_response(message, code=400):
        """Trả về phản hồi lỗi với mã lỗi."""
        return {"error": message, "code": code}

    def query_collection(self, collection_name, query, projection):
        """Thực hiện truy vấn chung với sắp xếp theo ngày."""
        start_time = time.time()
        collection = self.db[collection_name]
        result = list(collection.find(query, projection).sort("Ngay", -1))
        end_time = time.time()
        elapsed_time = end_time - start_time
        logging.info(f"Truy vấn trên collection '{collection_name}' mất {elapsed_time:.4f} giây.")
        return result

    def get_latest_stock_data(self, symbol):
        """Lấy dữ liệu cổ phiếu mới nhất và thông tin công ty cho mã cụ thể."""
        start_time = time.time()
        try:
            symbol = self.sanitize_data(symbol)
            if not self.validate_collection_name(symbol):
                return self.error_response(f"Tên mã cổ phiếu không hợp lệ: {symbol}", 422)

            company_info = self.db["ma_ck"].find_one({"MaCK": symbol})
            if not company_info:
                return self.error_response(f"Không tìm thấy thông tin công ty cho {symbol}.", 404)

            company_info = {
                "MaCK": company_info.get("MaCK"),
                "TenCongTy": company_info.get("TenCongTy")
            }

            collection = self.db[symbol]
            latest_record = collection.find_one(sort=[("Ngay", -1)])

            if latest_record:
                latest_data = {key: self.sanitize_data(value) for key, value in latest_record.items()}
                latest_data["company_info"] = company_info

                end_time = time.time()
                elapsed_time = end_time - start_time
                logging.info(f"Lấy dữ liệu mới nhất cho '{symbol}' mất {elapsed_time:.4f} giây.")
                return latest_data

            end_time = time.time()
            elapsed_time = end_time - start_time
            logging.info(f"Lấy dữ liệu mới nhất cho '{symbol}' mất {elapsed_time:.4f} giây - Không có dữ liệu.")
            return self.error_response(f"Không tìm thấy dữ liệu cổ phiếu cho {symbol}.", 404)

        except Exception as e:
            end_time = time.time()
            elapsed_time = end_time - start_time
            logging.error(f"Lỗi khi lấy dữ liệu mới nhất cho '{symbol}': {str(e)} (Thời gian: {elapsed_time:.4f} giây)")
            return self.error_response(f"Lỗi không mong muốn: {str(e)}", 500)

    def search_data(self, collection_name, start_date, end_date, groups=None):
        """Tìm kiếm dữ liệu cổ phiếu trong một khoảng thời gian cụ thể."""
        start_time = time.time()
        try:
            groups = groups or ["prices", "volumes", "adjusted_prices", "transaction_values", "changes", "close_prices", "correlation_data"]

            if not self.validate_collection_name(collection_name):
                return self.error_response("Tên collection không hợp lệ.", 422)

            if not self.is_valid_date(start_date) or not self.is_valid_date(end_date):
                return self.error_response("Định dạng ngày không hợp lệ. Sử dụng YYYY-MM-DD.", 422)

            collection_name = self.sanitize_data(collection_name)
            start_date = self.sanitize_data(start_date)
            end_date = self.sanitize_data(end_date)

            if collection_name not in self.db.list_collection_names():
                return self.error_response("Không tìm thấy collection.", 404)

            query = {"Ngay": {"$gte": start_date, "$lte": end_date}}

            projections = {
                "prices": {"Ngay": 1, "GiaMoCua": 1, "GiaDongCua": 1},
                "volumes": {"Ngay": 1, "KhoiLuongKhopLenh": 1, "KLThoaThuan": 1},
                "adjusted_prices": {"Ngay": 1, "GiaCaoNhat": 1, "GiaDongCua": 1},
                "transaction_values": {"Ngay": 1, "GiaTriKhopLenh": 1, "GtThoaThuan": 1},
                "changes": {"Ngay": 1, "ThayDoi_GiaTri": 1},
                "close_prices": {"Ngay": 1, "GiaDieuChinh": 1, "GiaDongCua": 1},
                "correlation_data": {"Ngay": 1, "GiaDongCua": 1, "KhoiLuongKhopLenh": 1}
            }

            result = {}
            for key in groups:
                projection = projections.get(key)
                if projection:
                    query_start_time = time.time()
                    query_result = self.query_collection(collection_name, query, projection)
                    query_end_time = time.time()
                    query_elapsed_time = query_end_time - query_start_time
                    logging.info(f"Truy vấn nhóm '{key}' trên collection '{collection_name}' mất {query_elapsed_time:.4f} giây.")
                    
                    result[key] = [
                        {field: self.sanitize_data(item.get(field)) for field in projection.keys()}
                        for item in query_result
                    ]

            end_time = time.time()
            elapsed_time = end_time - start_time
            logging.info(f"Tìm kiếm dữ liệu trên '{collection_name}' từ '{start_date}' đến '{end_date}' mất {elapsed_time:.4f} giây.")
            return result

        except Exception as e:
            end_time = time.time()
            elapsed_time = end_time - start_time
            logging.error(f"Lỗi khi tìm kiếm dữ liệu trên '{collection_name}': {str(e)} (Thời gian: {elapsed_time:.4f} giây)")
            return self.error_response(f"Lỗi không mong muốn: {str(e)}", 500)

    def calculate_macd_signal(data):
        """Tính tín hiệu MACD từ dữ liệu giá đóng cửa."""
        close_prices = [item['GiaDongCua'] for item in data]
        short_window = 12
        long_window = 26
        signal_window = 9

        short_ema = pd.Series(close_prices).ewm(span=short_window).mean()
        long_ema = pd.Series(close_prices).ewm(span=long_window).mean()
        macd = short_ema - long_ema
        signal_line = macd.ewm(span=signal_window).mean()

        signals = []
        for i in range(1, len(macd)):
            if macd[i] > signal_line[i] and macd[i - 1] <= signal_line[i - 1]:
                signals.append("Mua")
            elif macd[i] < signal_line[i] and macd[i - 1] >= signal_line[i - 1]:
                signals.append("Bán")
            else:
                signals.append("")
        return signals

    def calculate_rsi_signal(data):
        """Tính tín hiệu RSI từ dữ liệu giá đóng cửa."""
        close_prices = [item['GiaDongCua'] for item in data]
        delta = pd.Series(close_prices).diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        signals = []
        for value in rsi:
            if value > 70:
                signals.append("Quá mua")
            elif value < 30:
                signals.append("Quá bán")
            else:
                signals.append("")
        return signals
