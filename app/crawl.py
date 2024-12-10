from pymongo import MongoClient, ReplaceOne
from datetime import datetime, timedelta
import requests
import re
import logging
import time
import threading
from config import Config

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def format_date(date_str):
    """Chuyển đổi định dạng ngày từ dd/mm/yyyy sang yyyy-mm-dd."""
    return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")

def parse_thay_doi(thay_doi_str):
    """Phân tích thay đổi giá trị và phần trăm từ chuỗi."""
    if not thay_doi_str:
        return 0.0, 0.0
    match = re.match(r"([+-]?\d+\.\d+)\(([-+]?\d+\.\d+)\s%\)", thay_doi_str)
    if match:
        return float(match.group(1)), float(match.group(2))
    return 0.0, 0.0

def fetch_with_retry(url, retries=3, delay=5):
    """Thực hiện retry khi gọi API bị lỗi."""
    for attempt in range(retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response
        except requests.RequestException as e:
            logging.error(f"Request failed: {e}")
        logging.warning(f"Retrying ({attempt + 1}/{retries}) after {delay} seconds...")
        time.sleep(delay)
    return None

def fetch_data(symbol, start_date, end_date, db):
    """Thu thập dữ liệu từ API và thay thế bản ghi cũ nếu có thay đổi."""
    logging.info(f"Fetching data for symbol: {symbol} from {start_date} to {end_date}.")
    try:
        collection = db[symbol]
        page_size = 20
        url = f"https://s.cafef.vn/Ajax/PageNew/DataHistory/PriceHistory.ashx?Symbol={symbol}&StartDate={start_date}&EndDate={end_date}&PageIndex=1&PageSize={page_size}"
        
        response = fetch_with_retry(url)
        if not response:
            logging.error(f"Failed to fetch data for {symbol} after retries.")
            return

        data = response.json()
        total_records = data.get("Data", {}).get("TotalCount", 0)
        total_pages = (total_records // page_size) + (1 if total_records % page_size != 0 else 0)

        # Prepare a list for batch operations
        bulk_operations = []

        for page_index in range(total_pages, 0, -1):
            url = f"https://s.cafef.vn/Ajax/PageNew/DataHistory/PriceHistory.ashx?Symbol={symbol}&StartDate={start_date}&EndDate={end_date}&PageIndex={page_index}&PageSize={page_size}"
            response = fetch_with_retry(url)
            if not response:
                logging.error(f"Failed to fetch page {page_index} for {symbol}.")
                continue

            data = response.json()
            records = data.get("Data", {}).get("Data", [])
            if not records:
                logging.warning(f"No records found for {symbol} on page {page_index}.")
                break

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

                bulk_operations.append(ReplaceOne({'_id': transaction["_id"]}, transaction, upsert=True))

            logging.info(f"Completed page {page_index}/{total_pages} for {symbol}.")
            time.sleep(1)

        if bulk_operations:
            logging.info(f"Performing bulk write for {symbol}, {len(bulk_operations)} records.")
            collection.bulk_write(bulk_operations)

        logging.info(f"Finished fetching data for {symbol}.")
    except Exception as e:
        logging.error(f"An error occurred while fetching data for {symbol}: {e}")

def fetch_data_parallel(db_name, symbols_collection_name):
    """Thu thập dữ liệu cho nhiều mã cổ phiếu đồng thời."""
    logging.info(f"Starting parallel fetch for symbols in {symbols_collection_name}.")
    with MongoClient(Config.MONGO_URI) as client:
        db = client[db_name]
        symbols_collection = db[symbols_collection_name]
        symbols = [doc["MaCK"] for doc in symbols_collection.find()]

        logging.info(f"Symbols to process: {symbols}")
        today = datetime.now()
        if today.weekday() == 0:  # Nếu là thứ 2, lấy dữ liệu ngày thứ 6
            start_date = (today - timedelta(days=3)).strftime("%m/%d/%Y")
            end_date = (today - timedelta(days=3)).strftime("%m/%d/%Y")
        else:
            start_date = (today - timedelta(days=1)).strftime("%m/%d/%Y")
            end_date = (today - timedelta(days=1)).strftime("%m/%d/%Y")

        threads = []
        for symbol in symbols:
            logging.info(f"Starting thread for symbol: {symbol}")
            thread = threading.Thread(target=fetch_data, args=(symbol, start_date, end_date, db))
            threads.append(thread)
            thread.start()

        logging.info("All threads started. Waiting for completion.")
        for thread in threads:
            thread.join()
        logging.info("All threads completed.")

def is_in_collection_window():
    """Kiểm tra xem thời gian hiện tại có nằm trong khoảng cần thu thập dữ liệu không."""
    now = datetime.now()
    morning_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    morning_end = now.replace(hour=11, minute=31, second=0, microsecond=0)
    afternoon_start = now.replace(hour=13, minute=0, second=0, microsecond=0)
    afternoon_end = now.replace(hour=15, minute=17, second=0, microsecond=0)
    return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)

def start_background_data_collection():
    """Thu thập dữ liệu tự động vào thời gian cụ thể mỗi ngày trong tuần."""
    logging.info("Bắt đầu thu thập dữ liệu tự động.")
    
    def run_task():
        logging.info("Luồng nền thu thập dữ liệu đã khởi chạy.")
        while True:
            now = datetime.now()
            if now.weekday() < 5:  # Chỉ thực hiện vào các ngày trong tuần (thứ Hai đến thứ Sáu)
                if is_in_collection_window():
                    logging.info("Bắt đầu thu thập dữ liệu tại: %s", now)
                    try:
                        fetch_data_parallel(db_name="metadata", symbols_collection_name="ma_ck")
                        logging.info("Thu thập dữ liệu hoàn tất.")
                    except Exception as e:
                        logging.error(f"Lỗi trong quá trình thu thập dữ liệu: {e}")
                else:
                    logging.info("Ngoài khoảng thời gian thu thập. Dừng thu thập dữ liệu.")
                    time.sleep(60)
            else:
                logging.info("Hôm nay là cuối tuần. Dừng thu thập dữ liệu.")
                time.sleep(60) 

    data_thread = threading.Thread(target=run_task, daemon=True)
    data_thread.start()