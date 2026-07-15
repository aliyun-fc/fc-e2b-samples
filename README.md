# Alibaba Cloud E2B Sandbox Demos

All demos target Alibaba Cloud E2B. Every demo requires these E2B environment
variables in `.env`:

```ini
E2B_API_KEY=e2b_xxx
E2B_API_URL=https://api.us-west-1.e2b.fc.aliyuncs.com
E2B_DOMAIN=us-west-1.e2b.fc.aliyuncs.com
```

## Use Cases

| Demo | Use case |
| --- | --- |
| Code Interpreter | Execute Python code in an Alibaba Cloud E2B Code Interpreter sandbox and reuse sandbox state. |
| Browser CDP | Launch browsertool in an Alibaba Cloud E2B sandbox and expose a CDP WebSocket endpoint for Playwright. |
| BrowserUse Agent | Run BrowserUse agents in an Alibaba Cloud E2B browser sandbox, including session reuse. |
| LangChain Browser Agent | Control an Alibaba Cloud E2B browser sandbox through LangChain tools for navigation, screenshots, and cleanup. |
| Browser Studio | Provide an Alibaba Cloud E2B browser-focused API and frontend product shell. |
| PDF-to-Markdown LangChain | Build a document-conversion template, then use a LangChain agent to convert PDFs to Markdown in Alibaba Cloud E2B. |
| Mastra Code Agent | Use Alibaba Cloud E2B from a Mastra agent through sandbox, code, file, command, and cleanup tools. |
