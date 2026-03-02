<!--
 * @Author: Monterry
 * @Date: 2026-03-02
   -->
# Finance Table - v2版本

本人根据原作者的程序进行了一些改进

## 使用方法

1. 配置好Python环境，并安装```flask```库

2. 设置访问密码：当前目录下新建```mySecrets.py```，```password```对应的键值即为密码
   ```python
   users = {
       'admin': {
           'password': 'admin',
           'role': 'admin'  # 管理员账户:可以进行任何操作（新增、编辑、删除）
       },
       'guest': {
           'password': 'guest',
           'role': 'readonly'  # 只读
       }
   }
   ```
   
3. 当前目录下运行```main.py```并进入localhost:81即可访问

## 

