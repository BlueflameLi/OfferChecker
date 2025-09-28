import logging
from monitors.base import CompanyMonitor
from monitors.registry import register_monitor


@register_monitor("netease_huyu")
class NeteaseHuyuMonitor(CompanyMonitor):
    def __init__(self, config):
        super().__init__(config)
        self.h_map = {
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

            # 基于节点与节点状态的判定（参考站点 JS 逻辑）
            node = target_record.get("curProcessNode", "")
            node_status = target_record.get("curProcessNodeStatus")  # 可能为 2/3 等

            status = "未知"

            # 优先处理失败/放弃/拒绝等终止类状态
            if node and node_status is not None:
                if node.startswith("S00") and node_status == 2:
                    status = "筛选未通过"
                elif node.startswith("E00"):
                    if node_status == 2:
                        status = "笔试未通过"
                    elif node_status == 3:
                        status = "已放弃笔试"
                elif node.startswith("I00"):
                    if node_status == 2:
                        status = "面试不通过"
                    elif node_status == 3:
                        status = "已放弃面试"
                elif node.startswith("T00"):
                    if node_status == 2:
                        status = "录用不通过"
                    elif node_status == 3:
                        status = "候选人已拒绝"
                elif node.startswith("O00") and node_status == 3:
                    status = "候选人已拒绝"

            # 若未命中终止类状态，则给出阶段性状态描述
            if status == "未知":
                if node.startswith("S00"):
                    status = "筛选"
                elif node.startswith("E00"):
                    status = "笔试"
                elif node.startswith("I00"):
                    status = self.h_map.get(node) or "面试"
                elif node.startswith("T00"):
                    status = "录用审核"
                elif node.startswith("O00"):
                    status = "入职"

            status_info = (
                f"{target_record['positionName']} - "
                f"{status} "
                f"({target_record['projectName']})"
            )

            return status_info

        except Exception as e:
            logging.error(f"状态解析失败: {str(e)}")
            return None
