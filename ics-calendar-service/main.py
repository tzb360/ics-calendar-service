#!/usr/bin/env python3
"""
ICS Calendar Service - Main Entry Point
ICS 日历订阅服务主入口

用法:
  python main.py holidays    # 仅生成节假日 ICS
  python main.py worldcup    # 仅生成世界杯 ICS
  python main.py cs2         # 仅生成 CS2 ICS
  python main.py all         # 生成全部 ICS + 聚合版
"""

import argparse
import logging
import os
import sys

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.holidays_fetcher import build_holidays_ics
from src.worldcup_fetcher import build_worldcup_ics
from src.cs2_fetcher import build_cs2_ics
from src.ics_generator import merge_ics_files

# ── 配置 ────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def get_output_paths(output_dir: str) -> dict:
    """根据输出目录计算所有输出文件路径"""
    return {
        "holidays": os.path.join(output_dir, "holidays.ics"),
        "worldcup": os.path.join(output_dir, "worldcup.ics"),
        "cs2": os.path.join(output_dir, "cs2.ics"),
        "all": os.path.join(output_dir, "all.ics"),
    }


def run_holidays(paths: dict) -> str:
    """生成节假日日历"""
    os.makedirs(os.path.dirname(paths["holidays"]), exist_ok=True)
    return build_holidays_ics(paths["holidays"])


def run_worldcup(paths: dict) -> str:
    """生成世界杯日历"""
    os.makedirs(os.path.dirname(paths["worldcup"]), exist_ok=True)
    return build_worldcup_ics(paths["worldcup"])


def run_cs2(paths: dict) -> str:
    """生成 CS2 赛事日历"""
    os.makedirs(os.path.dirname(paths["cs2"]), exist_ok=True)
    return build_cs2_ics(paths["cs2"])


def run_all(paths: dict) -> str:
    """生成所有日历 + 聚合版"""
    results = []

    # 生成各分类日历
    results.append(("Holidays", run_holidays(paths)))
    results.append(("World Cup", run_worldcup(paths)))
    results.append(("CS2", run_cs2(paths)))

    # 聚合
    logger.info("生成聚合日历...")
    merge_ics_files(
        [paths["holidays"], paths["worldcup"], paths["cs2"]],
        paths["all"],
    )
    results.append(("All (merged)", paths["all"]))

    # 打印结果摘要
    logger.info("=" * 50)
    logger.info("日历文件生成完成:")
    for name, path in results:
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            logger.info(f"  {name}: {path} ({size_kb:.1f} KB)")
        else:
            logger.warning(f"  {name}: 生成失败")
    logger.info("=" * 50)

    return paths["all"]


def main():
    parser = argparse.ArgumentParser(
        description="ICS Calendar Service - ICS 日历订阅服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py holidays    仅生成节假日 ICS
  python main.py worldcup    仅生成世界杯赛程 ICS
  python main.py cs2         仅生成 CS2 赛事 ICS
  python main.py all         生成全部 (含聚合版)
        """,
    )
    parser.add_argument(
        "target",
        choices=["holidays", "worldcup", "cs2", "all"],
        default="all",
        nargs="?",
        help="要生成的目标日历 (默认: all)",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"输出目录 (默认: {DEFAULT_OUTPUT_DIR})",
    )

    args = parser.parse_args()
    output_dir = args.output_dir
    paths = get_output_paths(output_dir)

    logger.info(f"目标: {args.target}, 输出目录: {output_dir}")

    builders = {
        "holidays": lambda: run_holidays(paths),
        "worldcup": lambda: run_worldcup(paths),
        "cs2": lambda: run_cs2(paths),
        "all": lambda: run_all(paths),
    }

    try:
        result = builders[args.target]()
        if result:
            logger.info(f"✅ 完成: {result}")
    except Exception as e:
        logger.error(f"❌ 生成失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
