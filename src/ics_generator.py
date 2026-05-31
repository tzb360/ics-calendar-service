"""
ICS Calendar Generator - Core Module
生成符合 RFC 5545 标准的 iCalendar 文件
支持 Apple Calendar、Google Calendar、Outlook、Thunderbird
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
import hashlib
import uuid


# ── 常量 ────────────────────────────────────────────
TZID = "Asia/Shanghai"
X_WR_CALNAME_MAP = {
    "holidays": "中国法定节假日",
    "worldcup": "FIFA 世界杯赛程",
    "cs2": "CS2 Major 赛事",
    "all": "综合日历订阅",
}
X_WR_CALDESC_MAP = {
    "holidays": "国务院办公厅发布的法定节假日、调休上班安排",
    "worldcup": "FIFA 世界杯小组赛、淘汰赛完整赛程",
    "cs2": "CS2 Major 及顶级赛事赛程 (IEM/BLAST/ESL)",
    "all": "聚合日历：中国节假日 + 世界杯 + CS2 赛事",
}


def _escape_ics_text(text: str) -> str:
    """转义 ICS 文本中的特殊字符"""
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    text = text.replace("\n", "\\n")
    return text


def _dtstamp() -> str:
    """生成当前 UTC 时间戳 (DTSTAMP)"""
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _to_ical_datetime(dt: datetime) -> str:
    """
    将 datetime 转换为 iCalendar 本地时间格式 (带 TZID)
    """
    return dt.strftime("%Y%m%dT%H%M%S")


def _to_ical_date(d: date) -> str:
    """
    将 date 转换为 iCalendar 日期格式 (无时间)
    """
    return d.strftime("%Y%m%d")


def generate_event_uid(source: str, event_id: str, dt: datetime) -> str:
    """
    生成唯一的 UID
    基于 source + event_id + date 生成可复现的 UID
    """
    raw = f"{source}-{event_id}-{dt.strftime('%Y%m%d')}"
    hash_hex = hashlib.md5(raw.encode()).hexdigest()
    return f"{hash_hex}@{source}.ics-calendar"


def build_vtimezone() -> str:
    """
    构建 Asia/Shanghai VTIMEZONE 组件
    包含标准时间和夏令时边界定义 (中国历史上使用过夏令时，
    这里提供标准定义以确保兼容性)
    """
    return """BEGIN:VTIMEZONE
