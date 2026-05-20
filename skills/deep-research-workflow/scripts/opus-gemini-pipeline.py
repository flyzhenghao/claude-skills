#!/usr/bin/env python3
"""
Opus-Gemini Deep Research Pipeline
并发执行 Gemini Deep Research，支持多市场同时研究

Usage:
    python opus-gemini-pipeline.py <tasks.json>

Example:
    python opus-gemini-pipeline.py tasks.json
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import time

try:
    import google.generativeai as genai
except ImportError:
    print("❌ 错误: 缺少 google-generativeai 库")
    print("请运行: pip install google-generativeai")
    sys.exit(1)

# 配置 - 使用环境变量或默认值
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))

# 动态获取项目根目录
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent  # .claude/skills/deep-research-workflow/scripts -> project root

# 默认输出目录（可通过 tasks.json 覆盖）
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "knowledge-base/ai-generated/analysis/research-reports"
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"

# 配置 Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("⚠️  警告: 未设置 GEMINI_API_KEY 或 GOOGLE_API_KEY 环境变量")
    print("请设置环境变量或在脚本中配置 API Key")


class GeminiResearchWorker:
    """Gemini Deep Research Worker - 单个市场研究执行器"""

    def __init__(self, market_id: str, market_name: str, research_prompt: str, model_name: str = "gemini-2.0-flash-exp"):
        self.market_id = market_id
        self.market_name = market_name
        self.research_prompt = research_prompt
        self.model_name = model_name
        self.start_time = None
        self.end_time = None
        self.status = "pending"
        self.result = None
        self.error = None

    async def execute(self):
        """执行研究任务"""
        self.start_time = datetime.now()
        self.status = "running"

        print(f"\n{'='*60}")
        print(f"🔍 开始研究: {self.market_name}")
        print(f"📋 任务 ID: {self.market_id}")
        print(f"🤖 模型: {self.model_name}")
        print(f"⏰ 开始时间: {self.start_time.strftime('%H:%M:%S')}")
        print(f"{'='*60}\n")

        try:
            # 创建模型实例
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                }
            )

            # 增强的提示词（启用搜索）
            enhanced_prompt = f"""{self.research_prompt}

## 搜索要求

请使用 Google Search 功能搜索最新的、准确的信息。确保：
1. 数据来自 2024-2025 年的最新资料
2. 包含具体的数字和统计数据
3. 标注所有信息来源（URL、日期）
4. 对比多个来源以确保准确性

## 输出格式

使用 Markdown 格式，包含：
- 清晰的标题层级
- 对比表格（使用 | 分隔）
- 数据可视化（用 Markdown 表格展示）
- 完整的参考文献列表

