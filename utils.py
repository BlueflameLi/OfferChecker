import logging
import smtplib
from email.mime.text import MIMEText


def send_email_simple(subject: str, body: str, email_config: dict) -> bool:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = email_config["sender"]
    msg["To"] = email_config["receiver"]

    try:
        with smtplib.SMTP_SSL(email_config["smtp_server"], 465) as server:
            server.login(email_config["sender"], email_config["password"])
            server.sendmail(
                email_config["sender"], [email_config["receiver"]], msg.as_string()
            )
            server.quit()
        logging.info("邮件发送成功")
        return True
    except Exception as e:
        logging.error(f"邮件发送失败: {str(e)}")
        return False
