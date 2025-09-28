import time
import os
import json
import logging
import datetime
from pathlib import Path
from typing import Optional
from monitors.registry import get_monitor_class
import importlib
import pkgutil
import monitors as monitors_pkg

# ----------------- 基础配置 -----------------
CONFIG_FILE = os.environ.get("CONFIG_PATH", "config.json")
LOG_FILE = os.environ.get("LOG_PATH", "monitor.log")

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

    effective_console_enabled = console_enabled
    file_handler = None
    file_setup_error = None

    if file_enabled:
        try:
            log_path = Path(log_file)
            if log_path.exists() and log_path.is_dir():
                raise IsADirectoryError(
                    f"日志路径 {log_file} 指向目录，无法创建日志文件"
                )
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        except (OSError, PermissionError) as exc:
            file_handler = None
            file_setup_error = exc
            file_enabled = False
            if not effective_console_enabled:
                effective_console_enabled = True

    if effective_console_enabled:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)
        root.addHandler(ch)

    if file_handler is not None:
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    if file_setup_error:
        root.warning(
            "日志文件无法写入（%s），已自动退回到控制台输出。请检查路径或目录权限。",
            file_setup_error,
        )

    if not effective_console_enabled and file_handler is None:
        # 完全禁用日志输出
        logging.disable(logging.CRITICAL)


# ----------------- 主程序 -----------------
def main():

    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"未找到配置文件: {CONFIG_FILE}。请检查路径或通过环境变量 CONFIG_PATH 指定。"
        )

    with open(CONFIG_FILE, encoding="utf-8") as f:
        config = json.load(f)

    # 初始化日志（支持 console/file/both）
    setup_logging(config)

    # 动态加载 monitors 下的所有模块，使其通过装饰器完成注册
    for _finder, modname, _ispkg in pkgutil.iter_modules(monitors_pkg.__path__):
        if modname in {"__init__", "registry", "base"}:
            continue
        importlib.import_module(f"monitors.{modname}")

    # 初始化监控器（支持 provider/名称映射）
    name_alias = {
        "网易雷火": "netease_leihuo",
        "米哈游": "mihoyo",
        "网易互娱": "netease_huyu",
        "MokaHR": "mokahr",
    }

    monitors = []
    for company in config["companies"]:
        provider = company.get("provider") or name_alias.get(company.get("name"))
        cls = get_monitor_class(provider) if provider else None
        if cls is None:
            logging.warning(
                f"未识别的 provider/name: {company.get('provider') or company.get('name')}，跳过该公司"
            )
            continue
        monitors.append(cls(company))

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
