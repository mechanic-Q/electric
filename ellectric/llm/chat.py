"""
LLM 交互式对话入口 — 终端中启动 Ellectric 电力交易助手对话。

Usage:
    python -m ellectric.llm.chat
"""

import os
import sys


def main():
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("错误: 未设置 DEEPSEEK_API_KEY 环境变量")
        print("请设置: export DEEPSEEK_API_KEY=sk-xxx")
        sys.exit(1)

    from ellectric.llm.agent import ask_agent

    print("Ellectric 电力交易助手 (输入 /exit 退出)")

    while True:
        try:
            user_input = input("\n你: ").strip()
            if not user_input:
                continue
            if user_input == "/exit":
                print("再见!")
                break
            result = ask_agent(user_input)
            print(f"\n助手: {result}")
        except KeyboardInterrupt:
            print("\n再见!")
            break
        except Exception as e:
            print(f"\n错误: {e}")


if __name__ == "__main__":
    main()