TZID:Asia/Shanghai
X-LIC-LOCATION:Asia/Shanghai
BEGIN:STANDARD
TZOFFSETFROM:+0800
TZOFFSETTO:+0800
TZNAME:CST
DTSTART:19700101T000000
END:STANDARD
END:VTIMEZONE"""


class ICSEvent:
    """单个日历事件"""

    def __init__(
        self,
        summary: str,
        start: datetime,
        end: datetime,
        *,
        description: str = "",
        location: str = "",
        uid: Optional[str] = None,
        categories: Optional[List[str]] = None,
        is_all_day: bool = False,
    ):
        self.summary = summary
        self.description = description
        self.location = location
        self.start = start
        self.end = end
        self.is_all_day = is_all_day

        if uid is None:
            uid = str(uuid.uuid4())
        # Replace @ for ICS compatibility
        self.uid = uid.replace("@", "-at-")

        self.categories = categories or []
        self.last_modified = datetime.utcnow()

    def to_ical(self) -> str:
        """将事件序列化为 iCalendar VEVENT 格式"""
        lines = ["BEGIN:VEVENT"]

        lines.append(f"UID:{self.uid}")
        lines.append(f"DTSTAMP:{_dtstamp()}")
        lines.append(f"LAST-MODIFIED:{self.last_modified.strftime('%Y%m%dT%H%M%SZ')}")
        lines.append(f"SUMMARY:{_escape_ics_text(self.summary)}")

        if self.description:
            lines.append(f"DESCRIPTION:{_escape_ics_text(self.description)}")

        if self.location:
            lines.append(f"LOCATION:{_escape_ics_text(self.location)}")

        if self.categories:
            cats = ",".join(_escape_ics_text(c) for c in self.categories)
            lines.append(f"CATEGORIES:{cats}")

        # DTSTART / DTEND
        if self.is_all_day:
            start_d = self.start.date() if isinstance(self.start, datetime) else self.start
            end_d = (self.end + timedelta(days=1)).date() if isinstance(self.end, (datetime, date)) else (self.end + timedelta(days=1))
            lines.append(f"DTSTART;VALUE=DATE:{_to_ical_date(start_d)}")
            lines.append(f"DTEND;VALUE=DATE:{_to_ical_date(end_d)}")
        else:
            lines.append(f"DTSTART;TZID={TZID}:{_to_ical_datetime(self.start)}")
            lines.append(f"DTEND;TZID={TZID}:{_to_ical_datetime(self.end)}")

        # TRANSP: OPAQUE = 占用时间 (默认), TRANSPARENT = 空闲
        lines.append("TRANSP:OPAQUE")

        lines.append("END:VEVENT")
        return "\r\n".join(lines)


class ICSGenerator:
    """iCalendar 文件生成器"""

    def __init__(self, cal_type: str):
        self.cal_type = cal_type
        self.events: List[ICSEvent] = []
        self.prodid = "-//ICS Calendar Service//CN"

    def add_event(self, event: ICSEvent):
        self.events.append(event)

    def add_events(self, events: List[ICSEvent]):
        self.events.extend(events)

    def generate(self) -> str:
        """生成完整的 iCalendar 文件内容"""
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            f"PRODID:{self.prodid}",
            f"CALSCALE:GREGORIAN",
            f"METHOD:PUBLISH",
            f"X-WR-CALNAME:{_escape_ics_text(X_WR_CALNAME_MAP.get(self.cal_type, 'Calendar'))}",
            f"X-WR-CALDESC:{_escape_ics_text(X_WR_CALDESC_MAP.get(self.cal_type, ''))}",
            f"X-WR-TIMEZONE:{TZID}",
            # X-PUBLISHED-TTL 建议客户端刷新间隔 (小时)
            "X-PUBLISHED-TTL:PT1H",
            "",
            build_vtimezone(),
        ]

        for event in self.events:
            lines.append(event.to_ical())

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"

    def save(self, filepath: str) -> str:
        """保存 ICS 文件到指定路径，返回文件路径"""
        content = self.generate()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath


def merge_ics_files(filepaths: List[str], output_path: str) -> str:
    """
    合并多个 ICS 文件为一个聚合日历
    简单合并所有 VEVENT + 统一 VTIMEZONE
    """
    all_events: List[str] = []
    seen_uids: set = set()

    for fp in filepaths:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            continue

        # 提取所有 VEVENT 块
        import re
        for match in re.finditer(r"BEGIN:VEVENT\r?\n(.*?)\r?\nEND:VEVENT", content, re.DOTALL):
            event_block = match.group(0)
            # 提取 UID 去重
            uid_match = re.search(r"UID:(.+)", event_block)
            if uid_match:
                uid = uid_match.group(1).strip()
                if uid in seen_uids:
                    continue
                seen_uids.add(uid)
            all_events.append(event_block)

    # 构建聚合日历
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ICS Calendar Service//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_ics_text(X_WR_CALNAME_MAP['all'])}",
        f"X-WR-CALDESC:{_escape_ics_text(X_WR_CALDESC_MAP['all'])}",
        f"X-WR-TIMEZONE:{TZID}",
        "X-PUBLISHED-TTL:PT1H",
        "",
        build_vtimezone(),
    ]

    for event in all_events:
        lines.append(event)

    lines.append("END:VCALENDAR")
    content = "\r\n".join(lines) + "\r\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path
