"""
中国法定节假日数据抓取模块

数据来源 (优先级):
  1. chinese-calendar Python 包 (本地数据，最可靠)
  2. 备用网络数据源 (GitHub holiday-cn JSON)

生成包含以下内容的日历:
  - 法定节假日 (春节、清明、劳动节、端午、中秋、国庆、元旦)
  - 调休上班日期
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple

from src.ics_generator import ICSEvent, ICSGenerator, generate_event_uid

logger = logging.getLogger(__name__)

# 假期类别
CATEGORY_HOLIDAY = "节假日"
CATEGORY_WORKDAY = "调休上班"


def _classify_holiday_by_date(d: date) -> str:
    """根据日期推断节日名称"""
    m, day = d.month, d.day

    # 元旦: 1月1-3日左右
    if m == 1 and day <= 3:
        return "元旦"
    # 春节: 1月下旬-2月中旬 (农历新年)
    if m in (1, 2):
        return "春节"
    # 清明节: 4月4-6日左右
    if m == 4 and 1 <= day <= 10:
        return "清明节"
    # 劳动节: 5月1-5日
    if m == 5 and 1 <= day <= 7:
        return "劳动节"
    # 端午节: 5月下旬-6月 (农历五月初五)
    if m in (5, 6):
        return "端午节"
    # 中秋节: 9月中旬-10月初 (农历八月十五)
    if m == 9 and 7 <= day <= 30:
        return "中秋节"
    # 国庆节: 10月1-8日
    if m == 10 and 1 <= day <= 8:
        return "国庆节"
    if m == 10 and 9 <= day <= 15:
        return "国庆节"  # 可能有调整

    return "节假日"


def _classify_workday_by_date(d: date) -> str:
    """根据日期推断调休关联的节日"""
    m, day = d.month, d.day
    if m in (1, 2):
        return "春节"
    elif m == 4:
        return "清明节"
    elif m == 5:
        return "劳动节"
    elif m in (5, 6):
        return "端午节"
    elif m in (9, 10):
        return "国庆节" if day <= 15 else "中秋节"
    return "节假日"


class HolidaysFetcher:
    """中国法定节假日数据获取器"""

    def __init__(self):
        self._holidays: List[Dict] = []
        self._workdays: List[Dict] = []

    def fetch(self) -> Tuple[List[Dict], List[Dict]]:
        """获取节假日数据"""
        # ── 方案1: chinese-calendar 包 ──
        try:
            holidays, workdays = self._fetch_from_chinese_calendar()
            if holidays or workdays:
                self._holidays = holidays
                self._workdays = workdays
                return (holidays, workdays)
        except Exception as e:
            logger.warning(f"chinese-calendar 获取失败: {e}，尝试备用方案")

        # ── 方案2: 网络数据源 ──
        try:
            holidays, workdays = self._fetch_from_web()
            if holidays or workdays:
                self._holidays = holidays
                self._workdays = workdays
                return (holidays, workdays)
        except Exception as e:
            logger.error(f"备用方案也失败: {e}")

        return ([], [])

    def _fetch_from_chinese_calendar(self) -> Tuple[List[Dict], List[Dict]]:
        """通过 chinese-calendar 包获取假期数据"""
        from chinese_calendar import get_holidays, get_workdays

        today = date.today()
        years_to_fetch = [today.year, today.year + 1, today.year + 2]

        all_holidays: List[Dict] = []
        all_workdays: List[Dict] = []

        for year in years_to_fetch:
            try:
                year_start = date(year, 1, 1)
                year_end = date(year, 12, 31)

                holiday_dates = get_holidays(year_start, year_end)
                workday_dates = get_workdays(year_start, year_end)

                for d in holiday_dates:
                    if not isinstance(d, date):
                        continue
                    name = _classify_holiday_by_date(d)
                    all_holidays.append({
                        "date": d,
                        "name": name,
                    })

                for d in workday_dates:
                    if not isinstance(d, date):
                        continue
                    name = _classify_workday_by_date(d)
                    all_workdays.append({
                        "date": d,
                        "name": f"{name}调休上班",
                    })

            except NotImplementedError:
                logger.debug(f"{year} 年数据尚未发布")
                continue
            except Exception as e:
                logger.warning(f"获取 {year} 年数据失败: {e}")
                continue

        # 去重
        all_holidays = self._deduplicate(all_holidays, "date")
        all_workdays = self._deduplicate(all_workdays, "date")

        logger.info(
            f"chinese-calendar: {len(all_holidays)} 个节假日, "
            f"{len(all_workdays)} 个调休日"
        )
        return (all_holidays, all_workdays)

    def _deduplicate(self, items: List[Dict], key: str) -> List[Dict]:
        """按 key 去重"""
        seen = set()
        result = []
        for item in items:
            val = item[key]
            if val not in seen:
                seen.add(val)
                result.append(item)
        return result

    def _fetch_from_web(self) -> Tuple[List[Dict], List[Dict]]:
        """备用方案：网络 JSON 数据源"""
        import requests

        today = date.today()
        years = [today.year, today.year + 1, today.year + 2]

        all_holidays: List[Dict] = []
        all_workdays: List[Dict] = []

        for year in years:
            urls = [
                f"https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/{year}.json",
                f"https://fastly.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{year}.json",
            ]
            for url in urls:
                try:
                    resp = requests.get(url, timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        h, w = self._parse_json_holidays(data)
                        all_holidays.extend(h)
                        all_workdays.extend(w)
                        break
                except Exception:
                    continue

        all_holidays = self._deduplicate(all_holidays, "date")
        all_workdays = self._deduplicate(all_workdays, "date")

        logger.info(
            f"网络数据源: {len(all_holidays)} 个节假日, "
            f"{len(all_workdays)} 个调休日"
        )
        return (all_holidays, all_workdays)

    def _parse_json_holidays(self, data: dict) -> Tuple[List[Dict], List[Dict]]:
        """解析 JSON 格式的节假日数据"""
        holidays = []
        workdays = []
        days = data.get("days", [])

        for item in days:
            d_str = item.get("date", "")
            is_off = item.get("isOffDay", False)
            name = item.get("name", "")

            try:
                d = datetime.strptime(d_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            if is_off:
                holidays.append({
                    "date": d,
                    "name": _classify_holiday_by_date(d),
                })
            elif name or not is_off:
                # 非休息日但被记录 → 可能是调休上班
                related = _classify_workday_by_date(d)
                workdays.append({
                    "date": d,
                    "name": f"{related}调休上班",
                })

        return (holidays, workdays)

    def to_ics_events(self) -> List[ICSEvent]:
        """将节假日数据转换为 ICS 事件列表"""
        events = []

        for h in self._holidays:
            d = h["date"]
            start_dt = datetime(d.year, d.month, d.day, 0, 0, 0)
            end_dt = datetime(d.year, d.month, d.day, 23, 59, 59)
            name = h["name"]
            uid = generate_event_uid("holidays", f"holiday-{d.isoformat()}", start_dt)

            event = ICSEvent(
                summary=f"🎉 {name}",
                start=start_dt,
                end=end_dt,
                description=(
                    f"{name} (法定节假日)\n"
                    f"日期: {d.strftime('%Y年%m月%d日')}\n"
                    f"星期{d.strftime('%w')}"
                ),
                uid=uid,
                categories=[CATEGORY_HOLIDAY, name],
                is_all_day=True,
            )
            events.append(event)

        for w in self._workdays:
            d = w["date"]
            start_dt = datetime(d.year, d.month, d.day, 0, 0, 0)
            end_dt = datetime(d.year, d.month, d.day, 23, 59, 59)
            name = w["name"]
            weekday_names = ["日", "一", "二", "三", "四", "五", "六"]
            wd = weekday_names[int(d.strftime("%w"))]
            uid = generate_event_uid("holidays", f"workday-{d.isoformat()}", start_dt)

            event = ICSEvent(
                summary=f"💼 {name}",
                start=start_dt,
                end=end_dt,
                description=(
                    f"{name}\n"
                    f"日期: {d.strftime('%Y年%m月%d日')} (周{wd})\n"
                    f"请正常上班"
                ),
                uid=uid,
                categories=[CATEGORY_WORKDAY],
                is_all_day=True,
            )
            events.append(event)

        return events


def build_holidays_ics(output_path: str) -> str:
    """生成节假日 ICS 文件"""
    logger.info("开始获取中国法定节假日数据...")
    fetcher = HolidaysFetcher()
    holidays, workdays = fetcher.fetch()

    logger.info(f"最终: {len(holidays)} 个节假日, {len(workdays)} 个调休工作日")

    events = fetcher.to_ics_events()
    logger.info(f"生成 {len(events)} 个日历事件")

    generator = ICSGenerator("holidays")
    generator.add_events(events)
    generator.save(output_path)

    logger.info(f"节假日 ICS 文件已保存: {output_path}")
    return output_path
