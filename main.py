import requests
import smtplib
import time
import json
import logging
from email.mime.text import MIMEText
from pathlib import Path
import datetime
import base64
from Crypto.Cipher import AES as _AES
from typing import Optional

# ----------------- 基础配置 -----------------
CONFIG_FILE = "config.json"
STATE_FILE = "last_state.json"
LOG_FILE = "monitor.log"

# 统一初始化日志：支持控制台、文件或二者同时输出，可通过 config.json 配置覆盖


def setup_logging(cfg: Optional[dict] = None):
    """初始化日志系统

    支持配置项（在 config.json 顶层可添加 logging 字段）：
    {
      "logging": {
        "console_enabled": true,
        "file_enabled": true,
        "file": "monitor.log",
        "level": "INFO",
        "format": "%(asctime)s - %(levelname)s - %(message)s"
      }
    }
    若未提供配置，则默认开启控制台与文件双输出，日志文件为 monitor.log。
    """
    log_cfg = (cfg or {}).get("logging", {})

    console_enabled = log_cfg.get("console_enabled", True)
    file_enabled = log_cfg.get("file_enabled", True)
    log_file = log_cfg.get("file", LOG_FILE)
    level_str = str(log_cfg.get("level", "INFO")).upper()
    fmt = log_cfg.get("format", "%(asctime)s - %(levelname)s - %(message)s")

    level = getattr(logging, level_str, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # 清理已有 handler，避免重复添加
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(fmt)

    # 允许日志输出
    if console_enabled or file_enabled:
        logging.disable(logging.NOTSET)

    if console_enabled:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)
        root.addHandler(ch)

    if file_enabled:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(formatter)
        root.addHandler(fh)

    if not console_enabled and not file_enabled:
        # 完全禁用日志输出
        logging.disable(logging.CRITICAL)


# ----------------- 基类定义 -----------------
class CompanyMonitor:
    def __init__(self, config):
        self.company_name = config.get("name")
        self.position_id = config.get("position_id")
        self.cookie = config.get("cookie")
        self.request_body = config.get("request_body", {})
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        self.sessionHeader = config.get("header", {})
        self.session = requests.Session()

    def login(self):
        """需子类实现具体登录逻辑"""
        raise NotImplementedError

    def fetch_status(self):
        """需子类实现状态获取逻辑"""
        raise NotImplementedError

    def send_email(self, new_status, email_config):
        """发送邮件通知"""
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
        """主检查流程"""
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
        """读取上次状态"""
        if not Path(STATE_FILE).exists():
            return None
        with open(STATE_FILE, "r") as f:
            states = json.load(f)
            return states.get(self.company_name, None)

    def save_current_state(self, status):
        """保存当前状态"""
        states = {}
        if Path(STATE_FILE).exists():
            with open(STATE_FILE, "r") as f:
                states = json.load(f)
        states[self.company_name] = status
        with open(STATE_FILE, "w") as f:
            json.dump(states, f)


# ----------------- 具体公司实现示例 -----------------


class NeteaseLeihuoMonitor(CompanyMonitor):
    def login(self):
        """维持原有Cookie登录方式，请替换为有效SESSION"""
        self.session.cookies.update({"SESSION": self.cookie})
        return True  # 假设Cookie有效

    def fetch_status(self):
        """解析新版接口数据结构"""
        try:
            # 添加时间戳参数防止缓存
            timestamp = int(time.time() * 1000)
            api_url = (
                f"https://campus.163.com/api/campuspc/apply/find?timeStamp={timestamp}"
            )

            response = self.session.get(api_url, headers=self.headers)
            response.raise_for_status()

            data = response.json()

            if data["code"] != 200 or not data.get("data"):
                logging.error(f"接口响应异常: {data.get('msg')}")
                return None

            # 获取所有有效申请记录
            valid_records = [
                item for item in data["data"]["leihuoList"] if item["invalidFlag"] == 0
            ]

            if not valid_records:
                logging.warning("没有有效的投递记录")
                return "无有效投递"

            # 优先匹配配置的岗位ID
            if self.position_id:
                target_record = next(
                    (item for item in valid_records if item["id"] == self.position_id),
                    None,
                )
                if not target_record:
                    logging.warning(f"未找到ID为{self.target_position_id}的岗位")
                    return None
            else:
                # 未配置ID时取第一个有效记录
                target_record = valid_records[0]

            # 组合关键信息
            status_info = (
                f"{target_record['applyPosition']} - "
                f"{target_record['applyStatusValue']} "
                f"({target_record['projectName']})"
            )

            return status_info

        except Exception as e:
            logging.error(f"状态解析失败: {str(e)}")
            return None


