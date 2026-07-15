import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { cva, type VariantProps } from "class-variance-authority";
import {
  Activity,
  ArrowUpRight,
  Bot,
  Camera,
  CheckCircle2,
  CircleStop,
  Clock3,
  Globe2,
  Loader2,
  Play,
  Radio,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  XCircle,
} from "lucide-react";
import "./style.css";
import { cn } from "./lib/utils";

type Run = {
  run_id: string;
  status: string;
  result?: { title: string; url: string; screenshot_url: string };
  error?: string;
};
type RunEvent = { kind: string; at: string; error?: string; result?: Run["result"] };

const sample = "打开 https://example.com 并截取完整页面截图";
const terminalStatuses = ["completed", "failed", "stopped"];
const listenedEvents = [
  "run.queued",
  "sandbox.creating",
  "browser.starting",
  "sandbox.ready",
  "browser.connecting",
  "browser.screenshot",
  "run.completed",
  "run.failed",
  "run.stopped",
];

const eventCopy: Record<string, { title: string; description: string }> = {
  "run.queued": { title: "任务已入队", description: "Run 已创建，等待调度浏览器沙箱。" },
  "sandbox.creating": { title: "创建沙箱", description: "E2B 正在准备隔离执行环境。" },
  "browser.starting": { title: "启动浏览器", description: "Playwright/CDP 浏览器实例正在启动。" },
  "sandbox.ready": { title: "沙箱就绪", description: "运行环境已可接收自动化指令。" },
  "browser.connecting": { title: "连接浏览器", description: "服务正在连接远端浏览器会话。" },
  "browser.screenshot": { title: "采集截图", description: "页面已访问，正在保存视觉结果。" },
  "run.completed": { title: "运行完成", description: "任务已成功结束，截图可预览。" },
  "run.failed": { title: "运行失败", description: "执行链路返回了错误。" },
  "run.stopped": { title: "已停止", description: "用户已停止并销毁运行资源。" },
};

const buttonVariants = cva(
  "inline-flex h-10 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-slate-800",
        secondary: "bg-secondary text-secondary-foreground hover:bg-slate-200",
        outline: "border border-input bg-background hover:bg-secondary",
        destructive: "bg-destructive text-destructive-foreground hover:bg-red-600",
        ghost: "hover:bg-secondary",
      },
      size: {
        default: "h-10 px-4",
        sm: "h-8 px-3 text-xs",
        icon: "h-10 w-10 px-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({
  className,
  variant,
  size,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cn("rounded-lg border bg-card text-card-foreground shadow-studio", className)}>{children}</section>;
}

function CardHeader({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("border-b px-5 py-4", className)}>{children}</div>;
}

function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return <h2 className={cn("text-sm font-semibold tracking-tight", className)}>{children}</h2>;
}

function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "success" | "warning" | "danger" | "info" }) {
  const tones = {
    neutral: "border-slate-200 bg-slate-50 text-slate-700",
    success: "border-emerald-200 bg-emerald-50 text-emerald-700",
    warning: "border-amber-200 bg-amber-50 text-amber-700",
    danger: "border-red-200 bg-red-50 text-red-700",
    info: "border-sky-200 bg-sky-50 text-sky-700",
  };
  return <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium", tones[tone])}>{children}</span>;
}

function statusTone(status?: string): "neutral" | "success" | "warning" | "danger" | "info" {
  if (!status) return "neutral";
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "stopped") return "warning";
  return "info";
}

function statusIcon(status?: string) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
  if (status === "failed") return <XCircle className="h-4 w-4 text-red-600" />;
  if (status === "stopped") return <CircleStop className="h-4 w-4 text-amber-600" />;
  if (status) return <Loader2 className="h-4 w-4 animate-spin text-sky-600" />;
  return <Clock3 className="h-4 w-4 text-muted-foreground" />;
}

