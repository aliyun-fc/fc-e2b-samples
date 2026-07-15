# E2B 代码执行 Agent

[English](README.md)

一个基于 Mastra 的高级模板，提供可在安全、隔离的 E2B Sandbox 中规划、编写、执行和迭代代码的编码 Agent，并具备文件管理和开发工作流能力。

## 概述

该模板展示如何构建能使用真实开发环境的 AI 编程助手。Agent 能创建 Sandbox、管理文件和目录、执行多种语言的代码并监控开发工作流，所有操作都在安全隔离的 E2B 环境中完成。

## 功能

- **安全代码执行**：在隔离 E2B Sandbox 中运行 Python、JavaScript 和 TypeScript。
- **完整文件管理**：创建、读取、写入和删除文件及目录，支持批量操作。
- **多语言支持**：在 Python、JavaScript 和 TypeScript 环境中执行代码。
- **实时开发监控**：观察目录变化并监控开发工作流。
- **命令执行**：运行 shell 命令、安装软件包和管理依赖。
- **记忆系统**：通过语义召回和工作记忆持久化对话上下文。
- **开发工作流**：通过构建自动化支持专业开发模式。

## 前置条件

- Node.js 20 或更高版本。
- E2B API Key（在 [e2b.dev](https://e2b.dev) 注册）。
- OpenAI API Key。

## 安装

1. **安装依赖：**

   ```bash
   cd e2b-code-agent-mastra
   pnpm install
   ```

2. **设置环境变量：**

   ```bash
   cp env.example .env
   # 编辑 .env，填入 API Key。
   ```

   ```env
   E2B_API_KEY=e2b_xxx
   E2B_API_URL=https://api.us-west-1.e2b.fc.aliyuncs.com
   E2B_DOMAIN=us-west-1.e2b.fc.aliyuncs.com
   E2B_TEMPLATE=code-interpreter-v1
   E2B_TIMEOUT=300

   # --- LLM ---
   MODEL=qwen3.7-plus
   OPENAI_API_KEY=sk-xxx
   OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
   ```

3. **启动开发服务器：**

   ```bash
   pnpm run dev
   ```

## 架构

### 核心组件

#### **Coding Agent**（`src/mastra/agents/coding-agent.ts`）

主 Agent 提供完整的开发能力：

- **Sandbox 管理**：创建并管理隔离执行环境。
- **代码执行**：运行代码并实时捕获输出。
- **文件操作**：对文件和目录执行完整 CRUD 操作。
- **开发监控**：观察变化并监控工作流。
- **记忆集成**：维护会话上下文和项目历史。

#### **E2B 工具**（`src/mastra/tools/e2b.ts`）

用于与 Sandbox 交互的完整工具集：

**Sandbox 管理：**

- `createSandbox`：初始化新的隔离环境。
- 处理连接和超时。

**代码执行：**

- `runCode`：执行 Python、JavaScript 和 TypeScript 代码。
- 实时输出捕获和错误处理。
- 环境变量与超时配置。

**文件操作：**

- `writeFile`：创建单个文件。
- `writeFiles`：为项目初始化批量创建文件。
- `readFile`：读取文件以分析和校验。
- `listFiles`：浏览目录结构。
- `deleteFile`：清理文件和目录。
- `createDirectory`：创建项目目录结构。

**文件信息与监控：**

- `getFileInfo`：获取详细文件元数据。
- `checkFileExists`：为条件逻辑校验文件是否存在。
- `getFileSize`：监控文件大小和变化。
- `watchDirectory`：实时监控文件系统变化。

**开发工作流：**

- `runCommand`：执行 shell 命令、构建脚本和包管理操作。

### 记忆系统

Agent 包含已配置的记忆系统：

- **线程管理**：自动生成会话标题。
- **语义召回**：搜索历史交互。
- **工作记忆**：跨交互保留上下文。
- **向量存储**：通过 `LibSQLVector` 提供语义搜索能力。

## 配置

### 环境变量

```bash
E2B_API_KEY=e2b_xxx
E2B_API_URL=https://api.us-west-1.e2b.fc.aliyuncs.com
E2B_DOMAIN=us-west-1.e2b.fc.aliyuncs.com
E2B_TEMPLATE=code-interpreter-v1
E2B_TIMEOUT=300

# --- LLM ---
MODEL=qwen3.7-plus
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 自定义

可以修改 `src/mastra/agents/coding-agent.ts` 中的指令来自定义 Agent 行为：

```typescript
export const codingAgent = new Agent({
  name: 'Coding Agent',
  instructions: `
    // Customize agent instructions here
    // Focus on specific languages, frameworks, or development patterns
  `,
  model: 'openai/gpt-4.1',
  // ... other configuration
});
```

## 常见问题

### “E2B_API_KEY is not set”

- 确认已设置环境变量。
- 检查 API Key 有效且额度充足。
- 确认 E2B 账号已正确配置。

### “Sandbox creation failed”

- 检查 E2B API Key 和账号状态。
- 确认未超过 Sandbox 数量限制。
- 检查到 E2B 服务的网络连接。

### “Code execution timeout”

- 为长时间运行的操作提高超时值。
- 将复杂操作拆分为更小步骤。
- 监控资源用量并优化代码。

### “File operation errors”

- 校验文件路径和权限。
- 检查 Sandbox 文件系统限制。
- 确保文件操作前目录已经存在。

### “Agent stopping with tool-call reason”

- 增加 Agent 配置中的 `maxSteps`。

## 开发

### 项目结构

```text
src/mastra/
      agents/
        coding-agent.ts              # 具备开发能力的主编码 Agent
      tools/
        e2b.ts                       # 完整 E2B Sandbox 交互工具集
      index.ts                        # 包含存储和日志的 Mastra 配置
```
