"""
登录逻辑处理模块
支持cookie登录、表单登录和自动模式（先尝试cookie，失败后使用表单）
"""

import os
import time
from typing import Dict, Any, Optional, Tuple

from utils.selenium_browser import SeleniumBrowserManager
from utils.logger import get_logger

logger = get_logger()


class LoginHandler:
    """处理网站登录逻辑的类"""

    def __init__(self, browser: SeleniumBrowserManager, config: Dict[str, Any]):
        """
        初始化登录处理器
        
        Args:
            browser: 浏览器管理器实例
            config: 配置信息
        """
        self.browser = browser
        self.config = config
        self.website_config = config.get('WEBSITE', {})
        self.user_config = config.get('USER', {})
        self.login_config = config.get('LOGIN', {})
        self.elements_config = config.get('ELEMENTS', {}).get('login', {})
        self.login_check_config = config.get('ELEMENTS', {}).get('login_check', {})
        self.capsolver_config = config.get('CAPSOLVER', {})

        # 登录方式
        self.login_method = self.login_config.get('method', 'form')
        # Cookie路径
        self.cookie_path = self.login_config.get('cookie_path', 'cookies.json')
        # 是否保存Cookie
        self.save_cookie = self.login_config.get('save_cookie', True)

    def login(self) -> bool:
        """
        根据配置的方式进行登录
        
        Returns:
            登录是否成功
        """
        login_url = self.website_config.get('login_url', '')
        if not login_url:
            logger.error("登录URL未配置")
            return False

        # 根据登录方式选择登录逻辑
        if self.login_method == 'auto':
            logger.info("使用自动登录模式（优先尝试cookie登录）")
            # 先尝试Cookie登录
            success = self._cookie_login()
            # 如果Cookie登录失败，则使用表单登录
            if not success:
                logger.info("Cookie登录失败，切换到表单登录")
                success = self._form_login()
        elif self.login_method == 'cookie':
            logger.info("使用Cookie登录")
            success = self._cookie_login()
        else:  # 默认使用表单登录
            logger.info("使用表单登录")
            success = self._form_login()

        return success

    def _cookie_login(self) -> bool:
        """
        使用Cookie登录
        
        Returns:
            登录是否成功
        """
        # 检查Cookie文件是否存在
        if not os.path.exists(self.cookie_path):
            logger.warning(f"Cookie文件不存在: {self.cookie_path}")
            return False

        try:
            # 先打开首页
            self.browser.navigate_to(self.website_config.get('url', ''))
            time.sleep(2)  # 等待页面加载

            # 加载Cookie
            if not self.browser.load_cookies(self.cookie_path):
                logger.error("加载Cookie失败")
                return False

            # 刷新页面使Cookie生效
            self.browser.navigate_to(self.website_config.get('url', ''))
            time.sleep(2)  # 等待页面加载

            # 验证登录状态
            if self._verify_login_status():
                logger.info("Cookie登录成功")
                return True
            else:
                logger.warning("Cookie登录失败，可能已过期")
                # 删除过期的Cookie文件
                if os.path.exists(self.cookie_path):
                    os.remove(self.cookie_path)
                    logger.info(f"已删除过期的Cookie文件: {self.cookie_path}")
                return False

        except Exception as e:
            logger.error(f"Cookie登录过程出错: {e}")
            return False

    def _form_login(self) -> bool:
        """
        使用表单登录
        
        Returns:
            登录是否成功
        """
        try:
            # 打开登录页面
            self.browser.navigate_to(self.website_config.get('login_url', ''))
            time.sleep(2)  # 等待页面加载

            # 填写用户名
            username = self.user_config.get('username', '')
            if not username:
                logger.error("用户名未配置")
                return False

            if not self.browser.fill_input(self.elements_config.get('username_input', {}), username):
                logger.error("填写用户名失败")
                return False

            # 填写密码
            password = self.user_config.get('password', '')
            if not password:
                logger.error("密码未配置")
                return False

            if not self.browser.fill_input(self.elements_config.get('password_input', {}), password):
                logger.error("填写密码失败")
                return False

            # 点击登录按钮
            if not self.browser.click_element(self.elements_config.get('submit_button', {})):
                logger.error("点击登录按钮失败")
                return False

            time.sleep(3)

            # 检查是否需要处理Cloudflare Turnstile验证码
            result, token = self._handle_turnstile_captcha()
            if result:
                # 如果验证码处理成功，可能需要等待一段时间
                time.sleep(3)

            script = f"""
            fetch('/api/account/signIn', {{
                method: 'POST',
                headers: {{
                    'content-type': 'application/json'
                }},
                body: JSON.stringify({{
                    username: '{username}',
                    password: '{password}',
                    token: '{token}',
                    source: 'turnstile'
                }})
            }}).then(response => response.json())
            .then(data => {{
                    if (data.success) {{
                        location.href = '/';
                    }} else {{
                        console.log(data.message || '操作失败');
                    }}
                }});
            """
            self.browser.driver.execute_script(script)
            logger.info(f"已模拟Turnstile回调并发送登录请求，token: {token}")

            # 验证登录状态
            if self._verify_login_status():
                logger.info("表单登录成功")

                # 如果设置了保存Cookie，则保存
                if self.save_cookie:
                    if self.browser.save_cookies(self.cookie_path):
                        logger.info(f"已保存Cookie到: {self.cookie_path}")
                    else:
                        logger.warning("保存Cookie失败")

                return True
            else:
                logger.error("表单登录失败，请检查用户名和密码")
                return False

        except Exception as e:
            logger.error(f"表单登录过程出错: {e}")
            return False

    def _verify_login_status(self) -> bool:
        """
        验证是否已登录
        
        Returns:
            是否已登录
        """
        # 优先使用浏览器的验证方法
        if hasattr(self.browser, 'verify_login_status'):
            return self.browser.verify_login_status()

        # 备用方法：通过检查特定元素
        # if self.login_check_config:
        #     # 检查登录状态的元素是否存在
        #     logged_in_element = self.login_check_config.get('logged_in_element', {})
        #     logged_out_element = self.login_check_config.get('logged_out_element', {})
        #
        #     if logged_in_element and self.browser.is_element_present(logged_in_element, wait_time=3):
        #         return True
        #
        #     if logged_out_element and self.browser.is_element_present(logged_out_element, wait_time=3):
        #         return False
        #
        #     # 如果无法判断，假设已登录
        #     logger.warning("无法确定登录状态，默认为已登录")
        #     return True
        #
        # # 没有配置登录检查，假设成功
        # logger.warning("未配置登录检查元素，默认登录成功")
        return False

    def _handle_turnstile_captcha(self) -> tuple[bool, str | None]:
        """
        处理Cloudflare Turnstile验证码
        
        Returns:
            是否成功处理验证码
        """
        # 检查是否启用了Capsolver
        if not self.capsolver_config.get('enabled', False):
            logger.debug("Capsolver未启用，跳过验证码处理")
            return False, None

        # 检查是否启用了Turnstile验证码
        turnstile_config = self.capsolver_config.get('captcha_types', {}).get('turnstile', {})
        if not turnstile_config.get('enabled', False):
            logger.debug("Turnstile验证码未启用，跳过处理")
            return False, None

        # 检查页面上是否存在Turnstile验证码
        if not self.browser.is_element_present({'type': 'name', 'value': 'cf-turnstile-response'}, wait_time=3):
            logger.debug("页面上未检测到Turnstile验证码")
            return False, None

        try:
            site_key = turnstile_config.get('site_key', '')
            if not site_key:
                logger.error("Turnstile site_key未配置")
                return False, None

            # 获取当前URL
            current_url = self.browser.driver.current_url

            # 解决验证码
            token = self.browser.solve_turnstile(site_key, current_url)
            if not token:
                logger.error("解决Turnstile验证码失败")
                return False, None

            # 注入验证码解决方案
            self.browser.inject_token(token)
            logger.info("成功处理Turnstile验证码")
            return True, token

        except Exception as e:
            logger.error(f"处理Turnstile验证码时出错: {e}")
            return False, None
