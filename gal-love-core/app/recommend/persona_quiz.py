"""把一个画像体系适配成统一的 provider 契约。

现有 ``quiz.py`` 保留了题目与计算逻辑，这里只做接口对齐，
使口味问答与其他画像体系走同一条注册与合并链路。
"""

from __future__ import annotations

from .quiz import QUESTIONS, calculate_profile, filter_answers

KEY = "quiz"
TITLE = "口味测试"
SUBTITLE = "8 题，测你的叙事、氛围、节奏与结局偏好"
KIND = "questionnaire"
GROUP = "serious"
ESTIMATED_MINUTES = 2


def calculate(answers: dict[str, str]) -> dict:
    return calculate_profile(filter_answers(answers))