function App() {
  const [task, setTask] = useState(sample);
  const [run, setRun] = useState<Run>();
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const source = useRef<EventSource>();

  useEffect(() => () => source.current?.close(), []);

  const isRunning = Boolean(run && !terminalStatuses.includes(run.status));
  const progress = useMemo(() => {
    if (!run) return 0;
    if (run.status === "completed") return 100;
    if (run.status === "failed" || run.status === "stopped") return Math.max(12, events.length * 12);
    return Math.min(92, Math.max(12, events.length * 14));
  }, [events.length, run]);

  function watch(runId: string) {
    source.current?.close();
    const stream = new EventSource(`/api/runs/${runId}/events`);
    source.current = stream;
    stream.onmessage = () => undefined;
    listenedEvents.forEach((kind) => {
      stream.addEventListener(kind, (message) => {
        const event = JSON.parse((message as MessageEvent).data) as RunEvent;
        setEvents((old) => [...old, event]);
        if (event.result) setRun((old) => (old ? { ...old, status: "completed", result: event.result } : old));
        if (event.error) setRun((old) => (old ? { ...old, status: "failed", error: event.error } : old));
        if (terminalStatuses.includes(event.kind.replace("run.", "")) || ["run.completed", "run.failed", "run.stopped"].includes(event.kind)) {
          stream.close();
        }
      });
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setEvents([]);
    setRun(undefined);
    try {
      const response = await fetch("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "无法创建任务");
      setRun(data);
      watch(data.run_id);
    } catch (error) {
      setRun({ run_id: "", status: "failed", error: error instanceof Error ? error.message : "请求失败" });
    } finally {
      setSubmitting(false);
    }
  }

  async function stop() {
    if (!run?.run_id) return;
    await fetch(`/api/runs/${run.run_id}`, { method: "DELETE" });
    source.current?.close();
    setRun({ ...run, status: "stopped" });
  }

  return (
    <main className="min-h-screen">
      <div className="border-b bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-950 text-white">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight">Browser Studio</h1>
              <p className="text-sm text-muted-foreground">E2B browser automation demo</p>
            </div>
          </div>
          <div className="hidden items-center gap-2 sm:flex">
            <Badge tone="info">Playwright CDP</Badge>
            <Badge tone="success">SSE Live</Badge>
          </div>
        </div>
      </div>

      <div className="mx-auto grid max-w-7xl gap-5 px-5 py-6 lg:grid-cols-[420px_1fr]">
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>任务控制台</CardTitle>
                <TerminalSquare className="h-4 w-4 text-muted-foreground" />
              </div>
            </CardHeader>
            <form onSubmit={submit} className="space-y-4 p-5">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="task">
                  浏览任务
                </label>
                <textarea
                  id="task"
                  value={task}
                  onChange={(event) => setTask(event.target.value)}
                  placeholder="打开 https://example.com 并截图"
                  required
                  className="min-h-36 w-full resize-y rounded-md border border-input bg-white px-3 py-3 text-sm leading-6 shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Button className="col-span-2 sm:col-span-1" disabled={submitting || isRunning}>
                  {submitting || isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  {submitting ? "提交中" : isRunning ? "运行中" : "运行任务"}
                </Button>
                <Button
                  className="col-span-2 sm:col-span-1"
                  disabled={!isRunning}
                  type="button"
                  variant="outline"
                  onClick={stop}
                >
                  <CircleStop className="h-4 w-4" />
                  停止并销毁
                </Button>
              </div>
            </form>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>运行状态</CardTitle>
                <Badge tone={statusTone(run?.status)}>{run?.status ?? "idle"}</Badge>
              </div>
            </CardHeader>
            <div className="space-y-5 p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border bg-secondary">{statusIcon(run?.status)}</div>
                <div>
                  <p className="text-sm font-medium">{run ? "Run 已创建" : "等待提交任务"}</p>
                  <p className="text-xs text-muted-foreground">{run?.run_id ? `ID ${run.run_id}` : "输入任务后将启动隔离浏览器"}</p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>执行进度</span>
                  <span>{progress}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-secondary">
                  <div className="h-full rounded-full bg-sky-500 transition-all" style={{ width: `${progress}%` }} />
                </div>
              </div>
              {run?.error ? <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{run.error}</p> : null}
            </div>
          </Card>

          <div className="grid grid-cols-3 gap-3">
            <Metric icon={<ShieldCheck className="h-4 w-4" />} label="Sandbox" value="Isolated" />
            <Metric icon={<Radio className="h-4 w-4" />} label="Stream" value={`${events.length} events`} />
            <Metric icon={<Camera className="h-4 w-4" />} label="Output" value={run?.result ? "Ready" : "Pending"} />
          </div>
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle>页面截图</CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">任务完成后显示远端浏览器采集的完整页面结果。</p>
                </div>
                {run?.result?.url ? (
                  <a
                    className={cn(buttonVariants({ variant: "secondary", size: "sm" }))}
                    href={run.result.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    打开页面
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </a>
                ) : null}
              </div>
            </CardHeader>
            <div className="p-5">
              {run?.result?.screenshot_url ? (
                <div className="overflow-hidden rounded-lg border bg-slate-100">
                  <img className="block w-full" src={run.result.screenshot_url} alt="浏览器页面截图" />
                </div>
              ) : (
                <div className="flex min-h-[360px] items-center justify-center rounded-lg border border-dashed bg-slate-50 p-8 text-center">
                  <div className="max-w-sm space-y-3">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-white shadow-sm">
                      <Globe2 className="h-6 w-6 text-sky-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">截图预览区</p>
                      <p className="mt-1 text-sm text-muted-foreground">运行一个 URL 导航任务后，浏览器截图会在这里呈现。</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>

          <div className="grid gap-5 xl:grid-cols-[1fr_340px]">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>实时事件</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </div>
              </CardHeader>
              <ol className="divide-y">
                {events.length ? (
                  events.map((event, index) => <EventRow event={event} key={`${event.kind}-${event.at}-${index}`} />)
                ) : (
                  <li className="p-5 text-sm text-muted-foreground">提交任务后会在此显示 sandbox、browser 和 run 事件。</li>
                )}
              </ol>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>结果详情</CardTitle>
                  <Sparkles className="h-4 w-4 text-muted-foreground" />
                </div>
              </CardHeader>
              <div className="space-y-4 p-5">
                <ResultField label="页面标题" value={run?.result?.title || (run?.result ? "(无标题)" : "等待结果")} />
                <ResultField label="最终地址" value={run?.result?.url ?? "等待结果"} link={run?.result?.url} />
                <ResultField label="截图地址" value={run?.result?.screenshot_url ?? "等待结果"} link={run?.result?.screenshot_url} />
              </div>
            </Card>
          </div>
        </div>
      </div>
    </main>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-white p-3 shadow-sm">
      <div className="mb-2 text-muted-foreground">{icon}</div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold">{value}</p>
    </div>
  );
}

function EventRow({ event }: { event: RunEvent }) {
  const copy = eventCopy[event.kind] ?? { title: event.kind, description: "收到后端运行事件。" };
  const tone = event.kind.includes("failed") ? "danger" : event.kind.includes("completed") ? "success" : "info";
  return (
    <li className="flex gap-3 p-5">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary">
        {event.kind.includes("failed") ? <XCircle className="h-4 w-4 text-red-600" /> : <Activity className="h-4 w-4 text-sky-600" />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium">{copy.title}</p>
          <Badge tone={tone}>{event.kind}</Badge>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{event.error ?? copy.description}</p>
        <time className="mt-2 block text-xs text-muted-foreground">{new Date(event.at).toLocaleTimeString()}</time>
      </div>
    </li>
  );
}

function ResultField({ label, value, link }: { label: string; value: string; link?: string }) {
  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      {link ? (
        <a className="mt-1 block break-all text-sm font-medium text-sky-700 hover:underline" href={link} target="_blank" rel="noreferrer">
          {value}
        </a>
      ) : (
        <p className="mt-1 break-all text-sm font-medium">{value}</p>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
