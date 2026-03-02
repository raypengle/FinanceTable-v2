'''
Author: LetMeFly
Date: 2024-01-09 19:41:42
LastEditors: LetMeFly.xyz
LastEditTime: 2025-05-10 10:10:14
modified by raypengle 2026-02-08
'''
from flask import Flask, request, jsonify, send_file, make_response
from functools import wraps
from decimal import Decimal
import sqlite3
import base64
import json
try:
    import mySecrets
    users = mySecrets.users
except:
    users = {
        'admin': {'password': '', 'role': 'admin'},
        'guest': {'password': '', 'role': 'readonly'}
    }


# 初始化
print('Users loaded')
app = Flask(__name__)

# 添加响应处理钩子，支持 cookie 和 CORS
@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

conn = sqlite3.connect('finance.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS finance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        credit DECIMAL(10, 2),
        debit DECIMAL(10, 2),
        balance DECIMAL(10, 2)
    )
''')
conn.commit()
conn.close()


# 强制"登录"修饰器
def authChecker(requiredRole):
    """验证用户权限
    requiredRole: 'readonly' - 只需要任何有效用户
                'admin' - 需要管理员权限
    """
    def actualWarper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 首先尝试从 cookie 中获取认证信息
            username = request.cookies.get('username')
            password = request.cookies.get('password')
            # 如果没有 cookie，尝试从请求头中获取
            if not username:
                username = request.headers.get('X-Auth-User')
                # 如果从请求头获取，尝试验证用户是否真实存在
                if username and username in users:
                    # 从 sessionStorage 前端发来的请求比较可信
                    password = users[username].get('password', '')

            
            # 验证用户
            isAuthenticated = False
            userRole = None
            
            if username and username in users:
                user = users[username]
                if user.get('password') == password:
                    isAuthenticated = True
                    userRole = user.get('role')
            
            # 检查权限
            hasPermission = False
            if isAuthenticated:
                if requiredRole == 'readonly':
                    hasPermission = True  # readonly 和 admin 都可以访问只读
                elif requiredRole == 'admin':
                    hasPermission = (userRole == 'admin')  # 只有 admin 可以写入
            
            if not hasPermission:
                return send_file('HTMLs/login.html')
            return func(*args, **kwargs)
        return wrapper
    return actualWarper


# 登录接口
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # 验证用户
    if not username or username not in users:
        return jsonify({'success': False, 'error': '用户不存在'}), 401
    
    user = users[username]
    if user.get('password') != password:
        return jsonify({'success': False, 'error': '密码错误'}), 401
    
    # 登录成功，创建响应并设置 cookie
    response = make_response(jsonify({
        'success': True,
        'username': username,
        'role': user.get('role')
    }))
    
    # 设置会话 cookie（浏览器关闭时自动删除）
    response.set_cookie('username', username, httponly=False, samesite='Strict', path='/')
    response.set_cookie('password', password, httponly=False, samesite='Strict', path='/')
    
    return response


# 登出接口
@app.route('/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'success': True}))
    # 删除 cookie
    response.delete_cookie('username')
    response.delete_cookie('password')
    return response



# 页面 - 主页
@app.route('/', methods=['GET'])
@authChecker('readonly')  # reader、writer都可访问
def index():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('SELECT * FROM finance')
    rows = c.fetchall()
    conn.close()
    
    # 从 cookie 中获取认证信息（优先），否则尝试从请求头
    username = request.cookies.get('username')
    if not username:
        username = request.headers.get('X-Auth-User')
    userRole = None
    if username and username in users:
        userRole = users[username].get('role')
    
    isWriter = 'true' if userRole == 'admin' else 'false'
    html_button = '<button id="addRowButton" class="add-btn" onclick="addRow()">新增一行</button>' if userRole == 'admin' else ''
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Finance Table</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            padding: 40px 20px;
        }
        
        .header {
            max-width: 1200px;
            margin: 0 auto 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 20px;
        }
        
        h2 {
            color: #333;
            font-size: 24px;
            font-weight: 600;
        }
        
        .user-info {
            color: #666;
            font-size: 14px;
            margin-right: 20px;
        }
        
        .logout-btn {
            padding: 10px 16px;
            background-color: #333;
            color: white;
            border: 1px solid #333;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
        }
        
        .logout-btn:hover {
            background-color: #555;
            border-color: #555;
        }
        
        .logout-btn:active {
            background-color: #222;
            border-color: #222;
        }
        
        .table-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border: 1px solid #ddd;
            padding: 30px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        th {
            background-color: #333;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            border: 1px solid #333;
        }
        
        td {
            padding: 12px;
            border: 1px solid #ddd;
            font-size: 14px;
        }
        
        tr:hover {
            background-color: #fafafa;
        }
        
        input[type="text"],
        input[type="number"],
        input[type="file"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            font-size: 14px;
            font-family: inherit;
        }
        
        input[type="text"]:focus,
        input[type="number"]:focus,
        input[type="file"]:focus {
            outline: none;
            border: 1px solid #333;
            background-color: #fafafa;
        }
        
        .action-buttons {
            white-space: nowrap;
        }
        
        .action-buttons button {
            margin: 2px;
            padding: 8px 12px;
            cursor: pointer;
            border: 1px solid #ddd;
            background: #f5f5f5;
            color: #333;
            font-size: 13px;
        }
        
        .action-buttons button:hover {
            background: #e8e8e8;
            border-color: #333;
        }
        
        .action-buttons .delete-btn {
            background: #333;
            color: white;
            border: 1px solid #333;
        }
        
        .action-buttons .delete-btn:hover {
            background: #666;
            border-color: #666;
        }
        
        .add-btn {
            display: block;
            margin: 0 auto;
            min-width: 120px;
            padding: 10px 16px;
            background-color: #333;
            color: white;
            border: 1px solid #333;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
        }
        
        .add-btn:hover {
            background-color: #555;
            border-color: #555;
        }
        
        .add-btn:active {
            background-color: #222;
            border-color: #222;
        }
    </style>
    <script>
        // 从 sessionStorage 中获取用户信息（优先），否则从页面中的 Python 变量获取
        let storedUsername = sessionStorage.getItem('username');
        let storedRole = sessionStorage.getItem('userRole');
        
        const isWriter = """ + isWriter + """;
        const displayUsername = storedUsername || (document.body.innerText.includes('用户: admin') ? 'admin' : (document.body.innerText.includes('用户: guest') ? 'guest' : 'Unknown'));
        
        // 如果有存储的角色，覆盖 isWriter
        const actualIsWriter = storedRole === 'admin' ? 'true' : isWriter;
        
        function getAuthHeaders() {
            const headers = {'Content-Type': 'application/json'};
            // Cookie 会自动通过 credentials: 'include' 发送
            // 同时也发送 sessionStorage 中的用户信息作为备选
            if (storedUsername) {
                // 为了安全，不要在请求头中发送密码
                // 改用一个令牌或只发送用户名
                headers['X-Auth-User'] = storedUsername;
                headers['X-Auth-Role'] = storedRole || 'readonly';
            }
            return headers;
        }
        
        function logout() {
            if (confirm('确定要退出登录吗？')) {
                fetch('/logout', {
                    method: 'POST',
                    credentials: 'include'
                })
                .then(() => {
                    location.href = '/';
                })
                .catch(error => {
                    console.error(error);
                    location.href = '/';
                });
            }
        }
        
        function addRow() {
            const table = document.getElementById("financeTable");
            const rowCount = table.rows.length;
            const row = table.insertRow(rowCount);
            row.setAttribute('id', '_' + (rowCount));

            const today = new Date();
            const date = today.getFullYear() + '年' + (today.getMonth() + 1) + '月' + today.getDate() + '日';
            const lastVal = rowCount == 1 ? 0 : Number(document.querySelector('#_' + (rowCount - 1)).cells[5].innerText);

            row.innerHTML = `
                <td>${rowCount}</td>
                <td><input type="text" name="date" value="${date}"></td>
                <td><input type="text" name="description"></td>
                <td><input type="number" value="0" name="credit" min="0" step="0.01" onchange="change1val(this)"></td>
                <td><input type="number" value="0" name="debit" min="0" step="0.01" onchange="change1val(this)"></td>
                <td name="balance">${lastVal}</td>
                <td><input type="file" name="recepit" accept=".jpg"></td>
                <td></td>
            `;
            document.getElementById("addRowButton").innerText = "提交更改";
            document.getElementById("addRowButton").onclick = submitChange;
        }

        function change1val(elem) {
            const row = elem.parentNode.parentNode;
            const credit = row.querySelector(`input[name=credit]`);
            const debit = row.querySelector(`input[name=debit]`);
            if (Number(credit.value)) {
                credit.disabled = false;
                debit.disabled = true;
            }
            else if (Number(debit.value)) {
                credit.disabled = true;
                debit.disabled = false;
            }
            else {
                credit.disabled = false;
                debit.disabled = false;
            }
            calculateNewBalance(row);
        }

        function calculateNewBalance(row) {
            const credit = parseFloat(row.querySelector('input[name="credit"]').value) || 0;
            const debit = parseFloat(row.querySelector('input[name="debit"]').value) || 0;
            const lastRow = document.querySelector('#_' + (parseInt(row.getAttribute('id').split('_')[1]) - 1));
            const lastBalance = lastRow ? parseFloat(lastRow.cells[5].innerText) || 0 : 0;
            const newBalance = lastBalance + credit - debit;
            row.cells[5].innerText = newBalance.toFixed(2);
        }

        function submitChangeAfterFileLoaded(imgBase64) {
            const row = document.querySelector('#_' + (document.getElementById("financeTable").rows.length - 1));
            const date = row.querySelector('input[name="date"]').value;
            const description = row.querySelector('input[name="description"]').value;
            const credit = row.querySelector('input[name="credit"]').value;
            const debit = row.querySelector('input[name="debit"]').value;
            if (!date) {
                alert('请输入日期');
                return;
            }
            if (!description) {
                alert('请输入本笔财务的说明');
                return;
            }
            if (!parseFloat(credit) && !parseFloat(debit)) {
                alert('入账或出帐至少有一');
                return;
            }
            if (parseFloat(credit) && parseFloat(debit)) {
                alert('入账和出帐至多有一');
                return;
            }
            const data = {date: date, description: description, credit: credit, debit: debit, recepit: imgBase64};
            fetch('/add1', {
                method: 'POST',
                headers: getAuthHeaders(),
                credentials: 'include',
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                console.log(result);
                alert('添加成功');
                location.reload();
            })
            .catch(error => {
                console.error(error);
                alert('添加失败');
            });
        }

        function submitChange() {
            const row = document.querySelector('#_' + (document.getElementById("financeTable").rows.length - 1));
            const recepit = row.querySelector('input[name="recepit"]').files[0];
            if (!recepit) {
                submitChangeAfterFileLoaded('');
                return;
            }
            const reader = new FileReader();
            reader.onload = function() {
                const imgData = reader.result.split(',')[1];
                submitChangeAfterFileLoaded(imgData);
            }
            reader.readAsDataURL(recepit);
        }
        
        function enableEditMode(id) {
            const row = document.getElementById('_' + id);
            const cells = row.cells;
            cells[1].innerHTML = `<input type="text" name="date" value="${cells[1].innerText}">`;
            cells[2].innerHTML = `<input type="text" name="description" value="${cells[2].innerText}">`;
            cells[3].innerHTML = `<input type="number" name="credit" value="${cells[3].innerText}" min="0" step="0.01" onchange="change1val(this)">`;
            cells[4].innerHTML = `<input type="number" name="debit" value="${cells[4].innerText}" min="0" step="0.01" onchange="change1val(this)">`;
            cells[7].innerHTML = `<button onclick="saveEdit(${id})">保存</button><button onclick="location.reload()">取消</button>`;
        }
        
        function saveEdit(id) {
            const row = document.getElementById('_' + id);
            const date = row.querySelector('input[name="date"]').value;
            const description = row.querySelector('input[name="description"]').value;
            const credit = row.querySelector('input[name="credit"]').value;
            const debit = row.querySelector('input[name="debit"]').value;
            if (!date) {
                alert('请输入日期');
                return;
            }
            if (!description) {
                alert('请输入本笔财务的说明');
                return;
            }
            if (!parseFloat(credit) && !parseFloat(debit)) {
                alert('入账或出帐至少有一');
                return;
            }
            if (parseFloat(credit) && parseFloat(debit)) {
                alert('入账和出帐至多有一');
                return;
            }
            const data = {id: id, date: date, description: description, credit: credit, debit: debit};
            fetch('/edit1', {
                method: 'POST',
                headers: getAuthHeaders(),
                credentials: 'include',
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                console.log(result);
                alert('修改成功');
                location.reload();
            })
            .catch(error => {
                console.error(error);
                alert('修改失败');
            });
        }
        
        function deleteRecord(id) {
            if (!confirm('确定要删除这条记录吗？')) {
                return;
            }
            fetch('/delete1', {
                method: 'POST',
                headers: getAuthHeaders(),
                credentials: 'include',
                body: JSON.stringify({id: id})
            })
            .then(response => response.json())
            .then(result => {
                console.log(result);
                alert('删除成功');
                location.reload();
            })
            .catch(error => {
                console.error(error);
                alert('删除失败');
            });
        }
        
        function viewImg(id) {
            fetch('/img/' + id, {
                method: 'GET',
                headers: getAuthHeaders(),
                credentials: 'include'
            })
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.target = '_blank';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            })
            .catch(error => {
                console.error(error);
                alert('获取图片失败');
            });
        }
        
        // 页面加载后，更新用户信息显示
        document.addEventListener('DOMContentLoaded', function() {
            const userDisplay = document.getElementById('displayUserInfo');
            if (storedUsername) {
                userDisplay.innerText = storedUsername;
                // 如果登陆成功但尚未刷新，也需要考虑权限
                if (storedRole === 'admin' && !document.getElementById('addRowButton')) {
                    // 检查是否需要添加编辑/删除按钮
                    console.log('用户为 admin，已有编辑权限');
                }
            }
        });
    </script>
</head>
<body>
    <div class="header">
        <h2>Finance Data</h2>
        <div class="user-info">用户: <strong id="displayUserInfo">""" + (username or 'Unknown') + """</strong></div>
        <button class="logout-btn" onclick="logout()">退出登录</button>
    </div>
    <div class="table-container">
        <table id="financeTable">
            <tr><th>ID</th><th>日期</th><th>说明</th><th>入账</th><th>出账</th><th>账目余额</th><th>报销凭证</th><th>操作</th></tr>
""" + ''.join('<tr id="_' + str(row[0]) + '">' + ''.join(f'<td>{col}</td>' for col in row) + """<td><button onclick="viewImg(""" + str(row[0]) + """)" style="background: #f5f5f5; color: #333; border: 1px solid #ddd;">凭证</button></td><td class="action-buttons">""" + (f'<button onclick="enableEditMode({row[0]})">编辑</button><button class="delete-btn" onclick="deleteRecord({row[0]})">删除</button>' if userRole == 'admin' else '') + """</td></tr>""" for row in rows) + """
        </table>
""" + html_button + """
    </div>
</body>
</html>"""
    
    return html


# 图片 - 获取报销依据
@app.route('/img/<imgid>')
@authChecker('readonly')
def img(imgid):
    return send_file(f'Imgs/{imgid}.jpg', mimetype='image/jpeg')


# 接口 - 新增一行
@app.route('/add1', methods=['POST'])
@authChecker('admin')  # 只有admin可以访问
def add1():
    data = request.json
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, balance FROM finance ORDER BY id DESC LIMIT 1")
    result = cursor.fetchone()
    if not result:
        lastId, last_balance = 0, 0.0
    else:
        lastId, last_balance = result
    newId = lastId + 1
    recepit = data.get('recepit')
    if recepit:
        with open(f'Imgs/{newId}.jpg', 'wb') as f:
            f.write(base64.b64decode(recepit))
    credit = Decimal(str(data.get('credit', 0.0)))
    debit = Decimal(str(data.get('debit', 0.0)))
    new_balance = Decimal(str(last_balance)) + credit - debit
    new_balance = float(new_balance)
    cursor.execute("INSERT INTO finance (date, description, credit, debit, balance) VALUES (?, ?, ?, ?, ?)", (data['date'], data['description'], data['credit'], data['debit'], new_balance))
    conn.commit()
    conn.close()
    return jsonify({'new_balance': new_balance})


# 接口 - 修改一行
@app.route('/edit1', methods=['POST'])
@authChecker('admin')  # 只有admin可以访问
def edit1():
    data = request.json
    record_id = data.get('id')
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM finance WHERE id = ?", (record_id,))
    old_record = cursor.fetchone()
    if not old_record:
        conn.close()
        return jsonify({'error': '记录不存在'}), 404
    
    cursor.execute("SELECT balance FROM finance WHERE id < ? ORDER BY id DESC LIMIT 1", (record_id,))
    prev_result = cursor.fetchone()
    prev_balance = prev_result[0] if prev_result else 0.0
    
    credit = Decimal(str(data.get('credit', 0.0)))
    debit = Decimal(str(data.get('debit', 0.0)))
    new_balance = Decimal(str(prev_balance)) + credit - debit
    new_balance = float(new_balance)
    
    cursor.execute("UPDATE finance SET date = ?, description = ?, credit = ?, debit = ?, balance = ? WHERE id = ?", 
                   (data['date'], data['description'], data['credit'], data['debit'], new_balance, record_id))
    
    cursor.execute("SELECT id, credit, debit FROM finance WHERE id > ? ORDER BY id", (record_id,))
    following_records = cursor.fetchall()
    
    current_balance = new_balance
    for foll_id, foll_credit, foll_debit in following_records:
        current_balance = current_balance + float(foll_credit) - float(foll_debit)
        cursor.execute("UPDATE finance SET balance = ? WHERE id = ?", (current_balance, foll_id))
    
    conn.commit()
    conn.close()
    return jsonify({'new_balance': new_balance})


# 接口 - 删除一行
@app.route('/delete1', methods=['POST'])
@authChecker('admin')  # 只有admin可以访问
def delete1():
    data = request.json
    record_id = data.get('id')
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance FROM finance WHERE id = ?", (record_id,))
    record = cursor.fetchone()
    if not record:
        conn.close()
        return jsonify({'error': '记录不存在'}), 404
    
    cursor.execute("SELECT balance FROM finance WHERE id < ? ORDER BY id DESC LIMIT 1", (record_id,))
    prev_result = cursor.fetchone()
    prev_balance = prev_result[0] if prev_result else 0.0
    
    cursor.execute("DELETE FROM finance WHERE id = ?", (record_id,))
    
    cursor.execute("SELECT id, credit, debit FROM finance WHERE id > ? ORDER BY id", (record_id,))
    following_records = cursor.fetchall()
    
    current_balance = prev_balance
    for foll_id, foll_credit, foll_debit in following_records:
        current_balance = current_balance + float(foll_credit) - float(foll_debit)
        cursor.execute("UPDATE finance SET balance = ? WHERE id = ?", (current_balance, foll_id))
    
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})


print(app.url_map)
app.run(host='0.0.0.0', port='81', debug=True)
