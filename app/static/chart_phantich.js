$(document).ready(function () {
    // Lấy CSRF token từ thẻ meta trong HTML
    const csrfToken = $('meta[name="csrf-token"]').attr('content');

    // Cấu hình mặc định của AJAX để thêm CSRF token vào header
    $.ajaxSetup({
        beforeSend: function (xhr) {
            xhr.setRequestHeader('X-CSRFToken', csrfToken); // Thêm CSRF token vào header
        }
    });

    // Đặt giá trị tối đa cho các input date
    let today = new Date().toISOString().split('T')[0];
    $("#start_date").attr("max", today);
    $("#end_date").attr("max", today);

    // Hiển thị dữ liệu mặc định ban đầu
    fetchDataAndRender();

    // Sự kiện thay đổi mã chứng khoán
    document.getElementById('collection_name').addEventListener('change', function () {
        const selectedSymbol = this.value || "VN30INDEX";
        fetch(`/dataphantich?collection_name=${selectedSymbol}`)
            .then(response => response.json())
            .then(data => {
                // Cập nhật dữ liệu các box và biểu đồ
                renderCharts(data); // Gọi hàm cập nhật giao diện với dữ liệu mới
            })
            .catch(error => console.error('Error:', error));
    });

    // Lắng nghe sự kiện submit từ form
    $("#stockForm").on("submit", function (event) {
        event.preventDefault();

        let start_date = $("#start_date").val();
        let end_date = $("#end_date").val();

        // Kiểm tra và hoán đổi ngày nếu cần
        if (start_date && end_date && new Date(start_date) > new Date(end_date)) {
            let temp = start_date;
            start_date = end_date;
            end_date = temp;

            $("#start_date").val(start_date);
            $("#end_date").val(end_date);
        }

        // Lấy dữ liệu và render lại biểu đồ
        fetchDataAndRender();
    });

    // Hàm định dạng ngày theo "ngày/tháng/năm"
    function formatNgay(dateStr) {
        let date = new Date(dateStr);
        return date.getDate().toString().padStart(2, '0') + '/' +
               (date.getMonth() + 1).toString().padStart(2, '0') + '/' +
               date.getFullYear();
    }

    // Hàm lấy dữ liệu và hiển thị biểu đồ
    function fetchDataAndRender() {
        let collection_name = $("#collection_name").val() || "VN30INDEX";
        let start_date = $("#start_date").val();
        let end_date = $("#end_date").val();
        
        // Đo thời gian trước khi gửi yêu cầu AJAX
        let startTime = performance.now();
    
        if (!start_date || !end_date) {
            let today = new Date();
            let pastDate = new Date();
            pastDate.setDate(today.getDate() - 50);
    
            let formatDate = (date) => date.toISOString().split('T')[0];
            start_date = formatDate(pastDate);
            end_date = formatDate(today);
        }
    
        // Gửi yêu cầu AJAX
        $.ajax({
            url: "/dataphantich",
            method: "GET",
            data: {
                collection_name: collection_name,
                start_date: start_date,
                end_date: end_date
            },
            success: function (response) {
                if (response.error) {
                    window.location.href = "/404";
                } else {
                    window.lastChartData = response;
                    renderCharts(response);
    
                    // Đo thời gian sau khi dữ liệu đã được nhận và hiển thị
                    let endTime = performance.now();
                    let duration = endTime - startTime;
                    console.log(`Thời gian tải dữ liệu: ${duration}ms`);
                }
            },
            error: function (xhr) {
                if (xhr.status === 404) {
                    window.location.href = "/404";
                } else {
                    console.error("Lỗi không xác định khi lấy dữ liệu.");
                }
            }
        });
    }    

    // Hàm render biểu đồ
    function renderCharts(data) {
        $('.chart-container').empty();

        renderPriceChart(data.prices);
        renderVolumeChart(data.volumes);
        renderAdjustedPriceChart(data.adjusted_prices);
        renderTransactionValueChart(data.transaction_values);
        renderChangeChart(data.changes);
        renderClosePriceChart(data.close_prices);
        renderCorrelationChart(data.correlation_data);

        window.renderCharts = renderCharts; // Đặt hàm render để gọi lại
    }

    // Cập nhật theme biểu đồ (tối/sáng)
    function updateChartsTheme() {
        const isDarkMode = $('body').hasClass('dark-mode');
        Highcharts.setOptions({
            chart: {
                backgroundColor: 'transparent',
            },
            title: {
                style: {
                    color: isDarkMode ? '#ffffff' : '#333333',
                },
            },
            xAxis: {
                labels: {
                    style: {
                        color: isDarkMode ? '#ffffff' : '#333333',
                    },
                },
            },
            yAxis: {
                labels: {
                    style: {
                        color: isDarkMode ? '#ffffff' : '#333333',
                    },
                },
                title: {
                    style: {
                        color: isDarkMode ? '#ffffff' : '#333333',
                    },
                },
            },
            legend: {
                itemStyle: {
                    color: isDarkMode ? '#ffffff' : '#333333',
                },
            },
        });

        if (window.lastChartData) {
            renderCharts(window.lastChartData);
        }
    }

    $(".theme-toggle").on("click", updateChartsTheme);

    updateChartsTheme();

    function renderPriceChart(prices) {
        prices.sort((a, b) => new Date(a.Ngay) - new Date(b.Ngay));
    
        Highcharts.chart('priceChart', {
            chart: {
                height: 400,
                backgroundColor: 'transparent'
            },
            title: {
                text: 'Biểu đồ so sánh giá mở cửa và giá đóng cửa'
            },
            xAxis: {
                categories: prices.map(item => formatNgay(item.Ngay))
            },
            yAxis: {
                title: {
                    text: 'Giá (nghìn VND)'
                }
            },
            tooltip: {
                shared: true, 
                crosshairs: true,
                headerFormat: '<b>{point.key}</b><br>'
            },
            series: [
                {
                    name: 'Giá Mở Cửa',
                    type: 'line',
                    data: prices.map(item => item.GiaMoCua),
                    marker: {
                        enabled: false,
                        symbol: 'circle',
                        radius: 4
                    },
                    color: 'red'
                },
                {
                    name: 'Giá Đóng Cửa',
                    type: 'line',
                    data: prices.map(item => item.GiaDongCua),
                    marker: {
                        enabled: false,
                        symbol: 'circle',
                        radius: 4
                    },
                    color: '#33A42E'
                }
            ],
            credits: {
                enabled: false
            }
        });
    }        
    
    function renderVolumeChart(volumes) {
        volumes.sort((a, b) => new Date(a.Ngay) - new Date(b.Ngay));
    
        Highcharts.chart('volumeChart', {
            chart: {
                type: 'column',
                height: 400,
                backgroundColor: 'transparent'
            },
            title: {
                text: 'Biểu Đồ Khối Lượng Giao Dịch Theo Ngày'
            },
            xAxis: {
                categories: volumes.map(item => formatNgay(item.Ngay)),
                crosshair: true
            },
            yAxis: {
                title: {
                    text: 'Khối Lượng (CP)'
                }
            },
            tooltip: {
                shared: true,
                valueDecimals: 0,
                headerFormat: '<b>{point.key}</b><br>'
            },
            plotOptions: {
                column: {
                    borderRadius: 0
                }
            },
            series: [
                {
                    name: 'Khối Lượng Khớp Lệnh',
                    data: volumes.map(item => item.KhoiLuongKhopLenh),
                    color: '#33A42E'
                },
                {
                    name: 'Khối Lượng Thỏa Thuận',
                    data: volumes.map(item => item.KLThoaThuan),
                    color: 'red'
                }
            ],
            credits: {
                enabled: false
            }
        });
    }
    
    function renderAdjustedPriceChart(adjusted_prices) {
        adjusted_prices.sort((a, b) => new Date(a.Ngay) - new Date(b.Ngay));
    
        Highcharts.chart('adjustedPriceChart', {
            chart: {
                height: 400,
                backgroundColor: 'transparent'
            },
            title: {
                text: 'Biểu đồ so sánh giá cao nhất và giá đóng cửa'
            },
            xAxis: {
                categories: adjusted_prices.map(item => formatNgay(item.Ngay))
            },
            yAxis: {
                title: {
                    text: 'Giá (nghìn VND)'
                }
            },
            tooltip: {
                shared: true, 
                crosshairs: true,
                headerFormat: '<b>{point.key}</b><br>'
            },
            series: [
                {
                    name: 'Giá Cao Nhat',
                    type: 'line',
                    data: adjusted_prices.map(item => item.GiaCaoNhat),
                    marker: {
                        enabled: false,  
                        symbol: 'circle',  
                        radius: 4  
                    },
                    color: 'red'  
                },
                {
                    name: 'Giá Đóng Cửa',
                    type: 'line',
                    data: adjusted_prices.map(item => item.GiaDongCua),
                    marker: {
                        enabled: false,  
                        symbol: 'circle',  
                        radius: 4  
                    },
                    color: '#33A42E' 
                }
            ],
            credits: {
                enabled: false
            }
        });
    }
    
    function renderTransactionValueChart(transaction_values) {
        // Sắp xếp dữ liệu theo ngày
        transaction_values.sort((a, b) => new Date(a.Ngay) - new Date(b.Ngay));
    
        Highcharts.chart('transactionValueChart', {
            chart: {
                type: 'column',
                height: 400,
                backgroundColor: 'transparent'
            },
            title: {
                text: 'Biểu Đồ Giá trị Giao Dịch Theo Ngày'
            },
            xAxis: {
                categories: transaction_values.map(item => formatNgay(item.Ngay)),
                crosshair: true
            },
            yAxis: {
                title: {
                    text: 'Giá trị (VNĐ)'
                }
            },
            tooltip: {
                shared: true,
                valueDecimals: 0,
                headerFormat: '<b>{point.key}</b><br>'
            },
            plotOptions: {
                column: {
                    borderRadius: 0
                }
            },
            series: [
                {
                    name: 'Giá trị Khớp Lệnh',
                    data: transaction_values.map(item => item.GiaTriKhopLenh),
                    color: '#33A42E'
                },
                {
                    name: 'Giá trị Thỏa Thuận',
                    data: transaction_values.map(item => item.GtThoaThuan),
                    color: 'red'
                }
            ],
            credits: {
                enabled: false
            }
        });
    }
    
    
    function renderChangeChart(changes) {
        changes.sort((a, b) => new Date(a.Ngay) - new Date(b.Ngay));
    
        // Kiểm tra giá trị của ngày gần nhất
        const lastValue = changes[changes.length - 1].ThayDoi_GiaTri;
        const color = lastValue >= 0 ? '#33A42E' : 'red';
    
        Highcharts.chart('changeChart', {
            chart: {
                type: 'line',
                height: 400,
                backgroundColor: 'transparent'
            },
            title: {
                text: 'Biểu đồ thay đổi giá trị'
            },
            xAxis: {
                categories: changes.map(item => formatNgay(item.Ngay))
            },
            yAxis: {
                title: {
                    text: 'Giá (nghìn VND)'
                }
            },
            series: [{
                name: 'Giá thay đổi',
                data: changes.map(item => item.ThayDoi_GiaTri),
                color: color, // Thiết lập màu sắc dựa trên giá trị của ngày gần nhất
                marker: {
                    enabled: false
                }
            }],
            credits: {
                enabled: false
            }
        });
    }    
    
    function renderClosePriceChart(close_prices) {
        close_prices.sort((a, b) => new Date(a.Ngay) - new Date(b.Ngay));
    
        Highcharts.chart('closePriceChart', {
            chart: {
                height: 400,
                backgroundColor: 'transparent'
            },
            title: {
                text: 'Biểu đồ so sánh giá điều chỉnh và giá đóng cửa'
            },
            xAxis: {
                categories: close_prices.map(item => formatNgay(item.Ngay))
            },
            yAxis: {
                title: {
                    text: 'Giá (nghìn VND)'
                }
            },
            tooltip: {
                shared: true, 
                crosshairs: true,
                headerFormat: '<b>{point.key}</b><br>'
            },
            series: [
                {
                    name: 'Giá điều chỉnh',
                    type: 'line',
                    data: close_prices.map(item => item.GiaDieuChinh),
                    marker: {
                        enabled: false,  // Kích hoạt các marker (điểm)
                        symbol: 'circle',  // Dạng điểm tròn
                        radius: 4  // Kích thước điểm
                    },
                    color: 'red'  // Màu cho dòng Giá Mở Cửa
                },
                {
                    name: 'Giá Đóng Cửa',
                    type: 'line',
                    data: close_prices.map(item => item.GiaDongCua),
                    marker: {
                        enabled: false,  // Kích hoạt các marker (điểm)
                        symbol: 'circle',  // Dạng điểm tròn
                        radius: 4  // Kích thước điểm
                    },
                    color: '#33A42E'  // Màu cho dòng Giá Đóng Cửa
                }
            ],
            credits: {
                enabled: false
            }
        });
    }
    
    function renderCorrelationChart(correlation_data) {
        correlation_data.sort((a, b) => new Date(a.Ngay) - new Date(b.Ngay));
    
        const formattedData = correlation_data.map(item => {
            if (item.KhoiLuongKhopLenh && item.GiaDongCua) {
                return [item.KhoiLuongKhopLenh, item.GiaDongCua];
            }
            return null;
        }).filter(item => item !== null);
    
        Highcharts.chart('correlationChart', {
            chart: {
                type: 'scatter',
                height: 400,
                backgroundColor: null,
                zoomType: 'xy',
            },
            title: {
                text: 'Biểu Đồ Phân Tích Tương Quan: Giá Đóng Cửa và Giá Trị Khớp Lệnh'
            },
            yAxis: {
                title: {
                    text: 'Giá (nghìn VND)'
                }
            },
            tooltip: {
                headerFormat: '<b>{series.name}</b><br>',
                pointFormat: 'Khối Lượng: {point.x}<br>Giá: {point.y}'
            },
            series: [{
                name: 'Tương Quan (Giá đóng cửa và Khối lượng khớp lệnh)',
                data: formattedData
            }],
            credits: {
                enabled: false
            }
        });
    }        
});
