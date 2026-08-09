# 阿里云 E2B 沙箱示例

所有示例均面向阿里云 E2B。每个示例都需要在 `.env` 中配置以下 E2B 环境变量：

```ini
E2B_API_KEY=e2b_xxx
E2B_API_URL=https://api.us-west-1.e2b.fc.aliyuncs.com
E2B_DOMAIN=us-west-1.e2b.fc.aliyuncs.com
```

## 使用场景

| 示例 | 使用场景 |
| --- | --- |
| Code Interpreter | 在阿里云 E2B Code Interpreter 沙箱中执行 Python 代码，并复用沙箱状态。 |
| Browser CDP | 在阿里云 E2B 沙箱中启动 browsertool，并为 Playwright 暴露 CDP WebSocket 端点。 |
| BrowserUse Agent | 在阿里云 E2B 浏览器沙箱中运行 BrowserUse 智能体，支持会话复用。 |
| LangChain Browser Agent | 通过 LangChain 工具控制阿里云 E2B 浏览器沙箱，实现导航、截图与清理。 |
| Browser Studio | 提供面向阿里云 E2B 浏览器的 API 与前端产品外壳。 |
| PDF-to-Markdown LangChain | 构建文档转换模板，再通过 LangChain 智能体在阿里云 E2B 中将 PDF 转换为 Markdown。 |
| Mastra Code Agent | 通过沙箱、代码、文件、命令与清理工具，从 Mastra 智能体使用阿里云 E2B。 |