import logging
from monitors.base import CompanyMonitor
from monitors.registry import register_monitor


@register_monitor("mihoyo")
class MiHoYoMonitor(CompanyMonitor):
    def login(self):
        self.session.headers.update(self.sessionHeader)
        return True

    def fetch_status(self):
        try:
            api_url = "https://ats.openout.mihoyo.com/ats-portal/v1/apply_job/list"
            request_body = {"pageNo": 1, "pageSize": 10}

            response = self.session.post(api_url, json=request_body, headers=self.headers)
            response.raise_for_status()

            data = response.json()

            if data["code"] != 0 or not data.get("data"):
                logging.error(f"接口响应异常: {data.get('message')}")
                return None

            valid_records = [item for item in data["data"]["list"]]

            if not valid_records:
                logging.warning("没有有效的投递记录")
                return "无有效投递"

            if self.position_id:
                target_record = next(
                    (item for item in valid_records if item["id"] == self.position_id),
                    None,
                )
                if not target_record:
                    logging.warning(f"未找到ID为{getattr(self, 'target_position_id', self.position_id)}的岗位")
                    return None
            else:
                target_record = valid_records[0]

            status_info = f"{target_record['jobTitle']} - {target_record['status']} "

            return status_info

        except Exception as e:
            logging.error(f"状态解析失败: {str(e)}")
            return None
