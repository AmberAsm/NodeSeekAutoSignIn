"""
通知模块，支持Telegram通知和邮件通知
"""

import os
import requests
import json
import traceback
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
from typing import Dict, Any, Optional, List

from utils.logger import get_logger

logger = get_logger()

class Notifier:
    """通知管理类，支持多种通知方式"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化通知管理器
        
        Args:
            config: 配置信息
        """
        self.config = config
        
        # Telegram通知配置
        self.telegram_config = config.get('TELEGRAM', {})
        self.telegram_enabled = self.telegram_config.get('enabled', False)
        
        if self.telegram_enabled:
            self.telegram_token = self.telegram_config.get('token', '')
            self.telegram_url = self.telegram_config.get('url', '')
            if not self.telegram_token or not self.telegram_url:
                logger.warning("Telegram配置不完整，无法发送通知")
                self.telegram_enabled = False
            else:
                logger.info("Telegram通知已启用")
        else:
            logger.debug("Telegram通知未启用")
            
        # 邮件通知配置
        self.email_config = config.get('EMAIL', {})
        self.email_enabled = self.email_config.get('enabled', False)
        
        if self.email_enabled:
            self.smtp_server = self.email_config.get('smtp_server', '')
            self.smtp_port = self.email_config.get('smtp_port', 587)
            self.email_sender = self.email_config.get('sender', '')
            self.email_username = self.email_config.get('username', '')
            self.email_password = self.email_config.get('password', '')
            self.email_receiver = self.email_config.get('receiver', '')
            
            if not all([self.smtp_server, self.smtp_port, self.email_sender, 
                        self.email_password, self.email_receiver]):
                logger.warning("邮件配置不完整，无法发送邮件通知")
                self.email_enabled = False
            else:
                logger.info("邮件通知已启用")
        else:
            logger.debug("邮件通知未启用")

    def send_notification(self, title: str, message: str, success: bool = True, screenshot_path: Optional[str] = None) -> bool:
        """
        发送通知
        
        Args:
            title: 通知标题
            message: 通知内容
            success: 是否成功通知
            screenshot_path: 截图路径(可选)
            
        Returns:
            是否成功发送任一通知
        """
        results = []
        
        # 发送Telegram通知.暂时不能发送图片
        if self.telegram_enabled:
            telegram_result = self.send_telegram(title, message, success, None)
            results.append(telegram_result)
            
        # 发送邮件通知
        if self.email_enabled:
            email_result = self.send_email(title, message, success, screenshot_path)
            results.append(email_result)
            
        # 只要有一个通知发送成功，就返回True
        return any(results) if results else False
    
    def send_telegram(self, title: str, message: str, success: bool = True, screenshot_path: Optional[str] = None) -> bool:
        """
        发送Telegram通知
        
        Args:
            title: 通知标题
            message: 通知内容
            success: 是否成功通知
            screenshot_path: 截图路径(可选)
            
        Returns:
            是否成功发送通知
        """
        if not self.telegram_enabled:
            return False
            
        try:
            # 构建通知内容
            status_emoji = "✅" if success else "❌"
            content = f"{status_emoji} *{title}*\n\n{message}"
            
            # 构建表单数据
            form_data = {
                "token": self.telegram_token,
                "content": content,
                "title": title,
            }
            
            # 发送请求 - 使用POST Form形式
            response = requests.post(
                self.telegram_url,
                data=form_data,  # 直接传递字典，不使用json.dumps()
                timeout=10
            )
            
            # 检查响应
            if response.status_code == 200:
                logger.info(f"Telegram通知发送成功: {title}")
                
                # 如果有截图，则另外发送
                if screenshot_path and os.path.exists(screenshot_path):
                    try:
                        # 尝试发送图片
                        files = {'image': open(screenshot_path, 'rb')}
                        image_form_data = {
                            "token": self.telegram_token,
                            "title": f"{title} - 截图"
                        }
                        
                        img_response = requests.post(
                            self.telegram_url,
                            data=image_form_data,
                            files=files,
                            timeout=30
                        )
                        
                        if img_response.status_code == 200:
                            logger.info(f"Telegram截图发送成功: {screenshot_path}")
                        else:
                            logger.warning(f"Telegram截图发送失败: {img_response.status_code} - {img_response.text}")
                    except Exception as img_e:
                        logger.warning(f"发送Telegram截图时出错: {img_e}")
                    
                return True
            else:
                logger.error(f"Telegram通知发送失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"发送Telegram通知时出错: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def send_email(self, title: str, message: str, success: bool = True, screenshot_path: Optional[str] = None,
                 additional_images: Optional[List[str]] = None) -> bool:
        """
        发送邮件通知，支持发送截图和额外的图片附件
        
        Args:
            title: 邮件主题
            message: 邮件内容
            success: 是否成功通知
            screenshot_path: 截图路径(可选)
            additional_images: 额外的图片路径列表(可选)
            
        Returns:
            是否成功发送邮件
        """
        if not self.email_enabled:
            return False
            
        try:
            # 创建一个带有附件的邮件对象
            msg = MIMEMultipart('related')
            msg['Subject'] = f"{'✅ ' if success else '❌ '}{title}"
            msg['From'] = self.email_sender
            msg['To'] = self.email_receiver
            
            # 创建HTML内容，转换换行符为HTML换行标签
            html_message = message.replace('\n', '<br>')
            status_text = "成功" if success else "失败"
            
            # 创建HTML内容
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .container {{ padding: 20px; }}
                    .header {{ font-size: 18px; font-weight: bold; color: {'green' if success else 'red'}; }}
                    .content {{ margin-top: 20px; }}
                    .image-container {{ margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">{'✅ ' if success else '❌ '}{title} ({status_text})</div>
                    <div class="content">
                        {html_message}
                    </div>
            """
            
            # 如果有截图，添加到HTML中
            image_count = 0
            
            if screenshot_path and os.path.exists(screenshot_path):
                try:
                    # 读取图片文件
                    with open(screenshot_path, 'rb') as img_file:
                        img_data = img_file.read()
                    
                    # 创建图片附件
                    image = MIMEImage(img_data)
                    image_id = f"image{image_count}"
                    image.add_header('Content-ID', f'<{image_id}>')
                    msg.attach(image)
                    
                    # 在HTML中引用图片
                    html_content += f"""
                    <div class="image-container">
                        <p>签到结果截图:</p>
                        <img src="cid:{image_id}" style="max-width:800px; border:1px solid #ddd;">
                    </div>
                    """
                    image_count += 1
                    logger.info(f"已添加截图到邮件: {screenshot_path}")
                except Exception as img_e:
                    logger.warning(f"添加截图到邮件时出错: {img_e}")
            
            # 添加额外的图片
            if additional_images:
                for img_path in additional_images:
                    if os.path.exists(img_path):
                        try:
                            # 读取图片文件
                            with open(img_path, 'rb') as img_file:
                                img_data = img_file.read()
                            
                            # 创建图片附件
                            image = MIMEImage(img_data)
                            image_id = f"image{image_count}"
                            image.add_header('Content-ID', f'<{image_id}>')
                            msg.attach(image)
                            
                            # 获取文件名
                            filename = Path(img_path).name
                            
                            # 在HTML中引用图片
                            html_content += f"""
                            <div class="image-container">
                                <p>附件图片 - {filename}:</p>
                                <img src="cid:{image_id}" style="max-width:800px; border:1px solid #ddd;">
                            </div>
                            """
                            image_count += 1
                            logger.info(f"已添加附加图片到邮件: {img_path}")
                        except Exception as img_e:
                            logger.warning(f"添加附加图片到邮件时出错: {img_e}")
            
            # 完成HTML内容
            html_content += """
                </div>
            </body>
            </html>
            """
            
            # 添加HTML内容到邮件
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # 连接到SMTP服务器并发送
            try:
                # 使用SSL/TLS连接
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.ehlo()
                server.starttls()  # 启用TLS加密
                server.ehlo()
                
                # 登录
                server.login(self.email_username, self.email_password)
                
                # 发送邮件
                server.send_message(msg)
                server.quit()
                
                logger.info(f"邮件发送成功: {title}")
                return True
                
            except Exception as smtp_e:
                logger.error(f"SMTP操作出错: {smtp_e}")
                logger.error(traceback.format_exc())
                
                # 尝试不使用TLS的方式
                try:
                    logger.info("尝试使用非TLS方式连接SMTP服务器...")
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                    server.login(self.email_sender, self.email_password)
                    server.send_message(msg)
                    server.quit()
                    
                    logger.info(f"非TLS方式邮件发送成功: {title}")
                    return True
                except Exception as plain_e:
                    logger.error(f"非TLS方式SMTP操作也出错: {plain_e}")
                    return False
                
        except Exception as e:
            logger.error(f"发送邮件通知时出错: {e}")
            logger.error(traceback.format_exc())
            return False 