现在开始研究。
"""

            # 调用 Gemini API（同步方式，因为 SDK 不支持真正的 async）
            response = await asyncio.to_thread(
                model.generate_content,
                enhanced_prompt
            )

            # 提取结果
            self.result = response.text
            self.status = "completed"
            self.end_time = datetime.now()

            duration = (self.end_time - self.start_time).total_seconds()
            print(f"✅ 完成: {self.market_name}")
            print(f"⏱️  用时: {duration:.2f} 秒")
            print(f"📊 字数: {len(self.result)} 字符\n")

            return {
                "market_id": self.market_id,
                "market_name": self.market_name,
                "status": "success",
                "duration": duration,
                "output_length": len(self.result),
                "result": self.result
            }

        except Exception as e:
            self.status = "failed"
            self.error = str(e)
            self.end_time = datetime.now()

            print(f"❌ 失败: {self.market_name}")
            print(f"🔴 错误: {str(e)}\n")

            return {
                "market_id": self.market_id,
                "market_name": self.market_name,
                "status": "failed",
                "error": str(e)
            }


class ResearchOrchestrator:
    """研究协调器 - 管理并发执行"""

    def __init__(self, config: Dict, output_dir: Path, log_dir: Path):
        self.config = config
        self.output_dir = output_dir
        self.log_dir = log_dir
        self.workers = []
        self.results = []
        self.start_time = None
        self.end_time = None

        # 创建目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def create_workers(self):
        """创建所有 Worker"""
        markets = self.config["markets"]
        model_name = self.config["research_config"].get("gemini_model", "gemini-2.0-flash-exp")

        for market in markets:
            worker = GeminiResearchWorker(
                market_id=market["id"],
                market_name=market["name"],
                research_prompt=market["research_prompt"],
                model_name=model_name
            )
            self.workers.append(worker)

        print(f"📦 已创建 {len(self.workers)} 个研究 Worker")

    async def execute_concurrent(self):
        """并发执行所有任务"""
        self.start_time = datetime.now()

        print(f"\n{'='*80}")
        print(f"🚀 开始并发执行 - {len(self.workers)} 个市场同时研究")
        print(f"⏰ 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        # 并发执行（使用 asyncio.gather）
        tasks = [worker.execute() for worker in self.workers]
        self.results = await asyncio.gather(*tasks, return_exceptions=True)

        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        print(f"\n{'='*80}")
        print(f"🎉 全部完成！")
        print(f"⏱️  总用时: {duration:.2f} 秒 ({duration/60:.2f} 分钟)")
        print(f"✅ 成功: {sum(1 for r in self.results if isinstance(r, dict) and r['status'] == 'success')} 个")
        print(f"❌ 失败: {sum(1 for r in self.results if isinstance(r, dict) and r['status'] == 'failed')} 个")
        print(f"{'='*80}\n")

    def save_results(self):
        """保存所有结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存每个市场的报告
        for result in self.results:
            if isinstance(result, dict) and result["status"] == "success":
                market_id = result["market_id"]
                market_name = result["market_name"]
                content = result["result"]

                # 文件名
                filename = f"{market_id}_{market_name.replace(' ', '_')}.md"
                filepath = self.output_dir / filename

                # 写入文件
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {market_name}\n\n")
                    f.write(f"**任务 ID**: {market_id}\n")
                    f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"**模型**: {self.config['research_config'].get('gemini_model', 'gemini-2.0-flash-exp')}\n")
                    f.write(f"**字数**: {len(content)} 字符\n\n")
                    f.write(f"---\n\n")
                    f.write(content)

                print(f"💾 已保存: {filepath}")

        # 生成汇总文件（给 Opus 分析用）
        summary_file = self.output_dir / f"summary_for_opus_{timestamp}.md"
        self.generate_opus_summary(summary_file)

        # 保存执行日志
        log_file = self.log_dir / f"research_execution_log_{timestamp}.json"
        self.save_execution_log(log_file)

        print(f"\n✅ 所有结果已保存到: {self.output_dir}")
        print(f"📊 Opus 分析文件: {summary_file}")
        print(f"📋 执行日志: {log_file}")

    def generate_opus_summary(self, output_file: Path):
        """生成 Opus 分析用的汇总文件"""
        project_name = self.config.get("project_name", "研究项目")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {project_name} 研究报告汇总\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**研究市场数**: {len(self.results)}\n")
            f.write(f"**执行用时**: {(self.end_time - self.start_time).total_seconds()/60:.2f} 分钟\n\n")
            f.write(f"---\n\n")

            # 添加每个市场的报告
            for i, result in enumerate(self.results, 1):
                if isinstance(result, dict) and result["status"] == "success":
                    market_name = result["market_name"]
                    content = result["result"]

                    f.write(f"## 市场 {i}: {market_name}\n\n")
                    f.write(content)
                    f.write(f"\n\n{'='*80}\n\n")

            # 添加 Opus 分析提示
            f.write(f"\n\n# Opus 综合分析任务\n\n")
            f.write(f"基于以上 {len(self.results)} 个市场的研究报告，请帮我：\n\n")
            f.write(f"1. **综合分析** - 跨市场的共同趋势、差异和模式\n")
            f.write(f"2. **机会识别** - 最有潜力的方向（前 3 名）\n")
            f.write(f"3. **战略建议** - 如果要进入某个市场，推荐哪个？为什么？\n")
            f.write(f"4. **风险评估** - 各市场的主要风险和进入壁垒\n")
            f.write(f"5. **竞争格局** - 整体竞争态势和定位建议\n")
            f.write(f"6. **行动计划** - 下一步应该做什么？（3-5 个具体行动）\n\n")
            f.write(f"输出一份 **Executive Summary**（高管摘要），2000-3000 字，包含：\n")
            f.write(f"- 关键发现（5-7 条）\n")
            f.write(f"- 战略建议（优先级排序）\n")
            f.write(f"- 风险矩阵（市场 × 风险类型）\n")
            f.write(f"- 行动时间表\n")

    def save_execution_log(self, log_file: Path):
        """保存执行日志"""
        log_data = {
            "execution_time": {
                "start": self.start_time.isoformat(),
                "end": self.end_time.isoformat(),
                "duration_seconds": (self.end_time - self.start_time).total_seconds()
            },
            "config": self.config["research_config"],
            "results": [
                {
                    "market_id": r.get("market_id"),
                    "market_name": r.get("market_name"),
                    "status": r.get("status"),
                    "duration": r.get("duration"),
                    "output_length": r.get("output_length"),
                    "error": r.get("error")
                }
                for r in self.results if isinstance(r, dict)
            ]
        }

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)


