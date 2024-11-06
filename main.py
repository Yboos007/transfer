from flask import Flask, request, send_from_directory, render_template_string, session, jsonify, url_for, make_response
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, StringField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename, redirect
from flask_cors import CORS
import os
import logging
import shutil
import random
import string
import zipfile

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'Best'
app.config['UPLOAD_FOLDER'] = 'D:\\uploads'
app.config['MAX_CONTENT_LENGTH'] = 8192 * 1024 * 1024

file_links = {}

def initialize_upload_folder():
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        shutil.rmtree(app.config['UPLOAD_FOLDER'])
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

initialize_upload_folder()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class UploadForm(FlaskForm):
    files = FileField(' ', validators=[DataRequired()])
    submit = SubmitField('发送')

class PickupCodeForm(FlaskForm):
    pickup_code = StringField('取件码', validators=[DataRequired()])
    submit = SubmitField('下载')

def generate_unique_link():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(16))

def generate_pickup_code():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(4))

upload_page = """
<!doctype html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文件传输</title>
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background-color: #f4f4f4;
            font-family: Arial, sans-serif;
        }
        .container {
            width: 90%;
            max-width: 1200px;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .readme-box {
            background-color: #e7f3ff;
            border: 1px solid #b3d7ff;
            border-radius: 5px;
            padding: 15px;
            color: #333;
            margin-bottom: 20px;
        }
        .content {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .left-column, .right-column {
            padding: 20px;
            border-radius: 5px;
            background-color: #fff;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        h1, h2 {
            color: #333;
        }
        input[type=file], input[type=submit], input[type=text] {
            padding: 10px;
            margin-top: 10px;
            width: 100%;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        input[type=text] {
            width: auto; /* 调整取件码输入框的宽度 */
        }
        input[type=submit] {
            background-color: #4caf50;
            color: white;
            border: none;
            cursor: pointer;
        }
        input[type=submit]:hover {
            background-color: #45a049;
        }
        .progress-container {
            margin-top: 20px;
            position: relative;
            width: 100%;
            height: 20px;
            background-color: #f3f3f3;
            border-radius: 10px;
        }
        .progress-bar {
            position: absolute;
            top: 0;
            left: 0;
            height: 100%;
            background-color: #4caf50;
            border-radius: 10px;
            width: 0;
            transition: width 0.4s;
        }
        .progress-text {
            text-align: center;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #333;
        }
        .message {
            margin-top: 10px;
            color: #ff4500;
        }
        .error-message {
            color: red;
            margin-top: 20px;
            display: none; /* 默认隐藏 */
        }
        ul {
            list-style-type: none;
            padding: 0;
            margin: 0;
        }
        ul li {
            background-color: #f9f9f9;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            transition: background-color 0.3s;
        }
        ul li a {
            text-decoration: none;
            color: #007bff;
            font-weight: bold;
        }
        ul li:hover {
            background-color: #e7f1ff;
        }
        ul li a:hover {
            color: #0056b3;
        }
        /* 新增样式以处理历史链接的滚动条 */
        .history-list {
            max-height: 300px; /* 设置最大高度 */
            overflow-y: auto; /* 仅在需要时显示垂直滚动条 */
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 10px; /* 内边距 */
        }

        /* 新增样式以处理下载链接 */
        .download-link {
            word-wrap: break-word; /* 允许长链接换行 */
            overflow-wrap: break-word; /* 兼容性 */
            max-width: 100%; /* 限制最大宽度 */
            background-color: #f1f1f1;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
            word-break: break-all; /* 强制换行 */
        }

        @media (min-width: 768px) {
            .content {
                flex-direction: row;
            }
            .left-column, .right-column {
                flex: 1;
                margin: 0 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="readme-box">
            <h2>ReadMe!</h2>
            <p>欢迎使用文件传输工具！您可以通过选择单个或多个文件进行发送，系统会自动生成下载链接和取件码。</p>
            <p>发送完成后，您可以在右侧查看历史记录和下载链接及取件码，仅保存本次浏览器历史记录。</p>
            <p>请注意，因两个及以上文件程序会在发送后进行压缩，请尽量单个文件传输。</p>
            <p>欢迎给与意见或建议 <a href="mailto:jiayu_zhou007@163.com">发送邮件</a></p>
        </div>

        <div class="content">
            <div class="left-column">
                <h2>发送文件</h2>
                <form method="post" enctype="multipart/form-data" id="upload-form">
                    {{ form.hidden_tag() }}
                    {{ form.files.label() }}
                    <input type="file" name="files" multiple required>
                    <input type="submit" value="发送">
                </form>
                <div class="progress-container">
                    <div class="progress-bar" id="progress-bar"></div>
                    <div class="progress-text" id="progress-text">0%</div>
                </div>
                <p id="download-link" class="download-link"></p>
                <p id="pickup-code"></p>
                <p class="message" id="message"></p>
                <p class="error-message" id="error-message">无效的取件码，请重新输入。</p>
                
                <h2>取件码下载文件</h2>
                <form method="post" action="/download/pickup" id="pickup-form">
                    <input type="text" name="pickup_code" placeholder="请输入取件码" required>
                    <input type="submit" value="下载">
                </form>
            </div>
            <div class="right-column">
                <h2>历史链接记录</h2>
                <div class="history-list">
                    <ul>
                        {% for item in history %}
                            <li>
                                <a href="{{ item.link }}">{{ item.filename }}</a> 
                                (取件码: {{ item.pickup_code }})
                            </li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('upload-form');
            const progressBar = document.getElementById('progress-bar');
            const progressText = document.getElementById('progress-text');
            const downloadLink = document.getElementById('download-link');
            const pickupCode = document.getElementById('pickup-code');
            const message = document.getElementById('message');
            const errorMessage = document.getElementById('error-message');

            form.onsubmit = function(event) {
                event.preventDefault();
                const formData = new FormData(form);
                message.textContent = '文件发送中，请稍候...';

                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/upload', true);

                xhr.upload.onprogress = function(e) {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        progressBar.style.width = percent + '%';
                        progressText.textContent = percent + '%';
                    }
                };

                xhr.onload = function() {
                    if (xhr.status === 200) {
                        const response = JSON.parse(xhr.responseText);
                        if (response.success) {
                            progressBar.style.width = '100%';
                            progressText.textContent = '100%';
                            downloadLink.innerHTML = '下载链接: <a href="' + response.download_link + '">' + response.download_link + '</a>';
                            pickupCode.textContent = '取件码: ' + response.pickup_code;
                            message.textContent = '文件发送成功！';
                            setTimeout(function() {
                                location.reload();
                            }, 5000);
                            // 调整页面刷新时间
                        } else {
                            message.textContent = '文件发送失败，请稍后再试';
                        }
                    } else {
                        message.textContent = '文件发送失败，请稍后再试';
                    }
                };

                xhr.onerror = function() {
                    message.textContent = '文件发送失败，请稍后再试';
                };

                xhr.send(formData);
            };

            const pickupForm = document.getElementById('pickup-form');
            pickupForm.onsubmit = function(event) {
                event.preventDefault();
                const pickupCodeValue = pickupForm.elements['pickup_code'].value;

                // 发送取件码请求
                fetch('/download/pickup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams({ pickup_code: pickupCodeValue })
                })
                .then(response => {
                    if (response.ok) {
                        window.location.href = response.url; // 下载文件
                    } else {
                        errorMessage.style.display = 'block'; // 显示错误提示
                    }
                })
                .catch(error => {
                    console.error('错误:', error);
                    errorMessage.style.display = 'block'; // 显示错误提示
                });
            };
        });
    </script>
</body>
</html>
"""

