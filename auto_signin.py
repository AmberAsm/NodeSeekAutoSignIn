#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自动签到脚本主程序
"""

import argparse
import datetime
import os
import sys
import time
from typing import Dict, Any, Optional, Tuple

import schedule

import config
from login_handler import LoginHandler
from utils.notifier import Notifier

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.logger import setup_logger, get_logger, logger
from utils.selenium_browser import SeleniumBrowserManager


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        解析后的参数
    """
    parser = argparse.ArgumentParser(description='自动签到脚本')
    parser.add_argument('--headless', action='store_true', help='启用无头模式（不显示浏览器界面）')

    return parser.parse_args()


def perform_sign_in(browser_manager: SeleniumBrowserManager, config: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
    """
    执行签到操作
    
    Args:
        browser_manager: 浏览器管理器
        config: 配置信息
        
    Returns:
        (签到是否成功, 结果消息, 截图路径)
    """
    logger = get_logger()
    elements_config = config.get('ELEMENTS', {}).get('signin', {})
    website_config = config.get('WEBSITE', {})
    browser_config = config.get('BROWSER', {})
    signin_url = website_config.get('signin_url')
    signin_button = elements_config.get('signin_button')
    success_message = elements_config.get('success_message')
    # 是否截图
    take_screenshot = browser_config.get('screenshots', False)
    screenshot_path = None

    if not signin_url:
        logger.error("签到URL未配置")
        return False, "签到URL未配置", None

    try:
        # 导航到签到页面
        browser_manager.navigate_to(signin_url)
        time.sleep(2)  # 等待页面加载

        # 检查是否已经签到
        if success_message and browser_manager.is_element_present(success_message, wait_time=3):
            result_text = browser_manager.get_element_text(success_message)
            logger.info(f"今日已签到，无需重复操作: {result_text}")
            # 保存签到记录
            return True, result_text or "今日已签到", ""

        # 点击签到按钮
        if not browser_manager.click_element(signin_button):
            logger.error("点击签到按钮失败")
            return False, "点击签到按钮失败", None

        # 等待签到结果
        time.sleep(2)

        # 检查是否签到成功
        if success_message and browser_manager.is_element_present(success_message, wait_time=3):
            # 获取签到成功的消息
            result_text = browser_manager.get_element_text(success_message)
            logger.info(f"签到成功: {result_text}")

            # 截图保存
            if take_screenshot:
                screenshot_path = os.path.join("Screenshots",
                                               f"signin_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                browser_manager.take_screenshot(screenshot_path)
                logger.info(f"已保存签到成功截图: {screenshot_path}")

            return True, result_text or "签到成功", screenshot_path
        else:
            logger.warning("签到失败，未检测到成功消息")
            # 截图保存
            if take_screenshot:
                screenshot_path = os.path.join("Screenshots",
                                               f"signin_failed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                browser_manager.take_screenshot(screenshot_path)
                logger.info(f"已保存签到失败截图: {screenshot_path}")

            return False, "签到失败，未检测到成功消息", screenshot_path

    except Exception as e:
        message = f"签到过程中出错: {e}"
        logger.error(message)
        return False, message, None


def check_environment():
    """检查运行环境"""
    logger.info(f"Python 版本: {sys.version}")
    logger.info(f"操作系统: {sys.platform}")
    logger.info(f"工作目录: {os.getcwd()}")

    # 检查配置
    required_configs = ['WEBSITE', 'USER', 'LOGIN', 'BROWSER', 'ELEMENTS']
    for cfg in required_configs:
        if not hasattr(config, cfg):
            logger.error(f"缺少关键配置: {cfg}")
            return False

    # 检查BROWSER配置
    if not config.BROWSER.get('type'):
        logger.error("未指定浏览器类型")
        return False

    return True


def run_signin_task():
    logger.info("=" * 50)
    logger.info("自动签到脚本启动")
    logger.info(f"当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    notifier = Notifier(config.__dict__)

    try:
        browser_manager = None
        try:
            # 创建浏览器实例
            browser_manager = SeleniumBrowserManager(config.__dict__)
            # 初始化浏览器
            browser_manager.initialize_driver()
            # 创建登录处理器
            login_handler = LoginHandler(browser_manager, config.__dict__)
            # 执行登录
            login_success = False
            retry_count = config.RETRY.get('max_attempts', 3)
            retry_delay = config.RETRY.get('delay', 5)
            for attempt in range(retry_count):
                try:
                    logger.info(f"登录尝试 {attempt + 1}/{retry_count}")
                    if login_handler.login():
                        login_success = True
                        break
                    else:
                        logger.warning(f"登录失败，等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                except Exception as e:
                    logger.error(f"登录过程出错: {e}")
                    if attempt < retry_count - 1:
                        logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
            if not login_success:
                logger.error("登录失败次数超过最大重试次数，任务终止")
                return

            logger.info("登录成功，准备签到")
            # 签到流程
            signin_success = False
            signin_result = ""
            screenshot_path = ""

            for attempt in range(retry_count):
                try:
                    logger.info(f"签到尝试 {attempt + 1}/{retry_count}")
                    result = perform_sign_in(browser_manager, config.__dict__)
                    if isinstance(result, tuple) and len(result) == 3:
                        success, message, screenshot = result
                        if success:
                            signin_success = True
                            signin_result = message
                            screenshot_path = screenshot
                            break
                    else:
                        logger.warning(f"签到失败，等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                except Exception as e:
                    logger.error(f"签到过程出错: {e}")
                    if attempt < retry_count - 1:
                        logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)

            if signin_success:
                logger.info("签到流程完成")
                notifier.send_notification(
                    "NodeSeek签到成功",
                    f"签到结果: {signin_result}",
                    success=True,
                    screenshot_path=screenshot_path
                )
            else:
                logger.error("签到失败次数超过最大重试次数")
                notifier.send_notification(
                    "NodeSeek签到失败",
                    "签到失败次数超过最大重试次数",
                    success=False
                )

        finally:
            # 关闭浏览器
            if browser_manager:
                logger.info("关闭浏览器")
                browser_manager.close()

    except Exception as e:
        logger.error(f"签到任务执行失败: {e}")

    logger.info("=== NodeSeek自动签到任务结束 ===")


def setup_schedule():
    """设置定时任务"""
    schedule_config = config.SCHEDULE

    if not schedule_config.get('enabled', False):
        logger.info("定时任务未启用")
        return False

    schedule_time = schedule_config.get('time', '08:00')
    try:
        # 验证时间格式
        hour, minute = schedule_time.split(':')
        hour, minute = int(hour), int(minute)
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError("时间格式不正确")

        logger.info(f"设置定时任务，每天 {schedule_time} 执行签到")
        schedule.every().day.at(schedule_time).do(run_signin_task)
        return True

    except (ValueError, AttributeError) as e:
        logger.error(f"设置定时任务失败: {e}")
        return False


def run_scheduler():
    """运行定时调度器"""
    logger.info("启动定时调度器")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("用户中断，程序退出")
    except Exception as e:
        logger.error(f"调度器运行出错: {e}")


def main():
    """主程序入口"""
    # 解析命令行参数
    args = parse_arguments()

    # 设置日志
    setup_logger(config.LOGGING)

    # 检查运行环境
    if not check_environment():
        logger.error("运行环境检查失败")
        return

    # 创建通知器实例
    notifier = Notifier(config.__dict__)

    try:
        # 立即执行一次签到
        logger.info("立即执行签到任务")
        run_signin_task()

        # 设置定时任务
        schedule_enabled = setup_schedule()

        # 如果设置了定时任务，启动调度器
        if schedule_enabled:
            # 如果只运行定时任务且当前时间接近设定时间，可以考虑先执行一次
            current_time = datetime.datetime.now().time()
            schedule_time = config.SCHEDULE.get('time', '08:00')
            schedule_hour, schedule_minute = map(int, schedule_time.split(':'))
            schedule_time_obj = datetime.time(hour=schedule_hour, minute=schedule_minute)

            # 如果当前时间在设定时间的前后5分钟内，立即执行一次
            time_diff = abs((current_time.hour * 60 + current_time.minute) -
                            (schedule_hour * 60 + schedule_minute))
            if time_diff <= 5:
                logger.info(f"当前时间接近设定的签到时间 {schedule_time}，立即执行一次签到")
                run_signin_task()

            # 通知已设置定时任务
            if hasattr(config, 'TELEGRAM') and config.TELEGRAM.get('enabled', False):
                notifier.send_notification(
                    "NodeSeek签到任务已设置",
                    f"定时任务已设置，将在每天 {config.SCHEDULE.get('time', '08:00')} 自动执行签到",
                    success=True
                )

            # 运行调度器
            logger.info(f"开始等待定时任务执行，每天 {config.SCHEDULE.get('time', '08:00')} 自动签到")
            run_scheduler()
        else:
            # 如果没有启用定时任务，提示用户
            logger.warning("未启用定时任务，程序执行后自动退出")
    except Exception as e:
        logger.error(f"程序运行时出错: {e}")

        # 发送错误通知
        if hasattr(config, 'TELEGRAM') and config.TELEGRAM.get('enabled', False):
            notifier = Notifier(config.__dict__)
            notifier.send_notification(
                "NodeSeek签到程序出错",
                f"程序运行时出错: {str(e)}",
                success=False
            )

        sys.exit(1)


if __name__ == "__main__":
    main()
