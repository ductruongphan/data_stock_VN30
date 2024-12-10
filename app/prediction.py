import os
import time  # Đo hiệu suất
import logging  # Ghi log
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import numpy as np
from datetime import datetime
import pandas as pd
from datetime import timedelta
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import load_model  # type: ignore

# Cấu hình log
logging.basicConfig(level=logging.INFO)

class StockPredictionApp:
    def __init__(self, db):
        self.db = db
        self.models_cache = {}
        self.data_cache = {}
        self.scalers_cache = {}

    def load_and_prepare_data(self, symbol):
        """Load và chuẩn bị dữ liệu cổ phiếu từ MongoDB, chỉ lấy dữ liệu trước ngày hôm nay."""
        start_time = time.time()
        try:
            if symbol in self.data_cache:
                logging.info(f"Dữ liệu cho '{symbol}' được lấy từ bộ nhớ đệm.")
                return self.data_cache[symbol], self.scalers_cache[symbol]

            collection = self.db.db[symbol]
            data = list(collection.find().sort("Ngay", 1))

            df = pd.DataFrame(data)[['Ngay', 'GiaDongCua']]

            if df.empty or 'GiaDongCua' not in df.columns:
                logging.warning(f"Không có dữ liệu để dự báo cho mã cổ phiếu '{symbol}'.")
                return {"error": f"Không có dữ liệu để dự báo cho mã cổ phiếu {symbol}."}, None

            df['Ngay'] = pd.to_datetime(df['Ngay'])
            df.set_index('Ngay', inplace=True)

            # Lọc dữ liệu chỉ trước ngày hôm nay
            today = datetime.today().date()
            df = df[df.index.date < today]

            # Nếu không còn dữ liệu sau khi lọc
            if df.empty:
                logging.warning(f"Không có dữ liệu trước ngày hôm nay cho mã cổ phiếu '{symbol}'.")
                return {"error": f"Không có dữ liệu trước ngày hôm nay cho mã cổ phiếu {symbol}."}, None

            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(df[['GiaDongCua']].values)

            self.data_cache[symbol] = df
            self.scalers_cache[symbol] = scaler
            return df, scaler

        except Exception as e:
            logging.error(f"Lỗi khi tải và chuẩn bị dữ liệu cho '{symbol}': {str(e)}")
            return {"error": f"Lỗi khi tải và chuẩn bị dữ liệu cho {symbol}: {str(e)}"}, None

        finally:
            elapsed_time = time.time() - start_time
            logging.info(f"load_and_prepare_data('{symbol}') hoàn thành trong {elapsed_time:.4f} giây.")

    def get_or_load_model(self, symbol):
        """Tải mô hình từ bộ nhớ đệm hoặc từ file."""
        start_time = time.time()
        try:
            if symbol in self.models_cache:
                logging.info(f"Mô hình cho '{symbol}' được lấy từ bộ nhớ đệm.")
                return self.models_cache[symbol]

            model_path = os.path.join('models', f'{symbol}_model.keras')

            if not os.path.exists(model_path):
                logging.warning(f"Không tìm thấy mô hình cho mã cổ phiếu '{symbol}'.")
                return None

            model = load_model(model_path)
            self.models_cache[symbol] = model
            return model

        except Exception as e:
            logging.error(f"Lỗi khi tải mô hình cho '{symbol}': {str(e)}")
            return None

        finally:
            elapsed_time = time.time() - start_time
            logging.info(f"get_or_load_model('{symbol}') hoàn thành trong {elapsed_time:.4f} giây.")

    def retrain_model(self, model, x_train, y_train):
        """Huấn luyện lại mô hình với dữ liệu mới."""
        start_time = time.time()
        try:
            model.fit(x_train, y_train, epochs=5, batch_size=50, verbose=0)
            logging.info("Huấn luyện lại mô hình thành công.")
            return model

        except Exception as e:
            logging.error(f"Lỗi khi huấn luyện lại mô hình: {str(e)}")
            return model

        finally:
            elapsed_time = time.time() - start_time
            logging.info(f"retrain_model hoàn thành trong {elapsed_time:.4f} giây.")

    def predict_next_days(self, symbol, days_to_predict, retrain_interval=5):
        """Dự đoán giá cổ phiếu trong tương lai."""
        start_time = time.time()
        try:
            df, scaler = self.load_and_prepare_data(symbol)

            if isinstance(df, dict) and "error" in df:
                return df

            model = self.get_or_load_model(symbol)

            if not model:
                return {"error": f"Không tìm thấy mô hình cho mã cổ phiếu {symbol}."}

            predicted_prices = []
            predicted_dates = []

            scaled_data = scaler.transform(df[['GiaDongCua']].values)

            x_train, y_train = [], []
            for i in range(50, len(scaled_data)):
                x_train.append(scaled_data[i - 50:i, 0])
                y_train.append(scaled_data[i, 0])

            x_train, y_train = np.array(x_train), np.array(y_train)
            x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))

            next_date = df.index[-1]

            for i in range(1, days_to_predict + 1):
                next_date += timedelta(days=1)
                while next_date.weekday() >= 5:
                    next_date += timedelta(days=1)

                x_input = np.array([scaled_data[-50:, 0]])
                x_input = x_input.reshape((1, x_input.shape[1], 1))
                y_pred = model.predict(x_input, verbose=0)

                y_pred_inversed = scaler.inverse_transform(y_pred)
                predicted_price = round(float(y_pred_inversed[0][0]), 2)

                predicted_prices.append(predicted_price)
                predicted_dates.append(next_date)

                new_data = scaler.transform([[predicted_price]])
                scaled_data = np.vstack([scaled_data, new_data])

                if i % retrain_interval == 0:
                    logging.info(f"Tái huấn luyện mô hình sau {i} ngày dự đoán.")
                    x_train, y_train = [], []
                    for j in range(50, len(scaled_data)):
                        x_train.append(scaled_data[j - 50:j, 0])
                        y_train.append(scaled_data[j, 0])
                    x_train, y_train = np.array(x_train), np.array(y_train)
                    x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
                    model = self.retrain_model(model, x_train, y_train)

            return {"dates": [str(date) for date in predicted_dates], "predicted_prices": predicted_prices}

        except Exception as e:
            logging.error(f"Lỗi khi dự đoán dữ liệu cho '{symbol}': {str(e)}")
            return {"error": f"Lỗi khi dự đoán dữ liệu cho {symbol}: {str(e)}"}

        finally:
            elapsed_time = time.time() - start_time
            logging.info(f"predict_next_days('{symbol}', {days_to_predict}) hoàn thành trong {elapsed_time:.4f} giây.")
