"""
配置文件示例
使用前请复制此文件为 config.py 并填入你的个人信息
"""

# 网站配置
WEBSITE = {
    'name': 'nodeseek',  # 网站名称
    'url': 'https://www.nodeseek.com',  # 网站地址
    'login_url': 'https://www.nodeseek.com/signIn.html',  # 登录页面地址
    'signin_url': 'https://www.nodeseek.com/board',  # 签到页面地址
}

# 用户信息
USER = {
    'username': 'your_username',  # 登录用户名
    'password': 'your_password',    # 登录密码
}

# 登录方式配置
LOGIN = {
    'method': 'auto',  # 登录方式: form(表单登录)、cookie(Cookie登录)或auto(优先使用cookie，失败后使用表单)
    'cookie_path': 'cookies.json',  # Cookie保存路径，仅在cookie或auto登录方式下有效
    'save_cookie': True,  # 是否在表单登录成功后保存Cookie
}

# Capsolver验证码配置
CAPSOLVER = {
    'enabled': True,  # 是否启用Capsolver验证码识别
    'api_key': 'CAP-YOUR_API_KEY_HERE',     # Capsolver API密钥
    'captcha_types': {
        'recaptcha_v2': {
            'enabled': False,  # 是否启用reCAPTCHA v2识别
            'site_key': '',    # Google reCAPTCHA v2 site key
        },
        'hcaptcha': {
            'enabled': False,  # 是否启用hCaptcha识别
            'site_key': '',    # hCaptcha site key
        },
        'turnstile': {
            'enabled': True,  # 是否启用Cloudflare Turnstile识别
            'site_key': '0x4AAAAAAAaNy7leGjewpVyR',    # Cloudflare Turnstile site key
        }
    },
    'timeout': 60,     # 识别超时时间(秒)
}

# 浏览器配置
BROWSER = {
    'type': 'chrome',  # 浏览器类型：chrome、firefox 或 safari
    'headless': True,  # 是否使用无头模式（不显示浏览器窗口）
    'timeout': 10,  # 等待元素加载的超时时间（秒）
    'screenshots': True,  # 是否启用截图功能
}

# 网页元素定位信息（根据实际网站调整）
ELEMENTS = {
    'login': {
        'username_input': {'type': 'id', 'value': 'stacked-email'},  # 用户名输入框
        'password_input': {'type': 'id', 'value': 'stacked-password'},  # 密码输入框
        'submit_button': {'type': 'xpath', 'value': '//button[@type="submit"]'},  # 登录按钮
    },
    'signin': {
        'signin_button': {'type': 'xpath', 'value': '//button[contains(text(), "试试手气")]'},  # 签到按钮
        'success_message': {'type': 'xpath', 'value': '//div[contains(text(), "今日签到获得鸡腿")]'},  # 签到成功的消息
    },
    'login_check': {
        'logged_in_element': {'type': 'xpath', 'value': '//a[contains(@href, "logout")]'},  # 已登录状态下存在的元素（如退出登录按钮）
        'logged_out_element': {'type': 'xpath', 'value': '//a[contains(@href, "login")]'},  # 未登录状态下存在的元素（如登录按钮）
    }
}

# 定时任务配置
SCHEDULE = {
    'enabled': True,  # 是否启用定时任务
    'time': '01:00',  # 每天执行时间
}

# 邮件通知配置（可选.测试时用的AWS邮箱服务）
EMAIL = {
    'enabled': True,  # 是否启用邮件通知
    'smtp_server': 'smtp.example.com',  # SMTP服务器
    'smtp_port': 587,  # SMTP端口
    'sender': 'your_email@example.com',  # 发件人邮箱
    'username': 'your_smtp_username',  # 发件人邮箱用户名
    'password': 'your_smtp_password',  # 发件人邮箱密码或应用专用密码
    'receiver': 'receiver@example.com',  # 收件人邮箱
}

# Telegram通知配置（需自行编写通知）
TELEGRAM = {
    'enabled': False,  # 是否启用Telegram通知
    'token': 'YOUR_BOT_TOKEN',  # Telegram bot token
    'url': 'http://bot.example.com/notice',  # Telegram bot url
}

# 日志配置
LOGGING = {
    'level': 'DEBUG',  # 日志级别：DEBUG, INFO, WARNING, ERROR
    'file': 'logs/auto_signin.log',  # 日志文件名
    'max_size': '10 MB',  # 单个日志文件最大大小
    'backup_count': 3,  # 保留的备份日志文件数量
}

# 重试配置
RETRY = {
    'max_attempts': 3,  # 最大重试次数
    'delay': 5,  # 重试间隔（秒）
}
