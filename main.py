"""
Glean AI Agent - 使用示例
"""
import asyncio
from loguru import logger

from core.agent import GleanAI
from core.glean_chat_agent import GleanChatAgent, create_context_agent
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


def run_glean_chat_demo():
    """使用 Glean Chat API 的简化 Demo"""
    logger.info("=" * 60)
    logger.info("🚀 Glean Chat Agent Demo (Optimized)")
    logger.info("=" * 60)

    # 使用优化的 Glean Chat Agent
    agent = create_context_agent()

    questions = [
        "我们公司关于远程工作的政策是什么？",
        "如何申请年假？需要准备哪些材料？",
        "IT 安全政策中关于密码的要求是什么？",
        "我们公司使用哪些项目管理工具？",
        "公司的休假制度是怎样的？"
    ]

    for i, question in enumerate(questions, 1):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Query {i}/{len(questions)}: {question}")
        logger.info(f"{'=' * 60}")

        # 查询（使用 Glean Chat API）
        response = agent.query(question)

        # 显示结果
        print("\n" + "=" * 60)
        print("💡 ANSWER (Glean Chat API)")
        print("=" * 60)
        print(response.get("answer", "No answer generated"))

        if response.get("sources"):
            print("\n" + "=" * 60)
            print(f"📚 SOURCES ({len(response['sources'])} documents retrieved)")
            print("=" * 60)
            for source in response.get("sources", [])[:3]:
                print(f"\n  📄 {source.get('title', 'N/A')}")
                print(f"     - 来源: {source.get('datasource', 'N/A')}")
                if source.get("url"):
                    print(f"     - 链接: {source.get('url', 'N/A')}")

        print("\n" + "=" * 60)
        print("📊 METADATA")
        print("=" * 60)
        print(f"Execution Time: {response.get('execution_time', 0)}s")
        print(f"Success: {response.get('success', False)}")
        print(f"Sources Count: {len(response.get('sources', []))}")
        print("=" * 60)

        if i < len(questions):
            input("\nPress Enter to continue...")

    # 显示统计信息
    print("\n" + "=" * 60)
    print("📊 STATISTICS")
    print("=" * 60)
    stats = agent.get_stats()
    print(f"Total Queries: {stats['total_queries']}")
    print(f"Successful: {stats['successful_queries']}")
    print(f"Success Rate: {stats['success_rate']:.1%}")
    print(f"Conversation Length: {stats['conversation_length']}")
    print("=" * 60)


def run_glean_chat_interactive():
    """使用 Glean Chat API 的交互式模式"""
    agent = create_context_agent()

    print("=" * 60)
    print("🤖 Glean Chat Agent - Interactive Mode (Optimized)")
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

        response = agent.chat(question)

        print("\n" + "=" * 60)
        print("💡 ANSWER")
        print("=" * 60)
        print(response.get("answer", "No answer generated"))

        if response.get("success"):
            print("\n✅ Response successful")
        else:
            print("\n❌ Response failed")
            if response.get("error"):
                print(f"Error: {response['error']}")


def list_agents():
    """列出可用的 Glean Agents"""
    from core.glean_chat_agent import GleanChatAgent

    agent = GleanChatAgent(use_agents=True)

    print("=" * 60)
    print("🤖 Available Glean Agents")
    print("=" * 60)

    agents = agent.search_available_agents()

    if not agents:
        print("No agents found. You can create agents in Glean's Agent Builder:")
        print("  https://your-instance.glean.com/admin/agents")
    else:
        for idx, a in enumerate(agents, 1):
            print(f"\n{idx}. {a.get('name', 'N/A')}")
            print(f"   ID: {a.get('id', 'N/A')}")
            print(f"   Description: {a.get('description', 'N/A')}")

    print("\n" + "=" * 60)
    print("To use a specific agent:")
    print("  python main.py agent <agent_id> \"your question\"")
    print("=" * 60)


def run_with_agent(agent_id: str, question: str):
    """使用指定的 Agent 运行查询"""
    from core.glean_chat_agent import create_agent_with_id

    agent = create_agent_with_id(agent_id)

    print("=" * 60)
    print(f"🤖 Running Agent: {agent_id}")
    print("=" * 60)

    response = agent.query(question, with_context=False)

    print("\n" + "=" * 60)
    print("💡 AGENT ANSWER")
    print("=" * 60)
    print(response.get("answer", "No answer generated"))
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            asyncio.run(main())
        elif sys.argv[1] == "interactive":
            run_interactive()
        elif sys.argv[1] == "glean-chat-demo":
            run_glean_chat_demo()
        elif sys.argv[1] == "glean-chat-interactive":
            run_glean_chat_interactive()
        elif sys.argv[1] == "agents":
            list_agents()
        elif sys.argv[1] == "agent":
            if len(sys.argv) < 4:
                print("Usage: python main.py agent <agent_id> <question>")
                print("Example: python main.py agent agent-123 \"What is our policy?\"")
            else:
                run_with_agent(sys.argv[2], sys.argv[3])
        else:
            run_simple_query(" ".join(sys.argv[1:]))
    else:
        print("Usage:")
        print("  === Original Mode (with external LLM) ===")
        print("  python main.py demo                      - Run demo queries")
        print("  python main.py interactive               - Run interactive mode")
        print("  python main.py <question>              - Ask a single question")
        print()
        print("  === Optimized Mode (Glean Chat API) ===")
        print("  python main.py glean-chat-demo           - Run optimized demo (no external LLM)")
        print("  python main.py glean-chat-interactive    - Run optimized interactive mode")
        print()
        print("  === Glean Agents Mode ===")
        print("  python main.py agents                     - List available agents")
        print("  python main.py agent <id> <question>    - Run specific agent")
