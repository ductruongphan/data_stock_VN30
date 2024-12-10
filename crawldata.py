from pymongo import MongoClient, ReplaceOne
from datetime import datetime, timedelta
import requests
import re
import logging
from concurrent.futures import ThreadPoolExecutor
import time
from config import Config

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def format_date(date_str):
    """Chuyển đổi định dạng ngày từ dd/mm/yyyy sang yyyy-mm-dd."""
    return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")

def parse_thay_doi(thay_doi_str):
    """Phân tích sự thay đổi giá trị và phần trăm từ chuỗi CafeF."""
    if not thay_doi_str:
        return 0.0, 0.0
    match = re.match(r"([+-]?\d+\.\d+)\(([-+]?\d+\.\d+)\s%\)", thay_doi_str)
    if match:
        return float(match.group(1)), float(match.group(2))
    return 0.0, 0.0

def fetch_with_retry(url, retries=3, delay=5):
    """Gửi request với logic retry khi gặp lỗi."""
    for attempt in range(retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response
        except requests.RequestException as e:
            logging.warning(f"Lỗi khi gửi request đến {url}: {e}")
        time.sleep(delay)
    return None

def fetch_data(symbol, start_date, end_date, db):
    """Lấy dữ liệu chứng khoán của 1 mã từ CafeF và lưu vào MongoDB."""
    try:
        collection = db[symbol]
        page_size = 20
        url = f"https://s.cafef.vn/Ajax/PageNew/DataHistory/PriceHistory.ashx?Symbol={symbol}&StartDate={start_date}&EndDate={end_date}&PageIndex=1&PageSize={page_size}"
        
        response = fetch_with_retry(url)
        if not response:
            logging.error(f"Không thể lấy dữ liệu cho {symbol} sau nhiều lần thử.")
            return

        data = response.json()
        total_records = data.get("Data", {}).get("TotalCount", 0)
        total_pages = (total_records // page_size) + (1 if total_records % page_size != 0 else 0)

        for page_index in range(total_pages, 0, -1):
            url = f"https://s.cafef.vn/Ajax/PageNew/DataHistory/PriceHistory.ashx?Symbol={symbol}&StartDate={start_date}&EndDate={end_date}&PageIndex={page_index}&PageSize={page_size}"
            response = fetch_with_retry(url)
            if not response:
                continue

            data = response.json()
            records = data.get("Data", {}).get("Data", [])
            if not records:
                break

            operations = []
            for record in reversed(records):
                transaction = {
                    '_id': format_date(record['Ngay']),
                    'Ngay': format_date(record['Ngay']),
                    'GiaDieuChinh': float(record.get('GiaDieuChinh', 0)),
                    'GiaDongCua': float(record.get('GiaDongCua', 0)),
                    'KhoiLuongKhopLenh': int(record.get('KhoiLuongKhopLenh', 0)),
                    'GiaTriKhopLenh': float(record.get('GiaTriKhopLenh', 0)),
                    'KLThoaThuan': int(record.get('KLThoaThuan', 0)),
                    'GtThoaThuan': float(record.get('GtThoaThuan', 0)),
                    'GiaMoCua': float(record.get('GiaMoCua', 0)),
                    'GiaCaoNhat': float(record.get('GiaCaoNhat', 0)),
                    'GiaThapNhat': float(record.get('GiaThapNhat', 0)),
                    'ThayDoi_GiaTri': parse_thay_doi(record.get('ThayDoi', ''))[0],
                    'ThayDoi_PhanTram': parse_thay_doi(record.get('ThayDoi', ''))[1],
                }
                operations.append(ReplaceOne({"_id": transaction["_id"]}, transaction, upsert=True))

            if operations:
                collection.bulk_write(operations)
                logging.info(f"Đã cập nhật {len(operations)} bản ghi cho mã {symbol}.")

    except Exception as e:
        logging.error(f"Lỗi trong quá trình lấy dữ liệu cho {symbol}: {e}")

def fetch_data_parallel(db_name, symbols_collection_name):
    """Chạy song song việc tải dữ liệu cho tất cả các mã chứng khoán."""
    with MongoClient(Config.MONGO_URI) as client:
        db = client[db_name]
        symbols_collection = db[symbols_collection_name]
        symbols = [doc["MaCK"] for doc in symbols_collection.find()]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            for symbol in symbols:
                collection = db[symbol]
                last_record = collection.find_one(sort=[("Ngay", -1)])
                if last_record:
                    last_date = datetime.strptime(last_record["Ngay"], "%Y-%m-%d")
                    start_date = (last_date + timedelta(days=1)).strftime("%d/%m/%Y")
                else:
                    start_date = "01/01/2004"

                end_date = datetime.now().strftime("%d/%m/%Y")
                executor.submit(fetch_data, symbol, start_date, end_date, db)

def main():
    """Hàm chính khởi chạy chương trình."""
    db_name = "metadata"  # Tên cơ sở dữ liệu MongoDB
    symbols_collection_name = "ma_ck"  # Tên collection chứa mã chứng khoán
    fetch_data_parallel(db_name, symbols_collection_name)

if __name__ == "__main__":
    main()
