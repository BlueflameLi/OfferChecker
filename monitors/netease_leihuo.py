import time
import logging
from monitors.base import CompanyMonitor
from monitors.registry import register_monitor


@register_monitor("netease_leihuo")
class NeteaseLeihuoMonitor(CompanyMonitor):
    def login(self):
        self.session.cookies.update({"SESSION": self.cookie})
        return True

    def fetch_status(self):
        try:
            timestamp = int(time.time() * 1000)
            api_url = f"https://campus.163.com/api/campuspc/apply/find?timeStamp={timestamp}"
            response = self.session.get(api_url, headers=self.headers)
            response.raise_for_status()

            data = response.json()

            if data["code"] != 200 or not data.get("data"):
                logging.error(f"接口响应异常: {data.get('msg')}")
                return None

            valid_records = [
                item for item in data["data"]["leihuoList"] if item["invalidFlag"] == 0
            ]

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

            status_info = (
                f"{target_record['applyPosition']} - "
                f"{target_record['applyStatusValue']} "
                f"({target_record['projectName']})"
            )

            return status_info

        except Exception as e:
            logging.error(f"状态解析失败: {str(e)}")
            return None
