import { FormEvent, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Run = { run_id: string; status: string; result?: { title: string; url: string; screenshot_url: string }; error?: string };
type Event = { kind: string; at: string; error?: string; result?: Run["result"] };

const sample = "打开 https://example.com 并截取完整页面截图";

function App() {
  const [task, setTask] = useState(sample);
  const [run, setRun] = useState<Run>();
  const [events, setEvents] = useState<Event[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const source = useRef<EventSource>();

  useEffect(() => () => source.current?.close(), []);

  function watch(runId: string) {
    source.current?.close();
    const stream = new EventSource(`/api/runs/${runId}/events`);
    source.current = stream;
    stream.onmessage = () => undefined;
    ["run.queued", "sandbox.creating", "browser.starting", "sandbox.ready", "browser.connecting", "browser.screenshot", "run.completed", "run.failed", "run.stopped"].forEach((kind) => {
      stream.addEventListener(kind, (message) => {
        const event = JSON.parse((message as MessageEvent).data) as Event;
        setEvents((old) => [...old, event]);
        if (event.result) setRun((old) => old ? { ...old, status: "completed", result: event.result } : old);
        if (event.error) setRun((old) => old ? { ...old, status: "failed", error: event.error } : old);
        if (["run.completed", "run.failed", "run.stopped"].includes(event.kind)) stream.close();
      });
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true); setEvents([]); setRun(undefined);
    try {
      const response = await fetch("/api/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "无法创建任务");
      setRun(data); watch(data.run_id);
    } catch (error) { setRun({ run_id: "", status: "failed", error: error instanceof Error ? error.message : "请求失败" }); }
    finally { setSubmitting(false); }
  }

  async function stop() {
    if (!run?.run_id) return;
    await fetch(`/api/runs/${run.run_id}`, { method: "DELETE" });
    source.current?.close(); setRun({ ...run, status: "stopped" });
  }

  return <main>
    <section className="hero"><p className="eyebrow">E2B · PLAYWRIGHT · CDP</p><h1>Browser Studio</h1><p>在隔离的 E2B 浏览器中执行 URL 导航任务，并实时查看事件与截图。</p></section>
    <section className="panel"><form onSubmit={submit}><label htmlFor="task">浏览任务</label><textarea id="task" value={task} onChange={(e) => setTask(e.target.value)} placeholder="打开 https://example.com 并截图" required /><div className="actions"><button disabled={submitting}>{submitting ? "正在提交…" : "运行任务"}</button>{run && !["completed", "failed", "stopped"].includes(run.status) && <button className="secondary" type="button" onClick={stop}>停止并销毁</button>}</div></form></section>
    <section className="grid"><div className="panel"><h2>运行状态 <span>{run?.status ?? "等待提交"}</span></h2>{run?.error && <p className="error">{run.error}</p>}{run?.result && <dl><dt>页面标题</dt><dd>{run.result.title || "(无标题)"}</dd><dt>最终地址</dt><dd><a href={run.result.url} target="_blank">{run.result.url}</a></dd></dl>}<h2>事件</h2><ol className="events">{events.length ? events.map((event, index) => <li key={index}><b>{event.kind}</b><time>{new Date(event.at).toLocaleTimeString()}</time></li>) : <li>提交任务后会在此显示实时事件。</li>}</ol></div><div className="panel preview"><h2>页面截图</h2>{run?.result?.screenshot_url ? <img src={run.result.screenshot_url} alt="浏览器页面截图" /> : <p>截图将在任务完成后出现。</p>}</div></section>
  </main>;
}

createRoot(document.getElementById("root")!).render(<App />);
