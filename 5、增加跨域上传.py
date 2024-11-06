from flask import Flask, request, send_from_directory, render_template_string, session, jsonify, url_for, make_response
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
from flask_cors import CORS
import os
import logging
import shutil
import random
import string
import zipfile

app = Flask(__name__)
CORS(app)  # 启用 CORS 支持
app.config['SECRET_KEY'] = 'Best'
app.config['UPLOAD_FOLDER'] = 'D:\\uploads'  # 上传目录
app.config['MAX_CONTENT_LENGTH'] = 8192 * 1024 * 1024  # 限制最大文件大小

# 存储文件名和唯一链接的映射关系
file_links = {}

# 确保上传目录存在并清空
def initialize_upload_folder():
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        shutil.rmtree(app.config['UPLOAD_FOLDER'])
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

initialize_upload_folder()

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 创建上传表单类
class UploadForm(FlaskForm):
    files = FileField(' ', validators=[DataRequired()])
    submit = SubmitField('上传')

# 生成唯一链接
def generate_unique_link():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(16))

# 上传页面
upload_page = """
<!doctype html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文件传输</title>
    <style>
        body { display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f4f4f4; font-family: Arial, sans-serif; }
        .container { width: 80%; max-width: 1200px; display: flex; background-color: white; padding: 20px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); border-radius: 8px; flex-direction: column; }
        
        /* README 文字框样式 */
        .readme-box {
            background-color: #e7f3ff; /* 背景色 */
            border: 1px solid #b3d7ff; /* 边框颜色 */
            border-radius: 5px; /* 圆角效果 */
            padding: 15px; /* 内边距 */
            margin-bottom: 20px; /* 下边距 */
            color: #333; /* 文字颜色 */
        }

        .content { display: flex; width: 100%; }
        .left-column, .right-column { flex: 1; padding: 20px; }
        .left-column { border-right: 1px solid #ddd; }
        h1 { color: #333; }
        input[type=file], input[type=submit] { padding: 10px; margin-top: 10px; width: 100%; }
        .progress-container { margin-top: 20px; position: relative; width: 100%; height: 20px; background-color: #f3f3f3; border-radius: 10px; }
        .progress-bar { position: absolute; top: 0; left: 0; height: 100%; background-color: #4caf50; border-radius: 10px; width: 0; }
        .progress-text { text-align: center; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #333; }
        .message { margin-top: 10px; color: #ff4500; }

        /* 美化列表 */
        ul {
            list-style-type: none; /* 移除默认的列表样式 */
            padding: 0; /* 去掉内边距 */
            margin: 0; /* 去掉外边距 */
        }

        ul li {
            background-color: #f9f9f9; /* 列表项背景色 */
            margin: 10px 0; /* 列表项之间的间距 */
            padding: 15px; /* 列表项的内边距 */
            border-radius: 5px; /* 圆角效果 */
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1); /* 阴影效果 */
            transition: background-color 0.3s; /* 平滑过渡效果 */
        }

        ul li a {
            text-decoration: none; /* 移除链接下划线 */
            color: #007bff; /* 链接颜色 */
            font-weight: bold; /* 加粗链接文字 */
        }

        ul li:hover {
            background-color: #e7f1ff; /* 悬停时的背景色 */
        }

        ul li a:hover {
            color: #0056b3; /* 悬停时链接颜色 */
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- README 文字框 -->
        <div class="readme-box">
            <h2>ReadMe!</h2>
            <p>欢迎使用文件上传工具！您可以通过选择单个或多个文件进行上传，系统会自动生成下载链接。</p>
            <p>上传完成后，您可以在右侧查看历史记录和下载链接，仅保存本次浏览器历史记录。</p>
            <p>请注意，因两个及以上文件程序会在上传后进行压缩，请尽量单个文件传输。</p>
            <p>欢迎给与意见或建议 <a href="mailto:jiayu_zhou007@163.com">发送邮件</a></p>
        </div>

        <div class="content">
            <div class="left-column">
                <h1>上传文件</h1>
                <form method="post" enctype="multipart/form-data" id="upload-form">
                    {{ form.hidden_tag() }}
                    {{ form.files.label() }}
                    <input type="file" name="files" multiple required>
                    <input type="submit" value="上传">
                </form>
                <div class="progress-container">
                    <div class="progress-bar" id="progress-bar"></div>
                    <div class="progress-text" id="progress-text">0%</div>
                </div>
                <p id="download-link"></p>
                <p class="message" id="message"></p>
            </div>
            <div class="right-column">
                <h2>历史链接记录</h2>
                 <ul style="max-height: 200px; overflow-y: auto;">
                    {% for item in history %}
                        <li><a href="{{ item.link }}">{{ item.filename }}</a></li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('upload-form');
            const progressBar = document.getElementById('progress-bar');
            const progressText = document.getElementById('progress-text');
            const downloadLink = document.getElementById('download-link');
            const message = document.getElementById('message');

            form.onsubmit = function(event) {
                event.preventDefault();
                const formData = new FormData(form);
                message.textContent = '文件上传中，请稍候...';

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
                            message.textContent = '文件上传成功！';
                            setTimeout(function() {
                                location.reload();
                            }, 5000);
                            /* 这里控制下载链接转移到历史链接时间 */
                        } else {
                            alert('文件上传失败，请稍后再试');
                        }
                    } else {
                        alert('文件上传失败，请稍后再试');
                    }
                };

                xhr.onerror = function() {
                    alert('文件上传失败，请稍后再试');
                };

                xhr.send(formData);
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
    download_link = None

    try:
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                file_links[unique_link] = file_links.get(unique_link, []) + [filename]

        if len(files) > 1:
            zip_filename = f"{unique_link}.zip"
            zip_file_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)

            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for filename in file_links[unique_link]:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    zipf.write(file_path, arcname=filename)

            download_link = url_for('download_zip', link=unique_link, _external=True)
            logging.info(f'多个文件上传并压缩成功，下载链接: {download_link}')

        else:
            filename = file_links[unique_link][0]
            download_link = url_for('download_file', filename=filename, _external=True)
            logging.info(f'单个文件上传成功，下载链接: {download_link}')

        session.setdefault('history', []).append({'filename': zip_filename if len(files) > 1 else filename, 'link': download_link})
        session.modified = True

        return jsonify(success=True, download_link=download_link)
    except Exception as e:
        logging.error(f'文件上传失败: {e}')
        return jsonify(success=False, message='文件上传失败，请稍后再试')

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
    logging.info("当前版本v20241030,  ----By Jerry")
    app.run(host='0.0.0.0', port=8087, debug=True)