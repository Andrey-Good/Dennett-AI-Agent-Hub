import * as React from "react";

import ReactFlow, {
  Background,
  BackgroundVariant,
  Connection,
  Edge,
  Handle,
  MarkerType,
  Node,
  NodeProps,
  Position,
  ReactFlowInstance,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

import {
  ArrowLeft,
  ChevronDown,
  Circle,
  Download,
  FileUp,
  Layers,
  Play,
  Plus,
  Search,
  Settings2,
  Share2,
  Sparkles,
  Trash2,
  Wand2,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Node Builder (ReactFlow) redesigned to match the provided architecture HTML/CSS:
 * - Floating left "Outliner" panel (mindmap-like).
 * - Floating right "Tools / Settings" panel with sections: Timeout, Retry Policy, Commentary, Main, Outputs.
 * - Dotted dark canvas + pill toolbars similar to the reference screenshots.
 *
 * Single-file implementation to make integration easy:
 * Replace your existing `frontend/src/views/WorkflowBuilderPage.tsx` with this file.
 */

/* ----------------------------- Types & Models ----------------------------- */

type NodeKind = "llm" | "prompt" | "tool" | "output" | "note";

type Port = {
  id: string;
  label: string;
  color?: string; // for small dot / hint
};

type OutputSpec = {
  id: string;
  name: string;
  mode: "var" | "edges";
};

type AgentNodeConfig = {
  // Common
  timeoutSec?: number;
  retry?: number;
  commentary?: string;

  // LLM
  model?: string;
  takeOutside?: boolean;

  // Prompt-like
  systemInstruction?: string;
  prompt?: string;
  chatHistory?: string;

  // Tool-like
  toolName?: string;
  toolDescription?: string;

  // Output
  outputKey?: string;

  // Outputs section (UI like in the provided design)
  outputs?: OutputSpec[];
};

export type AgentNodeData = {
  kind: NodeKind;
  title: string;
  tag?: string; // small pill next to title
  description?: string; // short text in the card
  inputs: Port[];
  outputs: Port[];
  config: AgentNodeConfig;
};

type ContextMenuState =
  | { open: false }
  | { open: true; clientX: number; clientY: number; x: number; y: number };

/* --------------------------------- Helpers -------------------------------- */

function uid(prefix = "n") {
  // Works in modern browsers + Tauri. Falls back safely.
  const c: any = globalThis.crypto;
  const id = typeof c?.randomUUID === "function" ? c.randomUUID() : `${Date.now()}-${Math.random()}`;
  return `${prefix}-${id}`;
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function truncate(str: string, max = 110) {
  if (str.length <= max) return str;
  return `${str.slice(0, Math.max(0, max - 1))}…`;
}

function getNodeKindLabel(kind: NodeKind) {
  switch (kind) {
    case "llm":
      return "LLM";
    case "prompt":
      return "Prompt";
    case "tool":
      return "Tool";
    case "output":
      return "Output";
    case "note":
      return "Note";
    default:
      return "Node";
  }
}

function getKindDot(kind: NodeKind) {
  switch (kind) {
    case "llm":
      return "#7c3aed"; // purple
    case "prompt":
      return "#22c55e"; // green
    case "tool":
      return "#f59e0b"; // amber
    case "output":
      return "#3b82f6"; // blue
    case "note":
      return "#94a3b8"; // slate
    default:
      return "#94a3b8";
  }
}

/* ------------------------------- Node Renderer ------------------------------ */

function AgentNodeCard({ data, selected }: NodeProps<AgentNodeData>) {
  const headerHeight = 44;
  const rowGap = 22;

  return (
    <div
      className={cn(
        "min-w-[240px] max-w-[300px] rounded-[18px] border bg-[#161b22] shadow-[0_25px_80px_rgba(0,0,0,0.65)]",
        selected ? "border-[#4054b4]" : "border-[#30363d]",
      )}
    >
      <div
        className={cn(
          "flex items-start justify-between gap-3 border-b px-4 py-3",
          selected ? "border-[#4054b4]/50" : "border-[#30363d]",
        )}
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: getKindDot(data.kind) }} />
            <div className="truncate text-[12px] font-semibold text-[#e6edf3]">{data.title}</div>
          </div>

          <div className="mt-0.5 flex flex-wrap items-center gap-2">
            <div className="text-[10px] text-[#e6edf3]/55">{getNodeKindLabel(data.kind)}</div>
            {data.tag ? (
              <div className="inline-flex items-center gap-1 rounded-full border border-[#30363d] bg-[#0d1117] px-2 py-0.5 text-[10px] text-[#e6edf3]/75">
                <Circle className="h-2.5 w-2.5 fill-[#e6edf3]/65 text-[#e6edf3]/65" />
                <span className="truncate">{data.tag}</span>
              </div>
            ) : null}
          </div>
        </div>

        <div className="flex items-center gap-1">
          {data.outputs.length > 0 ? (
            <div className="rounded-full border border-[#30363d] bg-[#0d1117] px-2 py-0.5 text-[10px] text-[#e6edf3]/70">
              out: {data.outputs.length}
            </div>
          ) : null}
        </div>
      </div>

      <div className="px-4 py-3 text-[11px] leading-relaxed text-[#e6edf3]/75">
        <div className="space-y-2">
          {data.description ? <div className="text-[#e6edf3]/75">{data.description}</div> : null}

          <NodeCardPreview data={data} />

          {(data.inputs.length > 0 || data.outputs.length > 0) && (
            <div className="mt-1 grid grid-cols-2 gap-2 text-[10px] text-[#e6edf3]/55">
              <div className="space-y-1">
                {data.inputs.map((p) => (
                  <div key={p.id} className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: p.color ?? "rgba(230,237,243,0.55)" }} />
                    <span className="truncate">{p.label}</span>
                  </div>
                ))}
              </div>

              <div className="space-y-1 text-right">
                {data.outputs.map((p) => (
                  <div key={p.id} className="flex items-center justify-end gap-2">
                    <span className="truncate">{p.label}</span>
                    <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: p.color ?? "rgba(230,237,243,0.55)" }} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* INPUT handles (left) */}
      {data.inputs.map((p, idx) => (
        <Handle
          key={`in-${p.id}`}
          id={p.id}
          type="target"
          position={Position.Left}
          className="!h-2.5 !w-2.5 !border !border-[#30363d] !bg-[#0d1117]"
          style={{ top: headerHeight + 18 + idx * rowGap }}
        />
      ))}

      {/* OUTPUT handles (right) */}
      {data.outputs.map((p, idx) => (
        <Handle
          key={`out-${p.id}`}
          id={p.id}
          type="source"
          position={Position.Right}
          className="!h-2.5 !w-2.5 !border !border-[#30363d] !bg-[#0d1117]"
          style={{ top: headerHeight + 18 + idx * rowGap }}
        />
      ))}
    </div>
  );
}

function NodeCardPreview({ data }: { data: AgentNodeData }) {
  const cfg = data.config;

  if (data.kind === "llm") {
    return (
      <div className="rounded-xl border border-[#30363d] bg-[#0d1117] px-3 py-2">
        <div className="text-[10px] text-[#e6edf3]/55">Model</div>
        <div className="mt-0.5 text-[11px] text-[#e6edf3]/85">{cfg.model ?? "Select model…"}</div>
      </div>
    );
  }

  if (data.kind === "prompt") {
    const value = cfg.systemInstruction ?? cfg.prompt ?? cfg.chatHistory ?? "";
    return (
      <div className="rounded-xl border border-[#30363d] bg-[#0d1117] px-3 py-2 text-[11px] text-[#e6edf3]/80">
        {value ? truncate(value, 120) : "Type your prompt…"}
      </div>
    );
  }

  if (data.kind === "tool") {
    return (
      <div className="rounded-xl border border-[#30363d] bg-[#0d1117] px-3 py-2">
        <div className="text-[10px] text-[#e6edf3]/55">Tool</div>
        <div className="mt-0.5 text-[11px] text-[#e6edf3]/85">
          {cfg.toolName ?? "Tool name"}
        </div>
      </div>
    );
  }

  if (data.kind === "output") {
    return (
      <div className="rounded-xl border border-[#30363d] bg-[#0d1117] px-3 py-2">
        <div className="text-[10px] text-[#e6edf3]/55">Output key</div>
        <div className="mt-0.5 text-[11px] text-[#e6edf3]/85">{cfg.outputKey ?? "answer"}</div>
      </div>
    );
  }

  return null;
}

const nodeTypes = {
  agent: AgentNodeCard,
};

/* --------------------------- Initial Graph (Demo) --------------------------- */

const initialNodes: Node<AgentNodeData>[] = [
  {
    id: "sys",
    type: "agent",
    position: { x: 80, y: 160 },
    data: {
      kind: "prompt",
      title: "System Instruction",
      tag: "var: Системный_промт",
      description: "System rules / role for the model.",
      inputs: [],
      outputs: [{ id: "out", label: "system", color: "#22c55e" }],
      config: {
        systemInstruction:
          "Ты — помощник. Возвращай ответ кратко и по делу. Если не хватает данных — скажи, что уточнить.",
        timeoutSec: 60,
        retry: 1,
        commentary: "",
        outputs: [{ id: uid("o"), name: "Системный_промт", mode: "var" }],
      },
    },
  },
  {
    id: "history",
    type: "agent",
    position: { x: 80, y: 360 },
    data: {
      kind: "prompt",
      title: "Chat History",
      tag: "context",
      description: "Conversation context / memory slice.",
      inputs: [],
      outputs: [{ id: "out", label: "history", color: "#22c55e" }],
      config: {
        chatHistory: "Пользователь: ...\nАссистент: ...",
        timeoutSec: 60,
        retry: 1,
        outputs: [{ id: uid("o"), name: "history", mode: "var" }],
      },
    },
  },
  {
    id: "llm",
    type: "agent",
    position: { x: 420, y: 250 },
    data: {
      kind: "llm",
      title: "llm_local",
      tag: "DeepSeek-V3.1-Terminus-IQ4",
      description: "Takes system prompt + history and generates response.",
      inputs: [
        { id: "system", label: "system", color: "#22c55e" },
        { id: "history", label: "history", color: "#22c55e" },
      ],
      outputs: [{ id: "text", label: "text", color: "#7c3aed" }],
      config: {
        model: "DeepSeek-V3.1-Terminus-IQ4",
        takeOutside: false,
        timeoutSec: 60,
        retry: 1,
        commentary: "Берет файл расписания и ищет в нем конфликты (пример из макета).",
        outputs: [
          { id: uid("o"), name: "ответ_пользователю", mode: "var" },
          { id: uid("o"), name: "Conflict", mode: "var" },
        ],
      },
    },
  },
  {
    id: "out",
    type: "agent",
    position: { x: 780, y: 270 },
    data: {
      kind: "output",
      title: "Ответ пользователю",
      tag: "final",
      description: "Final output that goes back to the user.",
      inputs: [{ id: "in", label: "in", color: "#3b82f6" }],
      outputs: [],
      config: {
        outputKey: "ответ_пользователю",
        timeoutSec: 60,
        retry: 0,
        outputs: [{ id: uid("o"), name: "ответ_пользователю", mode: "var" }],
      },
    },
  },
];

const initialEdges: Edge[] = [
  {
    id: "e-sys-llm",
    source: "sys",
    sourceHandle: "out",
    target: "llm",
    targetHandle: "system",
    type: "smoothstep",
    style: { stroke: "rgba(230,237,243,0.28)", strokeWidth: 1.2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(230,237,243,0.35)" },
  },
  {
    id: "e-hist-llm",
    source: "history",
    sourceHandle: "out",
    target: "llm",
    targetHandle: "history",
    type: "smoothstep",
    style: { stroke: "rgba(230,237,243,0.28)", strokeWidth: 1.2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(230,237,243,0.35)" },
  },
  {
    id: "e-llm-out",
    source: "llm",
    sourceHandle: "text",
    target: "out",
    targetHandle: "in",
    type: "smoothstep",
    style: { stroke: "rgba(230,237,243,0.28)", strokeWidth: 1.2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(230,237,243,0.35)" },
  },
];

/* --------------------------------- Templates -------------------------------- */

type NodeTemplate = {
  title: string;
  description: string;
  kind: NodeKind;
  makeData: () => AgentNodeData;
};

const templates: NodeTemplate[] = [
  {
    title: "LLM",
    description: "Model execution node (timeout, retries, outputs).",
    kind: "llm",
    makeData: () => ({
      kind: "llm",
      title: "llm_local",
      tag: "Model",
      description: "LLM node. Connect prompts and get text.",
      inputs: [
        { id: "system", label: "system", color: "#22c55e" },
        { id: "history", label: "history", color: "#22c55e" },
      ],
      outputs: [{ id: "text", label: "text", color: "#7c3aed" }],
      config: {
        model: "DeepSeek-V3.1-Terminus-IQ4",
        takeOutside: false,
        timeoutSec: 60,
        retry: 1,
        outputs: [{ id: uid("o"), name: "answer", mode: "var" }],
      },
    }),
  },
  {
    title: "Prompt",
    description: "System instruction / user prompt / history.",
    kind: "prompt",
    makeData: () => ({
      kind: "prompt",
      title: "Prompt",
      tag: "var",
      description: "Text / prompt source.",
      inputs: [],
      outputs: [{ id: "out", label: "out", color: "#22c55e" }],
      config: {
        systemInstruction: "",
        prompt: "",
        timeoutSec: 60,
        retry: 0,
        outputs: [{ id: uid("o"), name: "prompt", mode: "var" }],
      },
    }),
  },
  {
    title: "Tool",
    description: "Tool wrapper (function / agent tool call).",
    kind: "tool",
    makeData: () => ({
      kind: "tool",
      title: "Tool Node",
      tag: "tool",
      description: "Represents a tool/function call.",
      inputs: [{ id: "in", label: "in", color: "#f59e0b" }],
      outputs: [{ id: "result", label: "result", color: "#f59e0b" }],
      config: {
        toolName: "schedule_parser",
        toolDescription: "Берет файл расписания и ищет конфликты.",
        timeoutSec: 60,
        retry: 1,
        outputs: [{ id: uid("o"), name: "result", mode: "var" }],
      },
    }),
  },
  {
    title: "Output",
    description: "Final result / export to UI.",
    kind: "output",
    makeData: () => ({
      kind: "output",
      title: "Output",
      tag: "final",
      description: "Terminal output.",
      inputs: [{ id: "in", label: "in", color: "#3b82f6" }],
      outputs: [],
      config: {
        outputKey: "answer",
        timeoutSec: 60,
        retry: 0,
        outputs: [{ id: uid("o"), name: "answer", mode: "var" }],
      },
    }),
  },
  {
    title: "Note",
    description: "Sticky note / documentation node.",
    kind: "note",
    makeData: () => ({
      kind: "note",
      title: "Note",
      tag: "docs",
      description: "Write anything to document your workflow.",
      inputs: [],
      outputs: [],
      config: {
        commentary: "Some note…",
        timeoutSec: 0,
        retry: 0,
        outputs: [],
      },
    }),
  },
];

/* -------------------------------- Main Page -------------------------------- */

export function WorkflowBuilderPage() {
  return (
    <ReactFlowProvider>
      <WorkflowBuilderInner />
    </ReactFlowProvider>
  );
}

function WorkflowBuilderInner() {
  const [nodes, setNodes, onNodesChange] = useNodesState<AgentNodeData>(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const [selectedNodeId, setSelectedNodeId] = React.useState<string | null>(null);
  const selectedNode = React.useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) ?? null,
    [nodes, selectedNodeId],
  );

  const [leftOpen, setLeftOpen] = React.useState(true);
  const [rightOpen, setRightOpen] = React.useState(true);

  const [menu, setMenu] = React.useState<ContextMenuState>({ open: false });
  const [rf, setRf] = React.useState<ReactFlowInstance | null>(null);

  const wrapperRef = React.useRef<HTMLDivElement | null>(null);

  const fileInputRef = React.useRef<HTMLInputElement | null>(null);

  const defaultEdgeOptions = React.useMemo<Partial<Edge>>(
    () => ({
      type: "smoothstep",
      style: { stroke: "rgba(230,237,243,0.28)", strokeWidth: 1.2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(230,237,243,0.35)" },
    }),
    [],
  );

  const addNodeFromTemplate = React.useCallback(
    (tpl: NodeTemplate, position?: { x: number; y: number }) => {
      const id = uid("node");
      const newNode: Node<AgentNodeData> = {
        id,
        type: "agent",
        position: position ?? { x: 120, y: 120 },
        data: tpl.makeData(),
      };

      setNodes((nds) => nds.concat(newNode));
      setSelectedNodeId(id);
    },
    [setNodes],
  );

  const screenToFlow = React.useCallback(
    (clientX: number, clientY: number) => {
      const anyRf = rf as any;
      if (anyRf?.screenToFlowPosition) return anyRf.screenToFlowPosition({ x: clientX, y: clientY });
      if (anyRf?.project) return anyRf.project({ x: clientX, y: clientY });
      return { x: clientX, y: clientY };
    },
    [rf],
  );

  const focusNode = React.useCallback(
    (nodeId: string) => {
      const n = nodes.find((x) => x.id === nodeId);
      if (!n) return;

      const anyRf = rf as any;
      // Center on node (approx).
      if (anyRf?.setCenter) {
        anyRf.setCenter(n.position.x + 140, n.position.y + 80, { zoom: 1.05, duration: 250 });
      } else if (anyRf?.fitView) {
        anyRf.fitView({ nodes: [n], duration: 250, padding: 0.25 });
      }
    },
    [nodes, rf],
  );

  const onConnect = React.useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            ...defaultEdgeOptions,
          },
          eds,
        ),
      );
    },
    [defaultEdgeOptions, setEdges],
  );

  const updateNodeData = React.useCallback(
    (nodeId: string, updater: (prev: AgentNodeData) => AgentNodeData) => {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id !== nodeId) return n;
          return { ...n, data: updater(n.data) };
        }),
      );
    },
    [setNodes],
  );

  const deleteSelectedNode = React.useCallback(() => {
    if (!selectedNodeId) return;
    setNodes((nds) => nds.filter((n) => n.id !== selectedNodeId));
    setEdges((eds) => eds.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId));
    setSelectedNodeId(null);
  }, [selectedNodeId, setEdges, setNodes]);

  const exportJson = React.useCallback(() => {
    const payload = {
      version: 1,
      nodes,
      edges,
    };

    const json = JSON.stringify(payload, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "workflow.json";
    a.click();

    setTimeout(() => URL.revokeObjectURL(url), 500);
  }, [edges, nodes]);

  const importJson = React.useCallback(async (file: File) => {
    const text = await file.text();
    const parsed = JSON.parse(text) as { nodes: Node<AgentNodeData>[]; edges: Edge[] };
    if (!parsed?.nodes || !parsed?.edges) return;

    setNodes(parsed.nodes);
    setEdges(parsed.edges);
    setSelectedNodeId(null);

    const anyRf = rf as any;
    if (anyRf?.fitView) {
      setTimeout(() => anyRf.fitView({ duration: 250, padding: 0.2 }), 50);
    }
  }, [rf, setEdges, setNodes]);

  const zoomIn = React.useCallback(() => {
    const anyRf = rf as any;
    anyRf?.zoomIn?.({ duration: 180 });
  }, [rf]);

  const zoomOut = React.useCallback(() => {
    const anyRf = rf as any;
    anyRf?.zoomOut?.({ duration: 180 });
  }, [rf]);

  const fit = React.useCallback(() => {
    const anyRf = rf as any;
    anyRf?.fitView?.({ duration: 220, padding: 0.2 });
  }, [rf]);

  const [search, setSearch] = React.useState("");

  const filteredNodes = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return nodes;
    return nodes.filter((n) => (n.data.title ?? "").toLowerCase().includes(q) || (n.data.tag ?? "").toLowerCase().includes(q));
  }, [nodes, search]);

  return (
    <div className="h-full">
      <div
        ref={wrapperRef}
        className="relative h-full overflow-hidden rounded-[22px] border border-[hsl(var(--tp-border))]"
        style={{
          backgroundColor: "#0d1117",
        }}
      >
        {/* Top toolbar (left / center / right) */}
        <div className="absolute left-4 top-4 z-30 flex items-center gap-2">
          <TopPill>
            <Sparkles className="h-4 w-4" />
            Workflow
          </TopPill>
          <TopPill>Edit</TopPill>
          <TopPill>Help</TopPill>
        </div>

        <div className="absolute left-1/2 top-4 z-30 flex -translate-x-1/2 items-center gap-2">
          <IconPill>
            <ArrowLeft className="h-4 w-4" />
          </IconPill>
          <TopPill className="min-w-[210px] justify-center">
            my_agent_generation_v2
          </TopPill>
        </div>

        <div className="absolute right-4 top-4 z-30 flex items-center gap-2">
          <TopPill className="gap-2">
            <Play className="h-4 w-4" />
            Run
            <ChevronDown className="h-4 w-4 opacity-70" />
          </TopPill>

          <IconButton title="Export JSON" onClick={exportJson}>
            <Download className="h-4 w-4" />
          </IconButton>

          <IconButton
            title="Import JSON"
            onClick={() => fileInputRef.current?.click()}
          >
            <FileUp className="h-4 w-4" />
          </IconButton>

          <IconPill>
            <Settings2 className="h-4 w-4" />
          </IconPill>

          <TopPill className="bg-white text-black hover:bg-white/90">
            <Share2 className="h-4 w-4" />
            Share
          </TopPill>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="application/json"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (!f) return;
            void importJson(f);
            e.target.value = "";
          }}
        />

        {/* Floating left panel (Outliner) */}
        {leftOpen ? (
          <div className="absolute left-4 top-24 z-30 w-[300px]">
            <div className="overflow-hidden rounded-[18px] border border-[#30363d] bg-[#161b22] shadow-[0_25px_80px_rgba(0,0,0,0.65)]">
              <div className="flex items-center justify-between border-b border-[#30363d] px-3 py-2">
                <div>
                  <div className="text-[12px] font-semibold text-[#e6edf3]">Outliner</div>
                  <div className="text-[10px] text-[#e6edf3]/45">Nodes & structure</div>
                </div>

                <button
                  className="inline-flex h-8 w-8 items-center justify-center rounded-[12px] border border-[#30363d] bg-[#0d1117] text-[#e6edf3]/75 hover:text-[#e6edf3]"
                  onClick={() => setLeftOpen(false)}
                  title="Hide"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="p-3">
                <div className="flex items-center gap-2 rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2">
                  <Search className="h-4 w-4 text-[#e6edf3]/55" />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="h-6 w-full bg-transparent text-[11px] text-[#e6edf3]/85 outline-none placeholder:text-[#e6edf3]/35"
                    placeholder="Search nodes…"
                  />
                </div>

                <div className="mt-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="text-[10px] font-semibold text-[#e6edf3]/70">
                      Nodes ({filteredNodes.length})
                    </div>

                    <button
                      className="inline-flex items-center gap-2 rounded-[12px] border border-[#30363d] bg-[#0d1117] px-2 py-1 text-[10px] font-semibold text-[#e6edf3]/80 hover:text-[#e6edf3]"
                      onClick={(e) => {
                        // Add a node near left panel.
                        e.stopPropagation();
                        addNodeFromTemplate(templates[0], { x: 220, y: 120 });
                      }}
                      title="Add node"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Add
                    </button>
                  </div>

                  <div className="max-h-[420px] space-y-1 overflow-auto pr-1">
                    {filteredNodes.map((n) => (
                      <button
                        key={n.id}
                        className={cn(
                          "group flex w-full items-center justify-between gap-2 rounded-[14px] border px-3 py-2 text-left text-[11px] transition",
                          n.id === selectedNodeId
                            ? "border-[#4054b4] bg-[#0d1117]"
                            : "border-[#30363d] bg-[#0d1117] hover:border-[#4054b4]/70",
                        )}
                        onClick={() => {
                          setSelectedNodeId(n.id);
                          focusNode(n.id);
                        }}
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: getKindDot(n.data.kind) }} />
                            <div className="truncate font-semibold text-[#e6edf3]/90">{n.data.title}</div>
                          </div>
                          <div className="mt-0.5 truncate text-[10px] text-[#e6edf3]/45">
                            {n.data.tag ?? getNodeKindLabel(n.data.kind)}
                          </div>
                        </div>

                        <div className="text-[10px] text-[#e6edf3]/40 group-hover:text-[#e6edf3]/70">
                          →
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="mt-3 border-t border-[#30363d] pt-3">
                  <div className="text-[10px] font-semibold text-[#e6edf3]/70">Library</div>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    {templates.slice(0, 4).map((tpl) => (
                      <button
                        key={tpl.title}
                        className="rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2 text-left hover:border-[#4054b4]/70"
                        onClick={() => addNodeFromTemplate(tpl, { x: 260, y: 220 })}
                      >
                        <div className="text-[11px] font-semibold text-[#e6edf3]/90">{tpl.title}</div>
                        <div className="mt-0.5 text-[10px] text-[#e6edf3]/45">{tpl.description}</div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="absolute left-4 top-24 z-30">
            <IconButton title="Show Outliner" onClick={() => setLeftOpen(true)}>
              <Layers className="h-4 w-4" />
            </IconButton>
          </div>
        )}

        {/* Floating right panel (Tools / Settings) */}
        {rightOpen ? (
          <div className="absolute right-4 top-24 z-30 w-[360px]">
            <InspectorPanel
              node={selectedNode}
              onClose={() => setSelectedNodeId(null)}
              onHide={() => setRightOpen(false)}
              onDelete={deleteSelectedNode}
              onUpdate={(updater) => {
                if (!selectedNode) return;
                updateNodeData(selectedNode.id, updater);
              }}
            />
          </div>
        ) : (
          <div className="absolute right-4 top-24 z-30">
            <IconButton title="Show Settings" onClick={() => setRightOpen(true)}>
              <Settings2 className="h-4 w-4" />
            </IconButton>
          </div>
        )}

        {/* Bottom prompt bar */}
        <div className="absolute bottom-4 left-1/2 z-30 w-[520px] -translate-x-1/2">
          <div className="flex items-center gap-2 rounded-[18px] border border-[#30363d] bg-[#161b22] px-3 py-2 shadow-[0_25px_80px_rgba(0,0,0,0.65)]">
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl border border-[#30363d] bg-[#0d1117] text-[#e6edf3]/80">
              <Sparkles className="h-4 w-4" />
            </div>

            <input
              className="h-9 w-full bg-transparent text-[11px] text-[#e6edf3]/85 outline-none placeholder:text-[#e6edf3]/35"
              placeholder="Describe your task, then connect nodes to build an agent…"
            />

            <button
              className="flex h-9 items-center gap-2 rounded-2xl bg-[#4054b4] px-3 text-[11px] font-semibold text-white shadow-[0_10px_30px_rgba(64,84,180,0.35)] hover:brightness-110"
              onClick={() => {
                // Convenience: add a prompt node near center.
                addNodeFromTemplate(templates[1], { x: 260, y: 120 });
              }}
              title="Quick add: Prompt"
            >
              <Plus className="h-4 w-4" />
              Node
            </button>
          </div>
        </div>

        {/* Canvas toolbar (zoom / fit) */}
        <div className="absolute bottom-4 right-4 z-30 flex items-center gap-2">
          <MiniTool title="Zoom in" onClick={zoomIn}>
            <ZoomIn className="h-4 w-4" />
          </MiniTool>
          <MiniTool title="Zoom out" onClick={zoomOut}>
            <ZoomOut className="h-4 w-4" />
          </MiniTool>
          <MiniTool title="Fit view" onClick={fit}>
            <Wand2 className="h-4 w-4" />
          </MiniTool>
        </div>

        {/* React Flow canvas */}
        <div className="absolute inset-0">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onInit={(instance) => setRf(instance)}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onPaneClick={() => setSelectedNodeId(null)}
            onSelectionChange={(sel) => setSelectedNodeId(sel.nodes?.[0]?.id ?? null)}
            onPaneContextMenu={(e) => {
              e.preventDefault();
              const bounds = wrapperRef.current?.getBoundingClientRect();
              const x = e.clientX - (bounds?.left ?? 0);
              const y = e.clientY - (bounds?.top ?? 0);
              setMenu({ open: true, clientX: e.clientX, clientY: e.clientY, x, y });
            }}
            onMoveStart={() => {
              if (menu.open) setMenu({ open: false });
            }}
            defaultEdgeOptions={defaultEdgeOptions}
            fitView
            minZoom={0.2}
            maxZoom={2.2}
            panOnScroll
            zoomOnScroll
            selectionOnDrag
            proOptions={{ hideAttribution: true }}
            className="!bg-transparent"
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={22}
              size={1}
              color="rgba(230,237,243,0.10)"
            />
          </ReactFlow>
        </div>

        {/* Context menu (right click) */}
        {menu.open ? (
          <div
            className="absolute z-40"
            style={{ left: menu.x, top: menu.y }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="w-[260px] overflow-hidden rounded-[16px] border border-[#30363d] bg-[#161b22] shadow-[0_25px_80px_rgba(0,0,0,0.65)]">
              <div className="flex items-center justify-between border-b border-[#30363d] px-3 py-2">
                <div className="text-[11px] font-semibold text-[#e6edf3]/90">Add node</div>
                <button
                  className="inline-flex h-7 w-7 items-center justify-center rounded-[12px] border border-[#30363d] bg-[#0d1117] text-[#e6edf3]/70 hover:text-[#e6edf3]"
                  onClick={() => setMenu({ open: false })}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="p-2">
                {templates.map((tpl) => (
                  <button
                    key={tpl.title}
                    className="w-full rounded-[14px] px-3 py-2 text-left hover:bg-[#0d1117]"
                    onClick={() => {
                      const pos = screenToFlow(menu.clientX, menu.clientY);
                      addNodeFromTemplate(tpl, pos);
                      setMenu({ open: false });
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: getKindDot(tpl.kind) }} />
                          <div className="truncate text-[11px] font-semibold text-[#e6edf3]/90">{tpl.title}</div>
                        </div>
                        <div className="mt-0.5 text-[10px] text-[#e6edf3]/45">{tpl.description}</div>
                      </div>

                      <div className="text-[10px] text-[#e6edf3]/40">⏎</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : null}

        {/* Click-catcher to close context menu */}
        {menu.open ? (
          <button
            className="absolute inset-0 z-20 cursor-default"
            onClick={() => setMenu({ open: false })}
            aria-label="Close context menu"
          />
        ) : null}
      </div>
    </div>
  );
}

/* ------------------------------ Inspector Panel ----------------------------- */

function InspectorPanel({
  node,
  onClose,
  onHide,
  onDelete,
  onUpdate,
}: {
  node: Node<AgentNodeData> | null;
  onClose: () => void;
  onHide: () => void;
  onDelete: () => void;
  onUpdate: (updater: (prev: AgentNodeData) => AgentNodeData) => void;
}) {
  const [mainOpen, setMainOpen] = React.useState(true);
  const [outputsOpen, setOutputsOpen] = React.useState(true);

  // Keep the panel open state stable, but update content when node changes.
  React.useEffect(() => {
    // no-op; placeholder to emphasize re-render on node change
  }, [node?.id]);

  if (!node) {
    return (
      <div className="overflow-hidden rounded-[18px] border border-[#30363d] bg-[#161b22] shadow-[0_25px_80px_rgba(0,0,0,0.65)]">
        <div className="flex items-center justify-between border-b border-[#30363d] px-3 py-2">
          <div>
            <div className="text-[12px] font-semibold text-[#e6edf3]">Tools / Settings</div>
            <div className="text-[10px] text-[#e6edf3]/45">Select a node to edit it</div>
          </div>

          <button
            className="inline-flex h-8 w-8 items-center justify-center rounded-[12px] border border-[#30363d] bg-[#0d1117] text-[#e6edf3]/75 hover:text-[#e6edf3]"
            onClick={onHide}
            title="Hide panel"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-3 text-[11px] text-[#e6edf3]/65">
          Click any node on the canvas to see its settings here.
        </div>
      </div>
    );
  }

  const cfg = node.data.config;
  const outputs = cfg.outputs ?? [];

  return (
    <div className="overflow-hidden rounded-[18px] border border-[#30363d] bg-[#161b22] shadow-[0_25px_80px_rgba(0,0,0,0.65)]">
      {/* Header (node name + tag) */}
      <div className="border-b border-[#30363d] px-3 py-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="truncate text-[12px] font-semibold text-[#e6edf3]">
              {node.data.title}
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-2">
              <div className="text-[10px] text-[#e6edf3]/45">{getNodeKindLabel(node.data.kind)}</div>
              {node.data.tag ? (
                <div className="inline-flex items-center gap-1 rounded-full border border-[#30363d] bg-[#0d1117] px-2 py-0.5 text-[10px] text-[#e6edf3]/75">
                  <Circle className="h-2.5 w-2.5 fill-[#e6edf3]/65 text-[#e6edf3]/65" />
                  {node.data.tag}
                </div>
              ) : null}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              className="inline-flex h-8 w-8 items-center justify-center rounded-[12px] border border-[#30363d] bg-[#0d1117] text-[#e6edf3]/75 hover:text-[#e6edf3]"
              onClick={onClose}
              title="Deselect"
            >
              <X className="h-4 w-4" />
            </button>

            <button
              className="inline-flex h-8 w-8 items-center justify-center rounded-[12px] border border-[#30363d] bg-[#0d1117] text-[#e6edf3]/75 hover:text-[#e6edf3]"
              onClick={onHide}
              title="Hide panel"
            >
              <Settings2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="max-h-[720px] overflow-auto p-3">
        {/* Basic */}
        <div className="space-y-3">
          <Field label="Title">
            <input
              className="h-9 w-full rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 text-[11px] text-[#e6edf3]/90 outline-none placeholder:text-[#e6edf3]/35"
              value={node.data.title}
              onChange={(e) => {
                const v = e.target.value;
                onUpdate((prev) => ({ ...prev, title: v }));
              }}
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Timeout (sec)">
              <input
                type="number"
                min={0}
                className="h-9 w-full rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 text-[11px] text-[#e6edf3]/90 outline-none"
                value={cfg.timeoutSec ?? 0}
                onChange={(e) => {
                  const v = clamp(Number(e.target.value || 0), 0, 60 * 60);
                  onUpdate((prev) => ({
                    ...prev,
                    config: { ...prev.config, timeoutSec: v },
                  }));
                }}
              />
            </Field>

            <Field label="Retry Policy">
              <input
                type="number"
                min={0}
                className="h-9 w-full rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 text-[11px] text-[#e6edf3]/90 outline-none"
                value={cfg.retry ?? 0}
                onChange={(e) => {
                  const v = clamp(Number(e.target.value || 0), 0, 99);
                  onUpdate((prev) => ({
                    ...prev,
                    config: { ...prev.config, retry: v },
                  }));
                }}
              />
            </Field>
          </div>

          <Field label="Commentary">
            <textarea
              className="min-h-[80px] w-full resize-none rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2 text-[11px] text-[#e6edf3]/90 outline-none placeholder:text-[#e6edf3]/35"
              value={cfg.commentary ?? ""}
              placeholder="Optional note / explanation…"
              onChange={(e) => {
                const v = e.target.value;
                onUpdate((prev) => ({
                  ...prev,
                  config: { ...prev.config, commentary: v },
                }));
              }}
            />
          </Field>

          <div className="border-t border-[#30363d] pt-3" />

          {/* Main section (collapsible) */}
          <CollapsibleHeader
            title="Main"
            open={mainOpen}
            onToggle={() => setMainOpen((v) => !v)}
          />
          {mainOpen ? (
            <div className="mt-2 space-y-3">
              <NodeMainForm node={node} onUpdate={onUpdate} />
            </div>
          ) : null}

          <div className="border-t border-[#30363d] pt-3" />

          {/* Outputs section (collapsible) */}
          <CollapsibleHeader
            title="Outputs"
            open={outputsOpen}
            onToggle={() => setOutputsOpen((v) => !v)}
          />

          {outputsOpen ? (
            <div className="mt-2 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-[10px] text-[#e6edf3]/55">Export values from this node</div>

                <button
                  className="inline-flex items-center gap-2 rounded-[12px] border border-[#30363d] bg-[#0d1117] px-2 py-1 text-[10px] font-semibold text-[#e6edf3]/80 hover:text-[#e6edf3]"
                  onClick={() => {
                    onUpdate((prev) => ({
                      ...prev,
                      config: {
                        ...prev.config,
                        outputs: [
                          ...(prev.config.outputs ?? []),
                          { id: uid("o"), name: "new_output", mode: "var" },
                        ],
                      },
                    }));
                  }}
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add output
                </button>
              </div>

              {outputs.length === 0 ? (
                <div className="rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2 text-[11px] text-[#e6edf3]/55">
                  No outputs configured.
                </div>
              ) : (
                <div className="space-y-2">
                  {outputs.map((o) => (
                    <div
                      key={o.id}
                      className="rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="text-[10px] text-[#e6edf3]/55">Name</div>
                          <input
                            className="mt-1 h-8 w-full rounded-[12px] border border-[#30363d] bg-[#161b22] px-3 text-[11px] text-[#e6edf3]/90 outline-none"
                            value={o.name}
                            onChange={(e) => {
                              const v = e.target.value;
                              onUpdate((prev) => ({
                                ...prev,
                                config: {
                                  ...prev.config,
                                  outputs: (prev.config.outputs ?? []).map((x) =>
                                    x.id === o.id ? { ...x, name: v } : x,
                                  ),
                                },
                              }));
                            }}
                          />
                        </div>

                        <button
                          className="inline-flex h-8 w-8 items-center justify-center rounded-[12px] border border-[#30363d] bg-[#161b22] text-[#e6edf3]/70 hover:text-[#e6edf3]"
                          title="Remove output"
                          onClick={() => {
                            onUpdate((prev) => ({
                              ...prev,
                              config: {
                                ...prev.config,
                                outputs: (prev.config.outputs ?? []).filter((x) => x.id !== o.id),
                              },
                            }));
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>

                      <div className="mt-2 flex items-center justify-between">
                        <div className="text-[10px] text-[#e6edf3]/55">Mode</div>
                        <PillToggle
                          value={o.mode}
                          options={[
                            { value: "var", label: "Var" },
                            { value: "edges", label: "Edges" },
                          ]}
                          onChange={(v) => {
                            onUpdate((prev) => ({
                              ...prev,
                              config: {
                                ...prev.config,
                                outputs: (prev.config.outputs ?? []).map((x) =>
                                  x.id === o.id ? { ...x, mode: v as OutputSpec["mode"] } : x,
                                ),
                              },
                            }));
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : null}

          <div className="border-t border-[#30363d] pt-3" />

          {/* Danger zone */}
          <button
            className="inline-flex w-full items-center justify-center gap-2 rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2 text-[11px] font-semibold text-[#e6edf3]/85 hover:border-[#ef4444]/60 hover:text-[#ef4444]"
            onClick={onDelete}
          >
            <Trash2 className="h-4 w-4" />
            Delete node
          </button>
        </div>
      </div>
    </div>
  );
}

function NodeMainForm({
  node,
  onUpdate,
}: {
  node: Node<AgentNodeData>;
  onUpdate: (updater: (prev: AgentNodeData) => AgentNodeData) => void;
}) {
  const cfg = node.data.config;

  if (node.data.kind === "llm") {
    return (
      <div className="space-y-3">
        <Field label="Model">
          <input
            className="h-9 w-full rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 text-[11px] text-[#e6edf3]/90 outline-none placeholder:text-[#e6edf3]/35"
            value={cfg.model ?? ""}
            placeholder="DeepSeek-V3.1-Terminus-IQ4"
            onChange={(e) => {
              const v = e.target.value;
              onUpdate((prev) => ({
                ...prev,
                tag: v || prev.tag,
                config: { ...prev.config, model: v },
              }));
            }}
          />
        </Field>

        <div className="flex items-center justify-between rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2">
          <div>
            <div className="text-[11px] font-semibold text-[#e6edf3]/85">take outside</div>
            <div className="text-[10px] text-[#e6edf3]/45">Allow external execution / remote run (placeholder)</div>
          </div>

          <button
            className={cn(
              "h-6 w-10 rounded-full border border-[#30363d] p-0.5 transition",
              cfg.takeOutside ? "bg-[#4054b4]" : "bg-[#161b22]",
            )}
            onClick={() => {
              onUpdate((prev) => ({
                ...prev,
                config: { ...prev.config, takeOutside: !prev.config.takeOutside },
              }));
            }}
            aria-label="Toggle take outside"
          >
            <span
              className={cn(
                "block h-5 w-5 rounded-full bg-white transition",
                cfg.takeOutside ? "translate-x-4" : "translate-x-0",
              )}
            />
          </button>
        </div>
      </div>
    );
  }

  if (node.data.kind === "prompt") {
    return (
      <div className="space-y-3">
        <Field label="System Instruction">
          <textarea
            className="min-h-[90px] w-full resize-none rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2 text-[11px] text-[#e6edf3]/90 outline-none placeholder:text-[#e6edf3]/35"
            value={cfg.systemInstruction ?? ""}
            placeholder="System Instruction…"
            onChange={(e) => {
              const v = e.target.value;
              onUpdate((prev) => ({
                ...prev,
                config: { ...prev.config, systemInstruction: v },
              }));
            }}
          />
        </Field>

        <Field label="Chat History">
          <textarea
            className="min-h-[70px] w-full resize-none rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2 text-[11px] text-[#e6edf3]/90 outline-none placeholder:text-[#e6edf3]/35"
            value={cfg.chatHistory ?? ""}
            placeholder="Optional history…"
            onChange={(e) => {
              const v = e.target.value;
              onUpdate((prev) => ({
                ...prev,
                config: { ...prev.config, chatHistory: v },
              }));
            }}
          />
        </Field>

        <Field label="Prompt">
          <textarea
            className="min-h-[70px] w-full resize-none rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2 text-[11px] text-[#e6edf3]/90 outline-none placeholder:text-[#e6edf3]/35"
            value={cfg.prompt ?? ""}
            placeholder="User prompt…"
            onChange={(e) => {
              const v = e.target.value;
              onUpdate((prev) => ({
                ...prev,
                config: { ...prev.config, prompt: v },
              }));
            }}
          />
        </Field>
      </div>
    );
  }

  if (node.data.kind === "tool") {
    return (
      <div className="space-y-3">
        <Field label="Tool name">
          <input
            className="h-9 w-full rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 text-[11px] text-[#e6edf3]/90 outline-none placeholder:text-[#e6edf3]/35"
            value={cfg.toolName ?? ""}
            placeholder="schedule_parser"
            onChange={(e) => {
              const v = e.target.value;
              onUpdate((prev) => ({
                ...prev,
                config: { ...prev.config, toolName: v },
              }));
            }}
          />
        </Field>

        <Field label="Description">
          <textarea
            className="min-h-[90px] w-full resize-none rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2 text-[11px] text-[#e6edf3]/90 outline-none placeholder:text-[#e6edf3]/35"
            value={cfg.toolDescription ?? ""}
            placeholder="What does this tool do…"
            onChange={(e) => {
              const v = e.target.value;
              onUpdate((prev) => ({
                ...prev,
                config: { ...prev.config, toolDescription: v },
              }));
            }}
          />
        </Field>
      </div>
    );
  }

  if (node.data.kind === "output") {
    return (
      <div className="space-y-3">
        <Field label="Output key">
          <input
            className="h-9 w-full rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 text-[11px] text-[#e6edf3]/90 outline-none placeholder:text-[#e6edf3]/35"
            value={cfg.outputKey ?? ""}
            placeholder="answer"
            onChange={(e) => {
              const v = e.target.value;
              onUpdate((prev) => ({
                ...prev,
                config: { ...prev.config, outputKey: v },
              }));
            }}
          />
        </Field>

        <div className="rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2 text-[11px] text-[#e6edf3]/65">
          Tip: Connect an LLM node output to this node input.
        </div>
      </div>
    );
  }

  // Note / default.
  return (
    <div className="rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2 text-[11px] text-[#e6edf3]/65">
      No special fields for this node type.
    </div>
  );
}

/* ----------------------------- Small UI Pieces ----------------------------- */

function TopPill({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div
      className={cn(
        "inline-flex h-9 items-center gap-2 rounded-[14px] border border-[#30363d] bg-[#161b22] px-3 text-[11px] font-semibold text-[#e6edf3]/85 shadow-[0_25px_80px_rgba(0,0,0,0.65)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

function IconPill({ children }: { children: React.ReactNode }) {
  return (
    <div className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] border border-[#30363d] bg-[#161b22] text-[#e6edf3]/80 shadow-[0_25px_80px_rgba(0,0,0,0.65)]">
      {children}
    </div>
  );
}

function IconButton({
  children,
  title,
  onClick,
}: {
  children: React.ReactNode;
  title?: string;
  onClick?: () => void;
}) {
  return (
    <button
      className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] border border-[#30363d] bg-[#161b22] text-[#e6edf3]/70 shadow-[0_25px_80px_rgba(0,0,0,0.65)] hover:text-[#e6edf3]"
      title={title}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function MiniTool({
  children,
  title,
  onClick,
}: {
  children: React.ReactNode;
  title?: string;
  onClick?: () => void;
}) {
  return (
    <button
      className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] border border-[#30363d] bg-[#161b22] text-[#e6edf3]/70 shadow-[0_25px_80px_rgba(0,0,0,0.65)] hover:text-[#e6edf3]"
      title={title}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-semibold text-[#e6edf3]/70">{label}</div>
      {children}
    </div>
  );
}

function CollapsibleHeader({
  title,
  open,
  onToggle,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      className="flex w-full items-center justify-between rounded-[14px] border border-[#30363d] bg-[#0d1117] px-3 py-2 text-left"
      onClick={onToggle}
    >
      <div className="text-[11px] font-semibold text-[#e6edf3]/85">{title}</div>
      <ChevronDown className={cn("h-4 w-4 text-[#e6edf3]/60 transition", open ? "rotate-180" : "")} />
    </button>
  );
}

function PillToggle({
  value,
  options,
  onChange,
}: {
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (next: string) => void;
}) {
  return (
    <div className="inline-flex overflow-hidden rounded-full border border-[#30363d] bg-[#161b22]">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            className={cn(
              "px-3 py-1 text-[10px] font-semibold transition",
              active ? "bg-[#4054b4] text-white" : "text-[#e6edf3]/75 hover:text-[#e6edf3]",
            )}
            onClick={() => onChange(opt.value)}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
