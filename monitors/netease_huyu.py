import logging
from monitors.base import CompanyMonitor
from monitors.registry import register_monitor


@register_monitor("netease_huyu")
class NeteaseHuyuMonitor(CompanyMonitor):
    def __init__(self, config):
        super().__init__(config)
        # 面试阶段映射，允许通过 extra.h_map 覆盖
        default_map = {
            "I0010001": "hr一面",
            "I0010002": "hr二面",
            "I0010003": "hr三面",
            "I0020001": "专业一面",
            "I0020002": "专业二面",
            "I0020003": "专业三面",
            "I0030001": "追加一面",
            "I0030002": "追加二面",
            "I0030003": "追加三面",
        }
        self.h_map = {**default_map, **self.extra.get("h_map", {})}

    def login(self):
        # 基类已应用鉴权，这里通常无需额外处理
        return True

    def fetch_status(self):
        try:
            api_url = "https://game.campus.163.com/api/recruitment/campus/deliveryRecord/currentDeliveryRecord"

            response = self.session.get(api_url, headers=self.headers)
            response.raise_for_status()

            data = response.json()

            if data["status"] != 1 or not data.get("data"):
                logging.error(f"接口响应异常: {data.get('message')}")
                return None

            valid_records = [item for item in data["data"]]

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

            status = "未知"
            if target_record["curProcessNode"].startswith("S00"):
                status = "筛选"
            elif target_record["curProcessNode"].startswith("T00"):
                status = "笔试"
            elif target_record["curProcessNode"].startswith("I00"):
                status = self.h_map.get(target_record["curProcessNode"]) or status

            status_info = (
                f"{target_record['positionName']} - "
                f"{status} "
                f"({target_record['projectName']})"
            )

            return status_info

        except Exception as e:
            logging.error(f"状态解析失败: {str(e)}")
            return None
