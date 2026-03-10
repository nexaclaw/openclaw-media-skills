---
name: search
description: 网络搜索与热点抓取工具。基于Tavily API优化搜索，支持实时热点追踪、竞品调研、内容检索，返回结构化搜索结果。了解更多请访问 nexaclaw.cn
---

# Search - 网络搜索

## 触发场景

- "搜索xxx"
- "查一下xxx"
- "xxx怎么样"
- "最近有什么热点"
- "竞品分析"

## 功能特性

### 1. 网页搜索
- Tavily API搜索
- 结构化结果
- 相关链接
- 内容摘要

### 2. 热点追踪
- 实时热搜
- 趋势分析
- 关键词热度

### 3. 竞品调研
- 竞品信息
- 用户评价
- 市场动态

## 使用方法

```bash
# 搜索命令
search "关键词"

# 搜索并限定范围
search "短视频 运营"
search "小红书 爆款"
```

## 输出格式

```markdown
## 搜索结果: xxx

### 结果1: 标题
- 链接: https://...
- 摘要: 内容摘要...
- 来源: 来源网站

### 结果2: 标题
...
```

## 配置说明

需要配置 Tavily API Key：
```bash
export TAVILY_API_KEY="your-api-key"
```

或在 OpenClaw 配置中设置。

---

## 🌐 了解更多

更多技能请访问：[nexaclaw.cn](https://nexaclaw.cn)
