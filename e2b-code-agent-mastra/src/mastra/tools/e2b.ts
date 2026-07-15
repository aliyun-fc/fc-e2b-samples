import { createTool } from '@mastra/core/tools';
import z from 'zod';
import { Sandbox } from '@e2b/code-interpreter';

// ---------------------------------------------------------------------------
// E2B connection config — read from env
// ---------------------------------------------------------------------------
const requiredEnv = (name: string) => {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Alibaba Cloud E2B requires ${name}`);
  }
  return value;
};

const E2B_DOMAIN = requiredEnv('E2B_DOMAIN');
const E2B_API_URL = requiredEnv('E2B_API_URL');
const E2B_TEMPLATE = process.env.E2B_TEMPLATE || 'code-interpreter-v1';

const connOpts = { domain: E2B_DOMAIN, apiUrl: E2B_API_URL };

// Many chat-model tool protocols stringify nested objects / numbers. Accept both.
const recordFromModel = z.union([
  z
    .record(z.unknown())
    .transform((o) =>
      Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v == null ? '' : String(v)])),
    ),
  z.string().transform((s) => {
    const t = s.trim();
    if (t === '' || t === '{}') return {};
    try {
      const parsed = JSON.parse(t) as unknown;
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
      return Object.fromEntries(
        Object.entries(parsed as Record<string, unknown>).map(([k, v]) => [
          k,
          v == null ? '' : String(v),
        ]),
      );
    } catch {
      return {};
    }
  }),
]);
const optionalRecordString = recordFromModel.optional();

const optionalNumber = z
  .union([z.number(), z.string(), z.null()])
  .optional()
  .transform((v): number | undefined => {
    if (v === undefined || v === null) return undefined;
    if (typeof v === 'number') return Number.isNaN(v) ? undefined : v;
    const n = Number(String(v).trim());
    return Number.isNaN(n) ? undefined : n;
  });

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------

const createSandboxInputSchema = z.object({
  metadata: optionalRecordString.describe(
    'Custom metadata for the sandbox (object or JSON string, e.g. {"purpose":"demo"}).',
  ),
  envs: optionalRecordString.describe(
    'Environment variables for the sandbox (object or JSON string, e.g. {"KEY":"v"}).',
  ),
  timeoutMs: optionalNumber.describe(
    'Timeout for the sandbox in milliseconds. @default 300_000',
  ),
});

export const createSandbox = createTool({
  id: 'createSandbox',
  description: 'Create an e2b sandbox',
  inputSchema: createSandboxInputSchema,
  outputSchema: z
    .object({ sandboxId: z.string() })
    .or(z.object({ error: z.string() })),
  execute: async (input) => {
    const { metadata, envs, timeoutMs } = createSandboxInputSchema.parse(input);
    try {
      const sandbox = await Sandbox.create(E2B_TEMPLATE, { metadata, envs, timeoutMs, ...connOpts });
      return { sandboxId: sandbox.sandboxId };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const killSandbox = createTool({
  id: 'killSandbox',
  description: 'Stop and release an e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string().describe('The sandboxId for the sandbox to stop'),
  }),
  outputSchema: z
    .object({ success: z.boolean(), sandboxId: z.string() })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId }) => {
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      await sandbox.kill();
      return { success: true, sandboxId };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

const runCodeInputSchema = z.object({
  sandboxId: z.string().describe('The sandboxId for the sandbox to run the code'),
  code: z.string().describe('The code to run in the sandbox'),
  runCodeOpts: z
    .object({
      language: z.enum(['python', 'javascript', 'typescript']).default('python'),
      envs: optionalRecordString,
      timeoutMs: optionalNumber,
      requestTimeoutMs: optionalNumber,
    })
    .optional()
    .describe('Run code options'),
});

export const runCode = createTool({
  id: 'runCode',
  description: 'Run code in an e2b sandbox',
  inputSchema: runCodeInputSchema,
  outputSchema: z
    .object({ execution: z.string() })
    .or(z.object({ error: z.string() })),
  execute: async (input) => {
    const { sandboxId, code, runCodeOpts } = runCodeInputSchema.parse(input);
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      const execution = await sandbox.runCode(code, runCodeOpts);
      return { execution: JSON.stringify(execution) };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const readFile = createTool({
  id: 'readFile',
  description: 'Read a file from the e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string(),
    path: z.string().describe('The path to the file to read'),
  }),
  outputSchema: z
    .object({ content: z.string(), path: z.string() })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId, path }) => {
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      const content = await sandbox.files.read(path);
      return { content, path };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const writeFile = createTool({
  id: 'writeFile',
  description: 'Write a single file to the e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string(),
    path: z.string().describe('The path where the file should be written'),
    content: z.string().describe('The content to write to the file'),
  }),
  outputSchema: z
    .object({ success: z.boolean(), path: z.string() })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId, path, content }) => {
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      await sandbox.files.write(path, content);
      return { success: true, path };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const writeFiles = createTool({
  id: 'writeFiles',
  description: 'Write multiple files to the e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string(),
    files: z.array(
      z.object({
        path: z.string(),
        data: z.string(),
      }),
    ),
  }),
  outputSchema: z
    .object({ success: z.boolean(), filesWritten: z.array(z.string()) })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId, files }) => {
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      for (const file of files) {
        await sandbox.files.write(file.path, file.data);
      }
      return { success: true, filesWritten: files.map((f) => f.path) };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const listFiles = createTool({
  id: 'listFiles',
  description: 'List files and directories in a path within the e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string(),
    path: z.string().default('/').describe('The directory path to list files from'),
  }),
  outputSchema: z
    .object({
      files: z.array(z.object({ name: z.string(), path: z.string(), isDirectory: z.boolean() })),
      path: z.string(),
    })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId, path: dirPath }) => {
    try {
      const dir = dirPath ?? '/';
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      const fileList = await sandbox.files.list(dir);
      return {
        files: fileList.map((file) => ({
          name: file.name,
          path: file.path,
          isDirectory: file.type === 'dir',
        })),
        path: dir,
      };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const deleteFile = createTool({
  id: 'deleteFile',
  description: 'Delete a file or directory from the e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string(),
    path: z.string().describe('The path to the file or directory to delete'),
  }),
  outputSchema: z
    .object({ success: z.boolean(), path: z.string() })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId, path }) => {
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      await sandbox.files.remove(path);
      return { success: true, path };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const createDirectory = createTool({
  id: 'createDirectory',
  description: 'Create a directory in the e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string(),
    path: z.string().describe('The path where the directory should be created'),
  }),
  outputSchema: z
    .object({ success: z.boolean(), path: z.string() })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId, path }) => {
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      await sandbox.files.makeDir(path);
      return { success: true, path };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const getFileInfo = createTool({
  id: 'getFileInfo',
  description: 'Get detailed information about a file or directory in the e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string(),
    path: z.string(),
  }),
  outputSchema: z
    .object({ name: z.string(), type: z.string().optional(), path: z.string(), size: z.number() })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId, path }) => {
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      const info = await sandbox.files.getInfo(path);
      return { name: info.name, type: info.type, path: info.path, size: info.size };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const checkFileExists = createTool({
  id: 'checkFileExists',
  description: 'Check if a file or directory exists in the e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string(),
    path: z.string().describe('The path to check for existence'),
  }),
  outputSchema: z
    .object({ exists: z.boolean(), path: z.string(), type: z.string().optional() })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId, path }) => {
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      try {
        const info = await sandbox.files.getInfo(path);
        return { exists: true, path, type: info.type };
      } catch {
        return { exists: false, path };
      }
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const getFileSize = createTool({
  id: 'getFileSize',
  description: 'Get the size of a file or directory in the e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string(),
    path: z.string(),
    humanReadable: z.boolean().default(false),
  }),
  outputSchema: z
    .object({
      size: z.number(),
      humanReadableSize: z.string().optional(),
      path: z.string(),
      type: z.string().optional(),
    })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId, path, humanReadable }) => {
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      const info = await sandbox.files.getInfo(path);

      let humanReadableSize: string | undefined;
      if (humanReadable) {
        const bytes = info.size;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        if (bytes === 0) {
          humanReadableSize = '0 B';
        } else {
          const i = Math.floor(Math.log(bytes) / Math.log(1024));
          humanReadableSize = `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
        }
      }

      return { size: info.size, humanReadableSize, path, type: info.type };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const watchDirectory = createTool({
  id: 'watchDirectory',
  description: 'Start watching a directory for file system changes in the e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string(),
    path: z.string().describe('The directory path to watch for changes'),
    recursive: z.boolean().default(false),
    watchDuration: z.number().default(30000).describe('How long to watch in milliseconds'),
  }),
  outputSchema: z
    .object({
      watchStarted: z.boolean(),
      path: z.string(),
      events: z.array(z.object({ type: z.string(), name: z.string(), timestamp: z.string() })),
    })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId, path, recursive, watchDuration }) => {
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      const events: Array<{ type: string; name: string; timestamp: string }> = [];

      const handle = await sandbox.files.watchDir(
        path,
        async (event) => {
          events.push({ type: String(event.type), name: event.name, timestamp: new Date().toISOString() });
        },
        { recursive },
      );

      await new Promise((resolve) => setTimeout(resolve, watchDuration));
      await handle.stop();

      return { watchStarted: true, path, events };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});

export const runCommand = createTool({
  id: 'runCommand',
  description: 'Run a shell command in the e2b sandbox',
  inputSchema: z.object({
    sandboxId: z.string(),
    command: z.string().describe('The shell command to execute'),
    workingDirectory: z.string().optional(),
    timeoutMs: z.number().default(30000),
    captureOutput: z.boolean().default(true),
  }),
  outputSchema: z
    .object({
      success: z.boolean(),
      exitCode: z.number(),
      stdout: z.string(),
      stderr: z.string(),
      command: z.string(),
      executionTime: z.number(),
    })
    .or(z.object({ error: z.string() })),
  execute: async ({ sandboxId, command, workingDirectory, timeoutMs }) => {
    try {
      const sandbox = await Sandbox.connect(sandboxId, connOpts);
      const startTime = Date.now();
      const result = await sandbox.commands.run(command, { cwd: workingDirectory, timeoutMs });
      return {
        success: result.exitCode === 0,
        exitCode: result.exitCode,
        stdout: result.stdout,
        stderr: result.stderr,
        command,
        executionTime: Date.now() - startTime,
      };
    } catch (e) {
      return { error: JSON.stringify(e) };
    }
  },
});
