"""
JQL 转换提示词模板

将自然语言转换为有效的 Jira JQL 查询语句
"""

# 系统提示词
SYSTEM_PROMPT = """你是一个专业的 Jira JQL（Jira Query Language）查询生成助手。
你的任务是将用户的自然语言描述转换为语法正确、可执行的 JQL 查询语句。

## JQL 语法基础

JQL 由字段、操作符和值组成，支持以下常见结构：

### 基本语法
- `field = value` - 等于
- `field != value` - 不等于
- `field IN (value1, value2)` - 在列表中
- `field NOT IN (value1, value2)` - 不在列表中
- `field IS NULL` / `field IS NOT NULL` - 空值判断
- `field > value` / `field < value` - 比较操作（适用于数字、日期）

### 逻辑操作符
- `AND` - 逻辑与
- `OR` - 逻辑或
- `NOT` - 逻辑非
- 使用括号 `()` 控制优先级

### 常用字段

**项目相关：**
- `project = "PROJECT_KEY"` - 项目键
- `project IN (KEY1, KEY2)` - 多个项目

**状态相关：**
- `status = "Open"` - 状态
- `status IN ("Open", "In Progress", "Reopened")` - 多个状态
- `statusCategory = "To Do"` - 状态分类

**优先级相关：**
- `priority = "High"` - 优先级
- `priority IN ("High", "Highest")` - 多个优先级

**分配相关：**
- `assignee = currentUser()` - 分配给当前用户
- `assignee = "user@company.com"` - 分配给指定用户
- `assignee IS EMPTY` - 未分配

**报告人相关：**
- `reporter = currentUser()` - 当前用户创建的
- `reporter = "user@company.com"` - 指定用户创建的

**创建/更新时间：**
- `created >= -7d` - 最近7天创建
- `created >= "2024-01-01"` - 指定日期后创建
- `updated >= -30d` - 最近30天更新

**问题类型：**
- `issuetype = "Bug"` - Bug
- `issuetype IN ("Bug", "Task", "Story")` - 多个类型

**文本搜索：**
- `summary ~ "keyword"` - 标题包含关键词
- `description ~ "keyword"` - 描述包含关键词
- `text ~ "keyword"` - 标题或描述包含

## 输出格式

请以 JSON 格式返回结果，必须包含以下字段：
```json
{
  "jql": "生成的JQL查询语句",
  "explanation": "对查询逻辑的简要说明",
  "fields_used": ["使用的字段列表"]
}
```

## 重要规则

1. **字段值**：字符串值必须用双引号包裹，如 `status = "Open"`
2. **项目键**：项目键不需要引号，如 `project = PROJ`
3. **用户名**：邮箱或用户名需要引号，如 `assignee = "user@company.com"`
4. **日期格式**：
   - 相对时间：`-1w` (1周前), `-7d` (7天前), `-30m` (30分钟前)
   - 绝对时间：`"2024-01-01"` 或 `"2024-01-01 10:00"`
5. **布尔值**：直接使用，如 `flagged = true`

## 示例

用户: "查找所有高优先级的 Bug"
输出: {"jql": "priority = \"Highest\" AND issuetype = \"Bug\"", "explanation": "查询优先级为最高且问题类型为Bug的工单", "fields_used": ["priority", "issuetype"]}

用户: "最近一周我创建的未解决问题"
输出: {"jql": "reporter = currentUser() AND status != \"Done\" AND created >= -7d", "explanation": "查询当前用户创建的、状态不是Done的、最近7天创建的工单", "fields_used": ["reporter", "status", "created"]}

用户: "分配给我的所有 Open 状态工单"
输出: {"jql": "assignee = currentUser() AND status = \"Open\"", "explanation": "查询分配给当前用户且状态为Open的工单", "fields_used": ["assignee", "status"]}

用户: "查找项目 PROJ 中所有 Story 和 Task"
输出: {"jql": "project = PROJ AND issuetype IN (\"Story\", \"Task\")", "explanation": "查询PROJ项目中类型为Story或Task的工单", "fields_used": ["project", "issuetype"]}
"""

