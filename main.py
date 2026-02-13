"""
Glean AI Agent - 使用示例
"""
import asyncio
from loguru import logger

from core.agent import GleanAI
from config.config import LogLevel


async def main():
    """主函数 - 演示智能体功能"""
    
    # 配置日志
    logger.info("=" * 60)
    logger.info("🚀 Glean AI Agent Demo")
    logger.info("=" * 60)
    
    # 初始化智能体
    agent = GleanAI()
    
    # 示例查询
    questions = [
        "我们公司关于远程工作的政策是什么？",
        "如何申请年假？需要准备哪些材料？",
        "IT 安全政策中关于密码的要求是什么？",
        "我们公司使用哪些项目管理工具？各有什么优缺点？",
        "对比 Google Drive 和 SharePoint 在我们公司的使用情况"
    ]
    
    # 执行查询
    for i, question in enumerate(questions, 1):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Query {i}/{len(questions)}: {question}")
        logger.info(f"{'=' * 60}")
        
        # 查询
        response = agent.query(question)
        
        # 显示结果
        print("\n" + "=" * 60)
        print("📊 ANALYSIS")
        print("=" * 60)
        print(f"Type: {response.get('analysis', {}).get('type', 'N/A')}")
        print(f"Complexity: {response.get('analysis', {}).get('complexity', 'N/A')}")
        print(f"Entities: {', '.join(response.get('analysis', {}).get('entities', []))}")
        
        print("\n" + "=" * 60)
        print("🎯 EXECUTION PLAN")
        print("=" * 60)
        plan = response.get('plan', {})
        print(f"Steps: {plan.get('estimated_steps', 0)}")
        for step in plan.get('steps', [])[:5]:
            print(f"  - {step.get('description', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("💡 ANSWER")
        print("=" * 60)
        print(response.get('answer', 'No answer generated'))
        
        print("\n" + "=" * 60)
        print("📚 SOURCES")
        print("=" * 60)
        for source in response.get('sources', [])[:5]:
            print(f"\n  📄 {source.get('title', 'N/A')}")
            print(f"     URL: {source.get('url', 'N/A')}")
            print(f"     Source: {source.get('datasource', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("📊 METADATA")
        print("=" * 60)
        metadata = response.get('metadata', {})
        print(f"Execution Time: {metadata.get('execution_time', 0)}s")
        print(f"Total Searches: {metadata.get('total_searches', 0)}")
        print(f"Documents Retrieved: {metadata.get('documents_retrieved', 0)}")
        print(f"Confidence: {response.get('confidence', 'N/A')}")
        
        print("=" * 60)
        
        # 等待继续
        if i < len(questions):
            input("\nPress Enter to continue...")


def run_simple_query(question: str):
    """运行单个查询"""
    agent = GleanAI()
    response = agent.query(question)
    
    print("\n" + "=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(response.get('answer', 'No answer generated'))
    print("=" * 60)
    
    return response


def run_interactive():
    """交互式模式"""
    agent = GleanAI()
    
    print("=" * 60)
    print("🤖 Glean AI Agent - Interactive Mode")
    print("=" * 60)
    print("Type your questions below (or 'quit' to exit)")
    print()
    
    while True:
        question = input("\n> ")
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        if not question.strip():
            continue
        
        response = agent.query(question)
        
        print("\n" + "=" * 60)
        print("💡 ANSWER")
        print("=" * 60)
        print(response.get('answer', 'No answer generated'))
        
        if response.get('confidence'):
            conf = response['confidence']
            if conf > 0.7:
                print(f"\n✅ High confidence ({conf:.2f})")
            elif conf > 0.4:
                print(f"\n⚠️  Medium confidence ({conf:.2f})")
            else:
                print(f"\n❌ Low confidence ({conf:.2f})")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            asyncio.run(main())
        elif sys.argv[1] == "interactive":
            run_interactive()
        else:
            run_simple_query(" ".join(sys.argv[1:]))
    else:
        print("Usage:")
        print("  python main.py demo          - Run demo queries")
        print("  python main.py interactive   - Run interactive mode")
        print("  python main.py <question>   - Ask a single question")
