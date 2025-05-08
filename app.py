from flask import Flask, render_template, request
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import os
import io
import base64
import requests
from urllib.parse import urlparse

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Анализ рисков по цветам
def analyze_risks(image):
    image = image.convert('RGB')
    pixels = np.array(image)
    green_mask = (pixels[:, :, 0] < 100) & (pixels[:, :, 1] > 120) & (pixels[:, :, 2] < 100)
    blue_mask = (pixels[:, :, 2] > 120) & (pixels[:, :, 0] < 100) & (pixels[:, :, 1] < 100)
    brown_mask = (pixels[:, :, 0] > 100) & (pixels[:, :, 1] > 80) & (pixels[:, :, 2] < 80)

    total_pixels = pixels.shape[0] * pixels.shape[1]
    green_pct = np.sum(green_mask) / total_pixels * 100
    blue_pct = np.sum(blue_mask) / total_pixels * 100
    brown_pct = np.sum(brown_mask) / total_pixels * 100

    risk_report = {
        "Риск засухи (мало растительности)": "найден" if green_pct < 20 else "не найден",
        "Риск наводнения (много воды)": "найден" if blue_pct > 30 else "не найден",
        "Деградация земли (сухая почва преобладает)": "найден" if brown_pct > 50 else "не найден",
    }

    return green_pct, blue_pct, brown_pct, risk_report

# Главная страница
@app.route('/')
def index():
    return render_template('index.html', creator="Рахим")

# Обработка изображения
@app.route('/upload', methods=['POST'])
def upload():
    image = None
    filename = ""

    # 1. Сначала пробуем загрузить по URL
    image_url = request.form.get('image_url')
    if image_url:
        try:
            response = requests.get(image_url)
            if response.status_code == 200:
                image = Image.open(io.BytesIO(response.content))
                parsed_url = urlparse(image_url)
                filename = os.path.basename(parsed_url.path)
                if not filename:
                    filename = "downloaded_image.jpg"
                image.save(os.path.join(UPLOAD_FOLDER, filename))
        except Exception as e:
            return f"Ошибка при загрузке изображения по ссылке: {e}"

    # 2. Или загружаем файл с устройства
    if not image:
        file = request.files.get('image_file')
        if file and file.filename:
            filename = file.filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            image = Image.open(filepath)
        else:
            return "Не выбрано изображение", 400

    # 3. Анализ рисков
    green_pct, blue_pct, brown_pct, risk_report = analyze_risks(image)

    # 4. Гистограмма
    image_array = np.array(image.convert('L'))  # оттенки серого
    plt.figure()
    plt.hist(image_array.ravel(), bins=256, color='gray')
    plt.title('Гистограмма яркости')
    plt.xlabel('Яркость')
    plt.ylabel('Количество пикселей')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    histogram_data = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    plt.close()

    return render_template('result.html',
                           image_path=os.path.join(UPLOAD_FOLDER, filename),
                           histogram_data=histogram_data,
                           risk_report=risk_report,
                           filename=filename)

if __name__ == '__main__':
    app.run(debug=True)