class MiHoYoMonitor(CompanyMonitor):
    def login(self):
        self.session.headers.update(self.sessionHeader)
        return True  # 假设Cookie有效

    def fetch_status(self):
        try:
            api_url = "https://ats.openout.mihoyo.com/ats-portal/v1/apply_job/list"
            request_body = {"pageNo": 1, "pageSize": 10}

            response = self.session.post(
                api_url, json=request_body, headers=self.headers
            )
            response.raise_for_status()

            data = response.json()

            if data["code"] != 0 or not data.get("data"):
                logging.error(f"接口响应异常: {data.get('message')}")
                return None

            # 获取所有有效申请记录
            valid_records = [item for item in data["data"]["list"]]

            if not valid_records:
                logging.warning("没有有效的投递记录")
                return "无有效投递"

            # 优先匹配配置的岗位ID
            if self.position_id:
                target_record = next(
                    (item for item in valid_records if item["id"] == self.position_id),
                    None,
                )
                if not target_record:
                    logging.warning(f"未找到ID为{self.target_position_id}的岗位")
                    return None
            else:
                # 未配置ID时取第一个有效记录
                target_record = valid_records[0]

            # 组合关键信息
            status_info = (
                f"{target_record['jobTitle']} - " f"{target_record['status']} "
            )

            return status_info

        except Exception as e:
            logging.error(f"状态解析失败: {str(e)}")
            return None


class NeteaseHuyuMonitor(CompanyMonitor):
    def __init__(self, config):
        super().__init__(config)

        self.h_map = {
            "I0010001": "hr\u4e00\u9762",
            "I0010002": "hr\u4e8c\u9762",
            "I0010003": "hr\u4e09\u9762",
            "I0020001": "\u4e13\u4e1a\u4e00\u9762",
            "I0020002": "\u4e13\u4e1a\u4e8c\u9762",
            "I0020003": "\u4e13\u4e1a\u4e09\u9762",
            "I0030001": "\u8ffd\u52a0\u4e00\u9762",
            "I0030002": "\u8ffd\u52a0\u4e8c\u9762",
            "I0030003": "\u8ffd\u52a0\u4e09\u9762",
        }

    def login(self):
        self.session.cookies.update(
            {
                "SESSION": self.cookie,
            }
        )
        return True  # 假设Cookie有效

    def fetch_status(self):
        try:
            api_url = "https://game.campus.163.com/api/recruitment/campus/deliveryRecord/currentDeliveryRecord"

            response = self.session.get(api_url, headers=self.headers)
            response.raise_for_status()

            data = response.json()

            if data["status"] != 1 or not data.get("data"):
                logging.error(f"接口响应异常: {data.get('message')}")
                return None

            # 获取所有有效申请记录
            valid_records = [item for item in data["data"]]

            if not valid_records:
                logging.warning("没有有效的投递记录")
                return "无有效投递"

            # 优先匹配配置的岗位ID
            if self.position_id:
                target_record = next(
                    (item for item in valid_records if item["id"] == self.position_id),
                    None,
                )
                if not target_record:
                    logging.warning(f"未找到ID为{self.target_position_id}的岗位")
                    return None
            else:
                # 未配置ID时取第一个有效记录
                target_record = valid_records[0]

            # TODO : 待补充状态
            status = "未知"
            if target_record["curProcessNode"].startswith("S00"):
                status = "筛选"
            elif target_record["curProcessNode"].startswith("T00"):
                status = "笔试"
            elif target_record["curProcessNode"].startswith("I00"):
                status = self.h_map.get(target_record["curProcessNode"])

            # 组合关键信息
            status_info = (
                f"{target_record['positionName']} - "
                f"{status} "
                f"({target_record['projectName']})"
            )

            return status_info

        except Exception as e:
            logging.error(f"状态解析失败: {str(e)}")
            return None


def aes_decrypt(content: str, key=None, IV=None):
    cipher = _AES.new(key, _AES.MODE_CBC, IV)
    content = base64.b64decode(content)
    return (cipher.decrypt(content).decode("utf-8")).replace("\n", "")