async def main(tasks_file: str):
    """主函数"""
    print(f"\n{'='*80}")
    print(f"🎯 Opus-Gemini Deep Research Pipeline (Mode C - generateContent)")
    print(f"{'='*80}\n")

    # 1. 读取任务配置
    print(f"📖 读取任务配置: {tasks_file}")
    with open(tasks_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    total_markets = config["research_config"]["total_markets"]
    print(f"✅ 任务配置已加载")
    print(f"📊 市场总数: {total_markets}")
    print(f"⚙️  执行模式: {config['research_config']['execution_mode']}")
    print(f"🤖 模型: {config['research_config'].get('gemini_model', 'gemini-2.0-flash-exp')}\n")

    # 确定输出目录
    output_dir_str = config["research_config"].get("output_dir")
    if output_dir_str:
        output_dir = Path(output_dir_str)
        if not output_dir.is_absolute():
            output_dir = PROJECT_ROOT / output_dir_str
    else:
        output_dir = DEFAULT_OUTPUT_DIR

    log_dir = DEFAULT_LOG_DIR

    # 2. 创建协调器
    orchestrator = ResearchOrchestrator(config, output_dir, log_dir)
    orchestrator.create_workers()

    # 3. 并发执行
    await orchestrator.execute_concurrent()

    # 4. 保存结果
    orchestrator.save_results()

    print(f"\n{'='*80}")
    print(f"🎊 任务完成！")
    print(f"\n下一步：")
    print(f"1. 打开 {output_dir / 'summary_for_opus_*.md'}")
    print(f"2. 复制全部内容")
    print(f"3. 粘贴到 claude.ai（使用 Opus 模型）或在 Claude Code 中使用 /model opus")
    print(f"4. 等待 Opus 生成综合分析")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    # 🚨 模式检查：优先显示模式警告
    print(f"\n{'='*80}")
    print(f"⚠️  警告: 此脚本使用模式 C（generateContent），质量较低（无实时搜索）")
    print(f"\n推荐使用模式 A（分享链接批量获取）获得更高质量结果：")
    print(f"  python3 .claude/scripts/fetch-deep-research-batch.py")
    print(f"\n如需继续使用模式 C，请修改脚本中的 MODE_CHECK_BYPASS 变量")
    print(f"{'='*80}\n")

    # 模式检查开关（设置为 False 禁用模式 C）
    MODE_CHECK_BYPASS = False

    if not MODE_CHECK_BYPASS:
        print(f"❌ 模式 C 已禁用")
        print(f"\n✅ 请使用模式 A（推荐）:")
        print(f"   python3 .claude/scripts/fetch-deep-research-batch.py")
        print(f"\n或模式 B（需付费 API Key）:")
        print(f"   python3 .claude/scripts/gemini-rerun-research.py --mode deep-research")
        print(f"\n详见: ~/.claude/skills/deep-research-workflow/SKILL.md")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("用法: python opus-gemini-pipeline.py <tasks.json>")
        print("示例: python opus-gemini-pipeline.py tasks.json")
        sys.exit(1)

    tasks_file = sys.argv[1]

    if not os.path.exists(tasks_file):
        print(f"❌ 错误: 文件不存在: {tasks_file}")
        sys.exit(1)

    # 检查 API Key
    if not GEMINI_API_KEY:
        print("❌ 错误: 未设置 GEMINI_API_KEY 或 GOOGLE_API_KEY 环境变量")
        print("请运行: export GEMINI_API_KEY='your-api-key'")
        sys.exit(1)

    # 运行
    asyncio.run(main(tasks_file))
