import json
import logging
import os
from pathlib import Path
import requests
import smtplib
from email.mime.text import MIMEText

STATE_FILE = os.environ.get("STATE_FILE_PATH", "last_state.json")


class CompanyMonitor:
    def __init__(self, config):
        # 通用自定义配置字段，供各 Provider 按需读取，避免直接暴露完整 config
        self.extra = config.get("extra", {})
        self.company_name = config.get("name")
        self.position_id = config.get("position_id")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        self.session = requests.Session()
        # 顶层 headers 统一鉴权（包含 Cookie/Authorization 等）
        self.headers.update(config.get("headers", {}))

    def login(self):
        raise NotImplementedError

    def fetch_status(self):
        raise NotImplementedError

    def send_email(self, new_status, email_config):
        msg = MIMEText(f"{self.company_name}状态更新：{new_status}", "plain", "utf-8")
        msg["Subject"] = f"[校招状态] {self.company_name} 进度更新"
        msg["From"] = email_config["sender"]
        msg["To"] = email_config["receiver"]

        try:
            with smtplib.SMTP_SSL(email_config["smtp_server"], 465) as server:
                server.login(email_config["sender"], email_config["password"])
                server.sendmail(
                    email_config["sender"], [email_config["receiver"]], msg.as_string()
                )
                server.quit()
            logging.info(f"邮件发送成功 - {self.company_name}")
        except Exception as e:
            logging.error(f"邮件发送失败: {str(e)}")

    def check_update(self, email_config):
        try:
            current_status = self.fetch_status()
            last_status = self.load_last_state()
            logging.info(
                f"{self.company_name} 当前状态: {current_status}, 上次状态: {last_status}"
            )
            if current_status and current_status != last_status:
                self.send_email(current_status, email_config)
                self.save_current_state(current_status)
                return True
            return False
        except Exception as e:
            logging.error(f"检查失败: {str(e)}")
            return False

    def load_last_state(self):
        state_path = Path(STATE_FILE)
        if not state_path.exists():
            return None
        with state_path.open("r", encoding="utf-8") as f:
            states = json.load(f)
            return states.get(self.company_name, None)

    def save_current_state(self, status):
        state_path = Path(STATE_FILE)
        states = {}
        if state_path.exists():
            with state_path.open("r", encoding="utf-8") as f:
                states = json.load(f)
        states[self.company_name] = status
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with state_path.open("w", encoding="utf-8") as f:
            json.dump(states, f, ensure_ascii=False)

    # --- 内部方法 ---
