---
name: workflow-automation
description: 自定义自动化工作流编排工具。支持多技能串联、条件触发、定时任务、数据流转，实现自媒体运营全流程自动化，提升效率。了解更多请访问 nexaclaw.cn
---

# Workflow Automation - 工作流自动化

## 触发场景

- "创建自动化流程"
- "定时任务"
- "多步骤自动化"
- "运营自动化"

## 功能特性

### 1. 工作流编排
- 可视化流程设计
- 技能节点拖拽
- 条件分支
- 循环逻辑

### 2. 触发器
- 定时触发
- 事件触发
- 手动触发
- API触发

### 3. 数据流转
- 节点间数据传递
- 变量存储
- 外部API调用
- 数据转换

### 4. 监控日志
- 执行记录
- 失败告警
- 运行状态
- 性能分析

## 典型工作流示例

```yaml
# 每日热点选题工作流
workflow:
  trigger: daily 9:00
  steps:
    - trending-hot: 抓取今日热点
    - topic-generator: 生成选题建议
    - content-calendar: 添加到日历
    - notification: 推送提醒
```

```yaml
# 自动发布工作流
workflow:
  trigger: manual
  steps:
    - copywriter: 生成文案
    - canghe-cover-image: 生成封面
    - XiaohongshuSkills: 发布到小红书
    - analytics-dashboard: 记录数据
```

## 使用方法

1. 创建工作流
2. 添加技能节点
3. 配置触发器
4. 启用运行

---

## 🌐 了解更多

更多技能请访问：[nexaclaw.cn](https://nexaclaw.cn)
