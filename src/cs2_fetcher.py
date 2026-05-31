"""
CS2 Major 赛事数据抓取模块

数据来源: HLTV.org (https://www.hltv.org)

抓取赛事:
  - Major (PGL/BLAST Major)
  - IEM Cologne
  - IEM Katowice
  - BLAST Premier
  - ESL Pro League

特性:
  - 自动同步对阵双方、开赛时间、BO3/BO5、阶段信息
  - 每小时检查更新
  - 如果 HLTV 不可用，使用缓存数据
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin

import pytz
import requests
from bs4 import BeautifulSoup

from src.ics_generator import ICSEvent, ICSGenerator, generate_event_uid

logger = logging.getLogger(__name__)

# ── 常量 ────────────────────────────────────────────
HLTV_BASE = "https://www.hltv.org"
CST = pytz.timezone("Asia/Shanghai")
MATCH_DURATION = timedelta(hours=3)
MATCH_DURATION_BO5 = timedelta(hours=4, minutes=30)
MATCH_DURATION_BO1 = timedelta(hours=1, minutes=30)

# 缓存文件路径
CACHE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output", ".cs2_cache.json"
)

# 目标赛事关键词
TARGET_EVENTS = [
    {"keywords": ["major"], "name": "CS2 Major", "priority": 1},
    {"keywords": ["iem cologne"], "name": "IEM Cologne", "priority": 2},
    {"keywords": ["iem katowice"], "name": "IEM Katowice", "priority": 3},
    {"keywords": ["blast premier"], "name": "BLAST Premier", "priority": 4},
    {"keywords": ["esl pro league"], "name": "ESL Pro League", "priority": 5},
    {"keywords": ["iem"], "name": "IEM", "priority": 6},
    {"keywords": ["blast"], "name": "BLAST", "priority": 7},
]

# 浏览器模拟 Headers
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


class HLTVFetcher:
    """HLTV CS2 赛事数据获取器"""

    def __init__(self):
        self.matches: List[Dict] = []
        self.session = requests.Session()
        self.session.headers.update(BROWSER_HEADERS)

    def fetch(self) -> List[Dict]:
        """获取 CS2 赛事数据"""
        # ── 尝试 HLTV ──
        try:
            self.matches = self._fetch_from_hltv()
            if self.matches:
                self._save_cache()
                return self.matches
        except Exception as e:
            logger.warning(f"HLTV 获取失败: {e}")

        # ── 加载缓存 ──
        cached = self._load_cache()
        if cached:
            logger.info(f"使用缓存数据: {len(cached)} 场比赛")
            self.matches = cached
            return cached

        logger.warning("无可用数据 (HLTV 不可用且无缓存)")
        return []

    def _fetch_from_hltv(self) -> List[Dict]:
        """从 HLTV 获取赛事数据"""
        # Step 1: 尝试获取 events 页面
        resp = self._fetch_with_retry(f"{HLTV_BASE}/events", max_retries=2)
        if resp is None:
            # 如果 events 页面被阻止，尝试直接搜索
            return self._search_events_directly()

        soup = BeautifulSoup(resp.text, "lxml")

        # 查找事件列表
        events = []
        seen_ids = set()

        # 尝试多种选择器
        for selector in [
            "a[href*='/events/']",
            ".event-col a[href*='/events/']",
            ".event-name-col a",
        ]:
            for link in soup.select(selector):
                href = link.get("href", "")
                event_id_match = re.search(r'/events/(\d+)/', href)
                if not event_id_match:
                    continue
                event_id = event_id_match.group(1)
                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)

                name = link.get_text(strip=True)
                if not name:
                    continue

                matched = self._match_target_event(name.lower())
                if matched:
                    events.append({
                        "id": event_id,
                        "name": matched["name"] or name,
                        "url": urljoin(HLTV_BASE, href),
                        "priority": matched["priority"],
                    })

        # 如果标准方法没找到，尝试搜索
        if not events:
            events = self._search_events_directly()

        # 按优先级排序
        events.sort(key=lambda x: x["priority"])

        logger.info(f"找到 {len(events)} 个目标赛事")

        # Step 2: 获取每个赛事的比赛数据
        all_matches = []
        for event in events[:8]:  # 限制最多 8 个赛事避免请求过多
            try:
                matches = self._get_event_matches(event)
                all_matches.extend(matches)
            except Exception as e:
                logger.warning(f"获取赛事 {event.get('name', '?')} 比赛失败: {e}")

        return all_matches

    def _fetch_with_retry(self, url: str, max_retries: int = 2):
        """带重试的 HTTP 请求"""
        for attempt in range(max_retries):
            try:
                # 每次重试前延迟
                if attempt > 0:
                    import time
                    time.sleep(2 * attempt)

                resp = self.session.get(url, timeout=20, allow_redirects=True)

                if resp.status_code == 403:
                    logger.debug(f"403 被拒绝 (尝试 {attempt + 1}/{max_retries})")
                    # 刷新 session 和 headers
                    self.session = requests.Session()
                    self.session.headers.update({
                        **BROWSER_HEADERS,
                        "Referer": "https://www.google.com/",
                    })
                    continue

                if resp.status_code == 200:
                    return resp

            except requests.RequestException as e:
                logger.debug(f"请求失败: {e}")
                continue

        return None

    def _search_events_directly(self) -> List[Dict]:
        """直接搜索目标事件 (备用方法)"""
        events = []

        # 尝试通过 HLTV 搜索结果 API
        for target in TARGET_EVENTS:
            kw = target["keywords"][0]
            try:
                # HLTV 搜索结果页面
                search_url = f"{HLTV_BASE}/search?query={kw}&type=event"
                resp = self._fetch_with_retry(search_url)
                if resp is None:
                    continue

                soup = BeautifulSoup(resp.text, "lxml")
                for link in soup.select("a[href*='/events/']"):
                    href = link.get("href", "")
                    eid_match = re.search(r'/events/(\d+)/', href)
                    if not eid_match:
                        continue
                    name = link.get_text(strip=True)
                    if name and name.lower().replace(" ", "") in kw.replace(" ", ""):
                        events.append({
                            "id": eid_match.group(1),
                            "name": target["name"],
                            "url": urljoin(HLTV_BASE, href),
                            "priority": target["priority"],
                        })
                        break
            except Exception:
                continue

        return events

    def _match_target_event(self, name_lower: str) -> Optional[Dict]:
        """检查事件是否为目标赛事"""
        for target in TARGET_EVENTS:
            if all(kw in name_lower for kw in target["keywords"]):
                return target
        return None

    def _get_event_matches(self, event: Dict) -> List[Dict]:
        """获取单个赛事的所有比赛"""
        event_id = event["id"]
        event_name = event["name"]

        # 使用 HLTV matches 页面
        url = f"{HLTV_BASE}/results?event={event_id}"
        resp = self._fetch_with_retry(url)
        if resp is None:
            return []
        soup = BeautifulSoup(resp.text, "lxml")

        matches = []

        # HLTV 比赛行 - 多种选择器
        for row in soup.select(
            "a[href*='/matches/'], "
            ".result-con .a-reset, "
            "tr.match, "
            ".match-box"
        ):
            try:
                match = self._parse_match(row, event_name, event_id)
                if match:
                    matches.append(match)
            except Exception:
                continue

        # 只保留最近的比赛（已完成和即将到来的）
        now = datetime.now(CST)
        recent_matches = []
        for m in matches:
            kickoff = m["kickoff"]
            # 保留未来比赛和最近 7 天内完成的比赛
            if kickoff > now - timedelta(days=7):
                recent_matches.append(m)

        return recent_matches

    def _parse_match(self, row, event_name: str, event_id: str) -> Optional[Dict]:
        """解析 HLTV 比赛行数据"""
        href = row.get("href", "")
        if not href or "/matches/" not in href:
            # 可能 nested <a>
            link = row.select_one("a[href*='/matches/']")
            if link:
                href = link.get("href", "")

        match_id_match = re.search(r'/matches/(\d+)/', href)
        if not match_id_match:
            return None

        match_id = match_id_match.group(1)

        # 提取队伍名称
        team1 = "TBD"
        team2 = "TBD"

        # HLTV 结构: team1, team2 类
        for selector, target in [
            (".team1", "team1"),
            (".team2", "team2"),
            ("[class*='team-1']", "team1"),
            ("[class*='team-2']", "team2"),
        ]:
            elem = row.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if target == "team1":
                    team1 = text
                else:
                    team2 = text

        # 提取 BO 类型
        row_text = row.get_text(" ", strip=True).lower()
        bo_type = "BO3"
        if "bo5" in row_text:
            bo_type = "BO5"
        elif "bo1" in row_text:
            bo_type = "BO1"

        # 提取阶段
        stage = ""
        stage_elem = row.select_one(".map-text, .stage, .round-info, [class*='stage']")
        if stage_elem:
            stage = stage_elem.get_text(strip=True)

        # 提取时间
        time_elem = row.select_one(".time, [data-time], [data-timestamp]")
        time_text = time_elem.get_text(strip=True) if time_elem else ""
        timestamp = row.get("data-timestamp", row.get("data-time", ""))

        kickoff = self._parse_time(time_text, timestamp)

        return {
            "match_id": match_id,
            "event_name": event_name,
            "event_id": event_id,
            "team1": team1 or "TBD",
            "team2": team2 or "TBD",
            "kickoff": kickoff,
            "bo_type": bo_type,
            "stage": stage,
        }

    def _parse_time(self, time_text: str, timestamp: str) -> datetime:
        """解析时间"""
        now = datetime.now(CST)

        if timestamp:
            try:
                ts = int(timestamp)
                if ts > 1e15:
                    ts = ts // 1000
                elif ts > 1e12:
                    ts = ts // 1000
                return datetime.fromtimestamp(ts, pytz.utc).astimezone(CST)
            except (ValueError, OSError):
                pass

        if not time_text:
            return now + timedelta(days=1)

        # 尝试绝对时间
        tm = re.search(r'(\d{1,2}):(\d{2})', time_text)
        if tm:
            h, m = int(tm.group(1)), int(tm.group(2))
            result = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if result < now:
                result += timedelta(days=1)
            return result

        return now + timedelta(days=1)

    def _save_cache(self):
        """保存缓存"""
        try:
            cache_data = []
            for m in self.matches:
                cache_data.append({
                    **m,
                    "kickoff": m["kickoff"].isoformat(),
                })
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"缓存保存失败: {e}")

    def _load_cache(self) -> List[Dict]:
        """加载缓存"""
        try:
            if not os.path.exists(CACHE_FILE):
                return []
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            matches = []
            for item in data:
                item["kickoff"] = datetime.fromisoformat(item["kickoff"])
                matches.append(item)
            return matches
        except Exception as e:
            logger.debug(f"缓存加载失败: {e}")
            return []

    def to_ics_events(self) -> List[ICSEvent]:
        """将 CS2 比赛数据转换为 ICS 事件列表"""
        events = []

        for m in self.matches:
            kickoff = m["kickoff"]
            bo_type = m.get("bo_type", "BO3")

            if bo_type == "BO5":
                duration = MATCH_DURATION_BO5
            elif bo_type == "BO1":
                duration = MATCH_DURATION_BO1
            else:
                duration = MATCH_DURATION

            end_time = kickoff + duration
            team1 = m.get("team1", "TBD")
            team2 = m.get("team2", "TBD")
            event_name = m.get("event_name", "")
            stage = m.get("stage", "")

            summary = f"🎮 {team1} vs {team2} ({bo_type})"

            desc_parts = [
                f"赛事: {event_name}",
                f"对阵: {team1} vs {team2}",
                f"赛制: {bo_type}",
                f"时间: {kickoff.strftime('%Y-%m-%d %H:%M')} (北京时间)",
            ]
            if stage:
                desc_parts.append(f"阶段: {stage}")

            description = "\n".join(desc_parts)
            uid = generate_event_uid("cs2", m["match_id"], kickoff)

            categories = ["CS2", event_name]
            if stage:
                categories.append(stage)

            event = ICSEvent(
                summary=summary,
                start=kickoff,
                end=end_time,
                description=description,
                location=event_name,
                uid=uid,
                categories=categories,
                is_all_day=False,
            )
            events.append(event)

        return events


def build_cs2_ics(output_path: str) -> str:
    """生成 CS2 赛事 ICS 文件"""
    logger.info("开始获取 CS2 赛事数据...")
    fetcher = HLTVFetcher()
    matches = fetcher.fetch()

    logger.info(f"获取到 {len(matches)} 场比赛")

    events = fetcher.to_ics_events()

    generator = ICSGenerator("cs2")
    generator.add_events(events)
    generator.save(output_path)

    logger.info(f"CS2 ICS 文件已保存: {output_path}")
    return output_path
