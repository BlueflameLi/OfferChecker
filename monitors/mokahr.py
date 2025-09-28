import json
import base64
import logging
from Crypto.Cipher import AES as _AES
from monitors.base import CompanyMonitor
from monitors.registry import register_monitor


def _aes_decrypt(content: str, key=None, IV=None):
    cipher = _AES.new(key, _AES.MODE_CBC, IV)
    content = base64.b64decode(content)
    return (cipher.decrypt(content).decode("utf-8")).replace("\n", "")


@register_monitor("mokahr")
class MokaHRMonitor(CompanyMonitor):
    def login(self):
        # 基类已应用鉴权，这里通常无需额外处理
        return True

    def fetch_status(self):
        try:
            api_url = "https://app.mokahr.com/api/outer/ats-apply/personal-center/applications"
            default_body = {}
            body_override = self.extra.get("request_body", {})
            request_body = {**default_body, **body_override}
            response = self.session.post(api_url, json=request_body, headers=self.headers)
            response.raise_for_status()

            data = response.json()

            base64Data = data["data"]
            necromancer = data["necromancer"]

            AES_KEY = necromancer.encode("utf-8")
            AES_IV = "de7c21ed8d6f50fe".encode("utf-8")

            dec_data = _aes_decrypt(base64Data, AES_KEY, AES_IV)

            data_json = json.loads(dec_data)

            if data_json["code"] != 0 or not data_json.get("data"):
                logging.error(f"接口响应异常: {data_json.get('message')}")
                return None

            campusApplyList = [
                item
                for item in data_json["data"]["campusApplyList"]
                if item["id"] == request_body.get("orgId")
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
                    logging.warning(f"未找到ID为{getattr(self, 'target_position_id', self.position_id)}的岗位")
                    return None
            else:
                target_record = valid_records[0]

            status_info = f"{target_record['orgName']} - {target_record['jobTitle']} - {target_record['stage']}"

            return status_info

        except Exception as e:
            logging.error(f"状态解析失败: {str(e)}")
            return None