# 示例提示词（用于 few-shot learning）
EXAMPLES = [
    {
        "input": "查找所有高优先级的 Bug",
        "output": {
            "jql": "priority = \"Highest\" AND issuetype = \"Bug\"",
            "explanation": "查询优先级为最高且问题类型为Bug的工单",
            "fields_used": ["priority", "issuetype"]
        }
    },
    {
        "input": "最近一周我创建的未解决问题",
        "output": {
            "jql": "reporter = currentUser() AND status != \"Done\" AND created >= -7d",
            "explanation": "查询当前用户创建的、状态不是Done的、最近7天创建的工单",
            "fields_used": ["reporter", "status", "created"]
        }
    },
    {
        "input": "分配给我的所有 Open 状态工单",
        "output": {
            "jql": "assignee = currentUser() AND status = \"Open\"",
            "explanation": "查询分配给当前用户且状态为Open的工单",
            "fields_used": ["assignee", "status"]
        }
    },
    {
        "input": "查找项目 PROJ 中所有 Story 和 Task",
        "output": {
            "jql": "project = PROJ AND issuetype IN (\"Story\", \"Task\")",
            "explanation": "查询PROJ项目中类型为Story或Task的工单",
            "fields_used": ["project", "issuetype"]
        }
    },
    {
        "input": "标题包含 'login' 的工单",
        "output": {
            "jql": "summary ~ \"login\"",
            "explanation": "查询标题中包含'login'关键词的工单",
            "fields_used": ["summary"]
        }
    },
    {
        "input": "未分配的 Bug",
        "output": {
            "jql": "issuetype = \"Bug\" AND assignee IS EMPTY",
            "explanation": "查询类型为Bug且未分配的工单",
            "fields_used": ["issuetype", "assignee"]
        }
    },
    {
        "input": "本月创建的高优先级任务",
        "output": {
            "jql": "priority IN (\"High\", \"Highest\") AND created >= -30d",
            "explanation": "查询本月创建的且优先级为高或最高的工单",
            "fields_used": ["priority", "created"]
        }
    },
    {
        "input": "所有进行中的 Story",
        "output": {
            "jql": "issuetype = \"Story\" AND status IN (\"In Progress\", \"Reopened\")",
            "explanation": "查询类型为Story且状态为进行中或重新打开的工单",
            "fields_used": ["issuetype", "status"]
        }
    }
]


def get_conversion_prompt(user_query: str, project_context: str = "") -> str:
    """
    生成 JQL 转换提示词

    Args:
        user_query: 用户的自然语言查询
        project_context: 项目上下文信息（可选）

    Returns:
        完整的提示词
    """
    prompt = SYSTEM_PROMPT

    # 添加项目上下文（如果有）
    if project_context:
        prompt += f"\n\n## 项目上下文\n{project_context}\n"

    # 添加示例
    prompt += "\n\n## 示例\n"
    for i, example in enumerate(EXAMPLES[:3], 1):
        prompt += f"\n示例 {i}:\n"
        prompt += f"输入: {example['input']}\n"
        prompt += f"输出: {example['output']}\n"

    # 添加用户查询
    prompt += f"\n\n请将以下查询转换为 JQL:\n{user_query}\n"
    prompt += "\n输出 JSON 格式:"

    return prompt


def get_fewshot_prompt(user_query: str) -> str:
    """
    获取包含多个示例的 Few-Shot 提示词

    Args:
        user_query: 用户的自然语言查询

    Returns:
        完整的 Few-Shot 提示词
    """
    examples_str = ""
    for example in EXAMPLES:
        examples_str += f"输入: {example['input']}\n"
        examples_str += f"输出: {example['output']}\n\n"

    prompt = f"""{SYSTEM_PROMPT}

## 示例

{examples_str}

请将以下查询转换为 JQL:
{user_query}

输出 JSON 格式:"""

    return prompt


def get_jql_syntax_reference() -> str:
    """
    获取 JQL 语法参考

    Returns:
        JQL 语法参考字符串
    """
    return """
## JQL 语法速查表

### 操作符
- `=` 等于
- `!=` 不等于
- `>` 大于
- `>=` 大于等于
- `<` 小于
- `<=` 小于等于
- `IN` 在列表中
- `NOT IN` 不在列表中
- `~` 包含（文本搜索）
- `!~` 不包含
- `IS NULL` 为空
- `IS NOT NULL` 不为空
- `WAS` 曾经是
- `WAS IN` 曾经在列表中
- `WAS NOT IN` 曾经不在列表中

### 字段
- `project` 项目
- `issuetype` 问题类型
- `status` 状态
- `priority` 优先级
- `assignee` 分配给
- `reporter` 报告人
- `created` 创建时间
- `updated` 更新时间
- `summary` 标题
- `description` 描述
- `labels` 标签
- `components` 组件

### 函数
- `currentUser()` 当前用户
- `membersOf("group")` 组成员
- `lead()` 项目负责人
"""
