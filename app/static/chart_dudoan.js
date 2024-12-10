async function getPrediction() {
    const symbol = document.getElementById("symbol").value;
    const days = parseInt(document.getElementById("days").value, 10);
    const errorMessage = document.getElementById("error-message");

    // Xóa thông báo lỗi trước đó
    errorMessage.textContent = "";

    if (!symbol) {
        errorMessage.textContent = "Vui lòng chọn mã cổ phiếu.";
        return;
    }

    if (isNaN(days) || days < 5 || days > 10) {
        errorMessage.textContent = "Vui lòng nhập số ngày trong khoảng từ 5 đến 10.";
        return;
    }

    const loader = document.getElementById("loader");
    loader.style.display = "flex";

    try {
        const response = await fetch(`/predict?symbol=${symbol}&days=${days}`);
        if (!response.ok) {
            throw new Error(`Lỗi HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        loader.style.display = "none";

        if (data.error) {
            errorMessage.textContent = data.error;
            return;
        }

        const formattedDates = data.dates.map(date => {
            const d = new Date(date);
            return d.toLocaleDateString('vi-VN');
        });

        // Lưu dữ liệu để tái tạo biểu đồ khi đổi theme
        window.lastChartData = { dates: formattedDates, prices: data.predicted_prices };

        renderPredictionChart(formattedDates, data.predicted_prices);
    } catch (error) {
        loader.style.display = "none";
        errorMessage.textContent = "Có lỗi xảy ra khi tải dữ liệu. Vui lòng thử lại.";
        console.error(error);
    }
}

function renderPredictionChart(dates, prices) {
    Highcharts.chart('prediction-chart', {
        chart: {
            type: 'line',
            backgroundColor: 'transparent',
        },
        title: {
            text: 'Dự đoán giá cổ phiếu',
        },
        xAxis: {
            categories: dates, // Danh sách ngày
            title: {
                text: 'Ngày',
            },
            labels: {
                rotation: -45,
                style: {
                    fontSize: '12px',
                },
            },
        },
        yAxis: {
            title: {
                text: 'Giá (nghìn VNĐ)',
            },
        },
        tooltip: {
            shared: true,
            crosshairs: true,
            headerFormat: '<b>{point.key}</b><br>',
        },
        series: [{
            name: 'Giá dự đoán',
            data: prices,
            color: 'rgba(75, 192, 192, 1)',
            lineWidth: 2,
            marker: {
                enabled: true,
                radius: 4,
            },
        }],
        credits: {
            enabled: false,
        },
    });
}

