from flask import Flask, request, send_from_directory, render_template_string, flash, session, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
import os
import logging
import shutil
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'BEST'  # 设置一个有效的 SECRET_KEY
app.config['UPLOAD_FOLDER'] = 'D:\\uploads'  # 上传目录
app.config['MAX_CONTENT_LENGTH'] = 8192 * 1024 * 1024  # 限制最大文件大小为100MB

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
    file = FileField('文件', validators=[DataRequired()])
    submit = SubmitField('上传')

# 生成唯一链接
def generate_unique_link():
    characters = string.ascii_letters + string.digits
    link = ''.join(random.choice(characters) for _ in range(16))
    return link

# 上传页面
upload_page = """
<!doctype html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>上传文件</title>
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background-color: #f4f4f4;
            font-family: Arial, sans-serif;
        }
        .container {
            width: 80%;
            max-width: 600px;
            background-color: white;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
        }
        h1 { color: #333; }
        form { margin-top: 20px; }
        input[type=file], input[type=submit] { padding: 10px; margin-top: 10px; width: 100%; }
        ul { list-style-type: none; padding: 0; }
        li { margin: 5px 0; }
        a { text-decoration: none; color: #007BFF; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>上传文件</h1>
        <form method="post" enctype="multipart/form-data" id="upload-form">
          {{ form.hidden_tag() }}
          {{ form.file.label() }}
          {{ form.file() }}
          {{ form.submit() }}
        </form>
        {% if download_link %}<p>下载链接: <a href="{{ download_link }}">{{ download_link }}</a></p>{% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    form = UploadForm()
    download_link = None
    if form.validate_on_submit():
        try:
            file = form.file.data
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)  # 保存文件

                # 生成唯一链接
                unique_link = generate_unique_link()
                file_links[unique_link] = filename

                download_link = url_for('download_file', link=unique_link, _external=True)

                logging.info(f'文件 {filename} 上传成功，保存路径: {file_path}，下载链接: {download_link}')
                logging.info(f'当前 file_links: {file_links}')
                return render_template_string(upload_page, form=form, download_link=download_link)
        except Exception as e:
            logging.error(f'文件上传失败: {e}')
            return '文件上传失败，请稍后再试'

    return render_template_string(upload_page, form=form)

@app.route('/download/<link>', methods=['GET'])
def download_file(link):
    logging.info(f'请求下载链接: {link}')
    if link in file_links:
        filename = file_links[link]
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logging.info(f'找到文件: {filename}，路径: {file_path}')

        if os.path.exists(file_path):
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        else:
            logging.error(f'文件 {filename} 不存在于路径 {file_path}')
            return '文件不存在。', 404
    else:
        logging.info(f'未找到链接: {link}')
        return '无效的下载链接。', 404

if __name__ == '__main__':
    app.run(debug=True)