class MokaHRMonitor(CompanyMonitor):
    def login(self):
        """维持原有Cookie登录方式，请替换为有效SESSION"""
        self.session.headers.update(
            {
                "Cookie": self.cookie,
            }
        )
        return True  # 假设Cookie有效

    def fetch_status(self):
        """解析新版接口数据结构"""
        try:
            api_url = "https://app.mokahr.com/api/outer/ats-apply/personal-center/applications"
            response = self.session.post(
                api_url, json=self.request_body, headers=self.headers
            )
            response.raise_for_status()

            data = response.json()

            base64Data = data["data"]
            necromancer = data["necromancer"]

            AES_KEY = necromancer.encode("utf-8")
            AES_IV = "de7c21ed8d6f50fe".encode("utf-8")

            dec_data = aes_decrypt(base64Data, AES_KEY, AES_IV)

            data_json = json.loads(dec_data)

            if data_json["code"] != 0 or not data_json.get("data"):
                logging.error(f"接口响应异常: {data_json.get('message')}")
                return None

            # 获取所有有效申请记录
            campusApplyList = [
                item
                for item in data_json["data"]["campusApplyList"]
                if item["id"] == self.request_body["orgId"]
            ]

            if not campusApplyList:
                logging.warning("没有有效的投递记录")
                return "无有效投递"

            valid_records = [
                item
                for item in campusApplyList[0]["candidateApps"][0]["projectApps"][0][
                    "apps"
                ]
            ]

            if not valid_records:
                logging.warning("没有有效的投递记录")
                return "无有效投递"

            # 优先匹配配置的岗位ID
            if self.position_id:
                target_record = next(
                    (
                        item
                        for item in valid_records
                        if item["appId"] == self.position_id
                    ),
                    None,
                )
                if not target_record:
                    logging.warning(f"未找到ID为{self.target_position_id}的岗位")
                    return None
            else:
                # 未配置ID时取第一个有效记录
                target_record = valid_records[0]

            # 组合关键信息
            status_info = f"{target_record['orgName']} - {target_record['jobTitle']} - {target_record['stage']}"

            return status_info

        except Exception as e:
            logging.error(f"状态解析失败: {str(e)}")
            return None


# ----------------- 主程序 -----------------
def main():

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    # 初始化日志（支持 console/file/both）
    setup_logging(config)

    # 初始化监控器
    monitors = []
    for company in config["companies"]:
        if company["name"] == "网易雷火":
            monitors.append(NeteaseLeihuoMonitor(company))
        elif company["name"] == "米哈游":
            monitors.append(MiHoYoMonitor(company))
        elif company["name"] == "网易互娱":
            monitors.append(NeteaseHuyuMonitor(company))
        elif company["name"] == "MokaHR":
            monitors.append(MokaHRMonitor(company))
        # 添加其他公司...

    WORK_HOURS = config["WORK_HOURS"]
    # 启动监控循环
    while True:
        now = datetime.datetime.now()
        current_hour = now.hour

        # 判断是否在工作时间段内
        if WORK_HOURS["start_hour"] <= current_hour < WORK_HOURS["end_hour"]:
            logging.info(f"=== 开始本轮检查 {now.strftime('%Y-%m-%d %H:%M')} ===")

            # 执行所有监控器检查
            for monitor in monitors:
                if monitor.login():
                    monitor.check_update(config["email"])
                else:
                    logging.warning(f"{monitor.company_name} 登录失败")

            # 计算下一轮检查时间（1小时后或工作时段结束）
            next_check = now + datetime.timedelta(hours=1)
            if next_check.hour >= WORK_HOURS["end_hour"]:
                # 如果下一轮超出工作时间，直接休眠到次日
                sleep_seconds = (
                    datetime.datetime.combine(
                        now.date() + datetime.timedelta(days=1),
                        datetime.time(WORK_HOURS["start_hour"]),
                    )
                    - now
                ).total_seconds()
            else:
                # 否则正常间隔1小时
                sleep_seconds = config["sleep_seconds"]

            logging.info(
                f"本轮检查完成，下次检查时间: {next_check.strftime('%Y-%m-%d %H:%M')}"
            )
            time.sleep(sleep_seconds)

        else:
            # 非工作时间计算休眠到次日开始时间
            if current_hour >= WORK_HOURS["end_hour"]:
                next_day = now + datetime.timedelta(days=1)
                next_check_time = datetime.datetime(
                    next_day.year,
                    next_day.month,
                    next_day.day,
                    WORK_HOURS["start_hour"],
                )
            else:
                next_check_time = datetime.datetime(
                    now.year, now.month, now.day, WORK_HOURS["start_hour"]
                )

            sleep_seconds = (next_check_time - now).total_seconds()
            logging.info(
                f"非工作时间，休眠至 {next_check_time.strftime('%Y-%m-%d %H:%M')}"
            )
            time.sleep(sleep_seconds)


if __name__ == "__main__":
    print("Starting monitor...")
    main()
