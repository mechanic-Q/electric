#!/usr/bin/env python3
"""CLI 壳 — 调用 ShanxiFetcher 从命令行抓取山西数据.

用法:
    python ellectric/scripts/fetch_shanxi.py --month 2026-06 --source spot_da
    python ellectric/scripts/fetch_shanxi.py --all
    python ellectric/scripts/fetch_shanxi.py --range 2026-01:2026-06
    python ellectric/scripts/fetch_shanxi.py --sources spot_da,spot_rt
"""

import argparse, logging, sys
sys.path.insert(0, '.')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def parse_range(r: str) -> list[str]:
    """'2026-01:2026-06' → ['2026-01','2026-02',...]"""
    parts = r.split(':')
    if len(parts) != 2:
        raise ValueError(f"range 格式 YYYY-MM:YYYY-MM (got '{r}')")
    months = []
    y1, m1 = map(int, parts[0].split('-'))
    y2, m2 = map(int, parts[1].split('-'))
    while (y1, m1) <= (y2, m2):
        months.append(f"{y1}-{m1:02d}")
        m1 += 1
        if m1 > 12:
            m1 = 1; y1 += 1
    return months

def main():
    parser = argparse.ArgumentParser(description="山西现货数据抓取")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="抓取全部 18 API × 全部月份")
    g.add_argument("--source", type=str, help="API 名 (如 spot_da)")
    g.add_argument("--sources", type=str, help="API 列表 (逗号分隔)")
    parser.add_argument("--month", type=str, default=None, help="月份 YYYY-MM (默认当月)")
    parser.add_argument("--range", type=str, default=None, help="月份范围 YYYY-MM:YYYY-MM")
    parser.add_argument("--cookie", type=str, default=None, help="X-Ticket (默认 SHANXI_COOKIE env)")
    args = parser.parse_args()

    from ellectric.fetch.shanxi import ShanxiFetcher
    fetcher = ShanxiFetcher(cookie=args.cookie)

    months = None
    if args.range:
        months = parse_range(args.range)
    elif args.month:
        months = [args.month]

    if args.source:
        results = {f"{args.source}_{m}": fetcher.fetch_one(args.source, m) for m in (months or [fetcher._default_months()[-1]])}
    elif args.sources:
        slist = [s.strip() for s in args.sources.split(',')]
        results = fetcher.fetch_range(sources=slist, months=months)
    elif args.all:
        results = fetcher.fetch_range(months=months)
    else:
        parser.print_help(); sys.exit(1)

    ok = sum(1 for r in results.values() if r.get("rows", 0) > 0)
    empty = sum(1 for r in results.values() if r.get("rows", 0) == 0)
    err = sum(1 for r in results.values() if "error" in r)
    print(f"\n完成. 有数据={ok} 空={empty} 失败={err}")
    sys.exit(1 if err > 0 else 0)

if __name__ == "__main__":
    main()
