"""
使用 Selenium 实现的浏览器管理模块
"""

import os
import json
import time
from typing import Dict, Any, Optional, Union

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from utils.logger import get_logger

logger = get_logger()
# 当Capsolver启用时导入
try:
    import capsolver
except ImportError:
    capsolver = None


class SeleniumBrowserManager:
    """Selenium浏览器管理类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化浏览器管理器
        
        Args:
            config: 浏览器配置信息
        """
        # self.config = config
        browser_config = config.get('BROWSER', {})
        self.timeout = browser_config.get('timeout', 30)
        self.browser_type = browser_config.get('type', 'chrome').lower()
        self.headless = browser_config.get('headless', False)
        self.driver = None
        self.wait = None

        # Capsolver配置
        self.capsolver_config = config.get('CAPSOLVER', {})
        if self.capsolver_config.get('enabled', False) and capsolver:
            capsolver.api_key = self.capsolver_config.get('api_key', '')
            logger.info("Capsolver已启用")
        else:
            logger.debug("Capsolver未启用或未安装")

    def initialize_driver(self) -> webdriver.Remote:
        """
        初始化WebDriver
        
        Returns:
            WebDriver实例
        """
        try:
            logger.info(f"初始化{self.browser_type}浏览器 (无头模式: {self.headless})")
            return self._init_chrome_driver()
        except Exception as e:
            logger.error(f"初始化WebDriver失败: {e}")
            raise

    def _init_chrome_driver(self) -> webdriver.Chrome:
        """初始化Chrome WebDriver，使用undetected_chromedriver"""
        try:
            # 从配置文件获取所有Chrome选项
            options = uc.ChromeOptions()

            # 基本设置 - 这些参数对所有模式都有效
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--start-maximized')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-blink-features=AutomationControlled')

            # 设置窗口大小为普通显示器尺寸
            options.add_argument('--window-size=1920,1080')

            # 默认使用最新的Chrome User-Agent
            options.add_argument(
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

            # 创建undetected_chromedriver实例 - 不在选项中设置headless，而是通过参数传递
            driver = uc.Chrome(
                options=options,
                driver_executable_path=None,
                headless=self.headless,
                use_subprocess=True,  # 使用子进程可以提高稳定性
                version_main=None,  # None表示使用最新版本
            )

            # 获取chome浏览器版本
            version = driver.capabilities['browserVersion']
            logger.info(f"Chrome浏览器版本: {version}")

            # 设置页面加载超时
            driver.set_page_load_timeout(self.timeout)

            # 如果使用无头模式，添加额外的反检测脚本
            if self.headless:
                self._inject_anti_detection_scripts(driver)

            self.driver = driver
            self.wait = WebDriverWait(driver, self.timeout)
            return driver

        except Exception as e:
            logger.error(f"初始化Chrome WebDriver失败: {e}")
            raise

    def _inject_anti_detection_scripts(self, driver):
        """注入反检测JavaScript脚本"""
        try:
            anti_detection_js = """
            // 修改navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 添加Chrome插件
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 修改window.chrome对象
            window.chrome = {
                runtime: {}
            };
            
            // 修改屏幕和窗口属性
            Object.defineProperty(window, 'outerWidth', { get: () => 1920 });
            Object.defineProperty(window, 'outerHeight', { get: () => 1080 });
            Object.defineProperty(screen, 'width', { get: () => 1920 });
            Object.defineProperty(screen, 'height', { get: () => 1080 });
            Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
            """

            driver.execute_script(anti_detection_js)
            logger.info("成功注入反检测JavaScript")
        except Exception as e:
            logger.error(f"注入反检测脚本失败: {e}")

    def _init_firefox_driver(self) -> webdriver.Firefox:
        """初始化Firefox WebDriver"""
        try:
            options = FirefoxOptions()

            if self.headless:
                options.add_argument('--headless')
            if self.user_agent:
                options.set_preference('general.useragent.override', self.user_agent)

            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)

            self.driver = driver
            self.wait = WebDriverWait(driver, self.timeout)
            return driver

        except Exception as e:
            logger.error(f"初始化Firefox WebDriver失败: {e}")
            raise

    def _init_edge_driver(self) -> webdriver.Edge:
        """初始化Edge WebDriver"""
        try:
            options = EdgeOptions()

            if self.headless:
                options.add_argument('--headless')
            if self.user_agent:
                options.add_argument(f'--user-agent={self.user_agent}')

            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)

            self.driver = driver
            self.wait = WebDriverWait(driver, self.timeout)
            return driver

        except Exception as e:
            logger.error(f"初始化Edge WebDriver失败: {e}")
            raise

    def navigate_to(self, url: str) -> None:
        """
        导航到指定URL
        
        Args:
            url: 目标网页URL
        """
        logger.info(f"导航至: {url}")
        self.driver.get(url)
        # 等待页面加载完成
        self.driver.execute_script("return document.readyState") == "complete"

    def find_element(self, element_config: Dict[str, str], wait_time: Optional[int] = None) -> Optional[
        webdriver.remote.webelement.WebElement]:
        """
        查找网页元素
        
        Args:
            element_config: 元素定位配置
            wait_time: 等待时间（秒）
            
        Returns:
            找到的元素或None
        """
        if not element_config:
            logger.error("元素配置为空")
            return None

        locator_type = element_config.get('type', '').lower()
        locator_value = element_config.get('value', '')

        if not locator_type or not locator_value:
            logger.error(f"元素定位信息不完整: {element_config}")
            return None

        wait_time = wait_time or self.timeout

        try:
            # 转换定位器类型
            by_type = self._get_selenium_by(locator_type)

            # 使用显式等待查找元素
            element = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((by_type, locator_value))
            )

            return element

        except TimeoutException:
            logger.warning(f"超时: 未找到元素 {locator_type}='{locator_value}'")
            return None
        except Exception as e:
            logger.error(f"查找元素时出错: {e}")
            return None

    def _get_selenium_by(self, locator_type: str) -> str:
        """
        转换定位器类型为Selenium的By类型
        
        Args:
            locator_type: 定位器类型
            
        Returns:
            Selenium的By类型
        """
        locator_map = {
            'id': By.ID,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'tag': By.TAG_NAME,
            'link_text': By.LINK_TEXT,
            'partial_link_text': By.PARTIAL_LINK_TEXT,
            'xpath': By.XPATH,
            'css': By.CSS_SELECTOR
        }
        return locator_map.get(locator_type, By.CSS_SELECTOR)

    def click_element(self, element_config: Dict[str, str], retry_count: int = 1) -> bool:
        """
        点击指定元素
        
        Args:
            element_config: 元素定位配置
            retry_count: 重试次数
            
        Returns:
            是否成功点击
        """
        for attempt in range(retry_count):
            try:
                element = self.find_element(element_config)
                if element:
                    # 等待元素可点击
                    WebDriverWait(self.driver, self.timeout).until(
                        EC.element_to_be_clickable((
                            self._get_selenium_by(element_config['type']),
                            element_config['value']
                        ))
                    )

                    # 点击元素
                    element.click()
                    logger.info(f"成功点击元素: {element_config.get('value')}")
                    return True

            except Exception as e:
                logger.warning(f"点击失败 (尝试 {attempt + 1}/{retry_count}): {e}")

            # 如果失败且还有重试次数，等待后重试
            if attempt < retry_count - 1:
                time.sleep(1)

        return False

    def fill_input(self, element_config: Dict[str, str], text: str) -> bool:
        """
        填写输入框
        
        Args:
            element_config: 元素定位配置
            text: 要输入的文本
            
        Returns:
            是否成功填写
        """
        try:
            element = self.find_element(element_config)
            if element:
                # 清空输入框
                element.clear()
                # 填写文本
                element.send_keys(text)
                logger.info(f"已在 {element_config.get('value')} 输入文本")
                return True
            return False
        except Exception as e:
            logger.error(f"填写输入框时出错: {e}")
            return False

    def is_element_present(self, element_config: Dict[str, str], wait_time: Optional[int] = None) -> bool:
        """
        检查元素是否存在
        
        Args:
            element_config: 元素定位配置
            wait_time: 等待时间（秒）
            
        Returns:
            元素是否存在
        """
        element = self.find_element(element_config, wait_time)
        return element is not None

    def get_element_text(self, element_config: Dict[str, str]) -> Optional[str]:
        """
        获取元素文本内容
        
        Args:
            element_config: 元素定位配置
            
        Returns:
            元素文本或None
        """
        element = self.find_element(element_config)
        if element:
            return element.text
        return None

    def take_screenshot(self, filename: str) -> bool:
        """
        截取当前页面的屏幕截图
        
        Args:
            filename: 保存的文件名
            
        Returns:
            是否成功截图
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            # 截图
            self.driver.save_screenshot(filename)
            logger.info(f"截图已保存至 {filename}")
            return True
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return False

    def save_cookies(self, filename: str) -> bool:
        """
        保存cookies到文件
        
        Args:
            filename: 保存的文件名
            
        Returns:
            是否保存成功
        """
        try:
            # 获取所有cookies
            cookies = self.driver.get_cookies()

            # # 确保目录存在
            # os.makedirs(os.path.dirname(filename), exist_ok=True)

            # 保存cookies到文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)

            logger.info(f"Cookies已保存至 {filename}")
            return True
        except Exception as e:
            logger.error(f"保存cookies失败: {e}")
            return False

    def load_cookies(self, filename: str) -> bool:
        """
        从文件加载cookies
        
        Args:
            filename: cookies文件路径
            
        Returns:
            是否加载成功
        """
        try:
            if not os.path.exists(filename):
                logger.error(f"Cookies文件不存在: {filename}")
                return False

            # 读取cookies文件
            with open(filename, 'r', encoding='utf-8') as f:
                cookies = json.load(f)

            # 添加cookies
            for cookie in cookies:
                self.driver.add_cookie(cookie)

            logger.info(f"已从 {filename} 加载cookies")
            return True
        except Exception as e:
            logger.error(f"加载cookies失败: {e}")
            return False

    def verify_login_status(self) -> bool:
        # 验证登录状态  查找<a href="/api/account/signOut" title="登出">
        if self.is_element_present({'type': 'xpath', 'value': '//a[@href="/api/account/signOut" and @title="登出"]'}, wait_time=3):
            return True
        else:
            return False

    def close(self) -> None:
        """关闭浏览器"""
        try:
            if self.driver:
                logger.info("关闭浏览器")
                self.driver.quit()
                self.driver = None
        except Exception as e:
            logger.error(f"关闭浏览器时出错: {e}")

    def solve_turnstile(self, site_key: str, url: str) -> Optional[str]:
        """
        解决Cloudflare Turnstile验证码

        Args:
            site_key: Turnstile site key
            url: 页面URL

        Returns:
            验证码解决方案或None（如果解决失败）
        """
        if not self.capsolver_config.get('enabled', False):
            logger.warning("Capsolver未启用，无法解决Turnstile")
            return None

        api_key = self.capsolver_config.get('api_key')
        if not api_key:
            logger.error("未配置Capsolver API密钥")
            return None

        # 检查是否已导入新版Cloudflare模块
        try:
            from python3_capsolver.cloudflare import Cloudflare
            from python3_capsolver.core.enum import CaptchaTypeEnm
            is_new_api = True
        except ImportError:
            is_new_api = False

        logger.info(f"正在使用Capsolver解决Turnstile (site_key: {site_key})")

        try:
            # 创建任务参数
            task_payload = {
                "websiteURL": url,
                "websiteKey": site_key
            }

            # 使用新版API
            if is_new_api:
                try:
                    # 使用异步API
                    import asyncio

                    # 创建Cloudflare对象
                    cloudflare = Cloudflare(
                        api_key=api_key,
                        captcha_type=CaptchaTypeEnm.AntiTurnstileTaskProxyLess
                    )

                    # 执行验证码任务
                    response = asyncio.run(cloudflare.aio_captcha_handler(task_payload=task_payload))

                    # 获取任务ID
                    while True:
                        time.sleep(1)  # delay
                        payload = {"clientKey": api_key, "taskId": response.get("taskId")}
                        res = requests.post("https://api.capsolver.com/getTaskResult", json=payload)
                        resp = res.json()
                        status = resp.get("status")
                        if status == "ready":
                            solution = resp.get("solution", {}).get('token')
                            logger.info("成功解决Turnstile")
                            return solution
                        elif status == "failed" or resp.get("errorId"):
                            logger.error(f"解决Turnstile时出错: {resp.get('errorId')}")
                            return None
                        else:
                            logger.debug("等待验证码识别结果...")

                except Exception as e:
                    logger.error(f"使用新版API解决Turnstile时出错: {e}")
                    # 如果新API失败，尝试回退到旧API

            # 使用旧版API
            if not is_new_api or 'solution' not in locals():
                # 添加任务类型
                task_payload["type"] = "TurnstileTaskProxyLess"

                timeout = self.capsolver_config.get('timeout', 60)
                task_id = capsolver.create_task(task_payload)
                logger.debug(f"已创建Turnstile任务 (ID: {task_id})")

                start_time = time.time()
                solution = None

                # 等待验证码解决结果
                while time.time() - start_time < timeout:
                    # 获取任务结果
                    response = capsolver.get_task_result(task_id)

                    if response.get('status') == 'ready':
                        solution = response.get('solution', {}).get('token')
                        logger.info("成功解决Turnstile")
                        break

                    # 等待后再次查询
                    time.sleep(5)

            return solution

        except Exception as e:
            logger.error(f"解决Turnstile时出错: {e}")
            return None

    def inject_token(self, token: str) -> None:
        """
        注入Cloudflare Turnstile验证码解决方案

        Args:
            token: 验证码解决方案
        """
        script = f"""
        let element = document.getElementsByName('cf-turnstile-response')[0];
        element.value = '{token}';
        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
        """
        self.driver.execute_script(f"document.getElementsByName('cf-turnstile-response')[0].value = '{token}';")
        logger.info(f"已注入Cloudflare Turnstile验证码解决方案: {token}")

    def get_page_source(self) -> str:
        """
        获取当前页面的HTML源码
        
        Returns:
            HTML源码字符串
        """
        try:
            return self.driver.page_source
        except Exception as e:
            logger.error(f"获取页面源码时出错: {e}")
            return None
