"""18 档评级映射单一事实源（canonical rating intervals，高→低排序）。

本模块位于 src/（随发行包分发），供 src/composite_scorer.py 的评级映射/CCC 封顶与
scripts/consistency_check.py 的评级表漂移门禁双向 import 同源——禁止在任何一处复制
数值副本。区间语义以 dev/engine/dual-track-methodology.md §六 为最终裁决。
"""

CANONICAL_RATING_INTERVALS = [
    (9.5, 10.0, "AAA"),
    (9.0, 9.4, "AA+"),
    (8.5, 8.9, "AA"),
    (8.0, 8.4, "AA-"),
    (7.5, 7.9, "A+"),
    (7.0, 7.4, "A"),
    (6.5, 6.9, "A-"),
    (6.0, 6.4, "BBB+"),
    (5.5, 5.9, "BBB"),
    (5.0, 5.4, "BBB-"),
    (4.5, 4.9, "BB+"),
    (4.0, 4.4, "BB"),
    (3.5, 3.9, "BB-"),
    (3.0, 3.4, "B+"),
    (2.5, 2.9, "B"),
    (2.0, 2.4, "B-"),
    (1.0, 1.9, "CCC"),
    (0.0, 0.9, "D"),
]