def set_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/', methods=['GET', 'POST'])
def index():
    form = UploadForm()
    history = session.get('history', [])
    response = make_response(render_template_string(upload_page, form=form, history=history))
    return set_no_cache_headers(response)

@app.route('/upload', methods=['POST'])
def upload_file():
    files = request.files.getlist('files')
    unique_link = generate_unique_link()
    pickup_code = generate_pickup_code()

    try:
        if not files:
            return jsonify(success=False, message='没有文件被上传。')

        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                file_links[unique_link] = file_links.get(unique_link, []) + [filename]

        # Handle file zipping if multiple files uploaded
        if len(files) > 1:
            zip_filename = f"{unique_link}.zip"
            zip_file_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)

            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for filename in file_links[unique_link]:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    zipf.write(file_path, arcname=filename)

            download_link = url_for('download_zip', link=unique_link, _external=True)
        else:
            filename = file_links[unique_link][0]
            download_link = url_for('download_file', filename=filename, _external=True)

        # Store the link and pickup code in session history
        session.setdefault('history', []).append({
            'filename': zip_filename if len(files) > 1 else filename,
            'link': download_link,
            'pickup_code': pickup_code
        })
        session.modified = True

        # Store the download link by pickup code
        file_links[pickup_code] = download_link

        return jsonify(success=True, download_link=download_link, pickup_code=pickup_code)
    except Exception as e:
        logging.error(f'文件发送失败: {e}')
        return jsonify(success=False, message='文件发送失败，请稍后再试')

@app.route('/download/pickup', methods=['POST'])
def download_by_pickup_code():
    pickup_code = request.form.get('pickup_code')
    download_link = file_links.get(pickup_code)

    if download_link:
        return redirect(download_link)  # Redirect to the download link
    else:
        logging.error(f'无效的取件码: {pickup_code}')
        return jsonify(success=False, message='无效的取件码。'), 404

@app.route('/download/zip/<link>', methods=['GET'])
def download_zip(link):
    zip_filename = f"{link}.zip"
    zip_file_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)

    if os.path.exists(zip_file_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], zip_filename, as_attachment=True)
    else:
        logging.error(f'文件未找到: {zip_file_path}')
        return '无效的下载链接。', 404

@app.route('/download/file/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    logging.info('服务器启动中...')
    logging.info("当前版本v20241105,  ----By Jerry")
    app.run(host='0.0.0.0', port=6789, debug=False)