import * as React from "react";

import ReactFlow, {
  Background,
  BackgroundVariant,
  BaseEdge,
  Connection,
  Edge,
  EdgeLabelRenderer,
  EdgeProps,
  Handle,
  MarkerType,
  Node,
  NodeProps,
  Position,
  ReactFlowInstance,
  ReactFlowProvider,
  addEdge,
  getSmoothStepPath,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

import {
  ArrowLeft,
  ChevronDown,
  Download,
  FileUp,
  Layers,
  Link2,
  Play,
  Plus,
  Search,
  Settings2,
  Share2,
  Trash2,
  Wand2,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

/**
 * Workflow builder (ReactFlow)
 * Reworked according to “План перестройки.docx”:
 * - Left panel: Public variables (full height, opens via side button, closes via X)
 * - Right panel: Node settings (when selected) or Nodes list (when none selected)
 * - Panels are full height and docked to the sides.
 * - Removed bottom-center prompt bar.
 * - Zoom toolbar in the bottom-left.
 * - Logical edges show a label (condition) in the center.
 */

/* --------------------------------- Types --------------------------------- */

type NodeKind = "llm" | "prompt" | "tool" | "output" | "note";

type Port = {
  id: string;
  label: string;
};

type FieldType = "text" | "number" | "textarea" | "toggle";

type SettingField = {
  key: string;
  label: string;
  type: FieldType;
  placeholder?: string;
};

type FieldBinding =
  | { type: "global"; varId: string }
  | { type: "edge"; edgeId: string };

type AgentNodeConfig = {
  timeoutSec?: number;
  retry?: number;
  commentary?: string;

  // llm
  model?: string;

  // prompt
  systemInstruction?: string;
  prompt?: string;

  // tool
  toolName?: string;
  toolDescription?: string;

  // output
  outputKey?: string;

  // binding meta
  bindings?: Record<string, FieldBinding>;
};

export type AgentNodeData = {
  kind: NodeKind;
  title: string;
  tag?: string;
  description?: string;
  inputs: Port[];
  outputs: Port[];
  config: AgentNodeConfig;
};

type NodeTemplate = {
  title: string;
  description: string;
  kind: NodeKind;
  makeData: () => AgentNodeData;
};

type ContextMenuState =
  | { open: false }
  | { open: true; clientX: number; clientY: number; x: number; y: number };

type GlobalVar = { id: string; name: string; value: string };

type BindMenuState =
  | { open: false }
  | { open: true; fieldKey: string; x: number; y: number };

/* -------------------------------- Helpers -------------------------------- */

function uid(prefix = "id") {
  const c: any = globalThis.crypto;
  const id = typeof c?.randomUUID === "function" ? c.randomUUID() : `${Date.now()}-${Math.random()}`;
  return `${prefix}-${id}`;
}

function truncate(str: string, max = 120) {
  if (str.length <= max) return str;
  return `${str.slice(0, Math.max(0, max - 1))}…`;
}

function kindDot(kind: NodeKind) {
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

function requestSettingsSchema(kind: NodeKind): Promise<SettingField[]> {
  // “По запросу”: сейчас это mocked-request.
  // Встроите тут реальный вызов бэкенда (например: GET /workflow/node-schema?kind=...)
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(getLocalSchema(kind)), 140);
  });
}

function getLocalSchema(kind: NodeKind): SettingField[] {
  const base: SettingField[] = [
    { key: "title", label: "Title", type: "text", placeholder: "Node title" },
    { key: "timeoutSec", label: "Timeout (sec)", type: "number" },
    { key: "retry", label: "Retry", type: "number" },
    { key: "commentary", label: "Commentary", type: "textarea", placeholder: "Optional notes" },
  ];

  if (kind === "llm") {
    return [
      ...base,
      { key: "model", label: "Model", type: "text", placeholder: "DeepSeek-R1" },
    ];
  }

  if (kind === "prompt") {
    return [
      ...base,
      { key: "systemInstruction", label: "System instruction", type: "textarea" },
      { key: "prompt", label: "Prompt", type: "textarea" },
    ];
  }

  if (kind === "tool") {
    return [
      ...base,
      { key: "toolName", label: "Tool name", type: "text" },
      { key: "toolDescription", label: "Tool description", type: "textarea" },
    ];
  }

  if (kind === "output") {
    return [
      ...base,
      { key: "outputKey", label: "Output key", type: "text", placeholder: "answer" },
    ];
  }

  // note
  return [
    { key: "title", label: "Title", type: "text", placeholder: "Note" },
    { key: "commentary", label: "Text", type: "textarea", placeholder: "Write something…" },
  ];
}

/* ------------------------------ Edge renderer ----------------------------- */

function LabeledSmoothStepEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
  label,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={style} markerEnd={markerEnd} />
      {label ? (
        <EdgeLabelRenderer>
          <div
            className="pointer-events-none absolute rounded-xl border border-[hsl(var(--tp-border))] bg-black/50 px-2 py-1 text-[10px] font-semibold text-white/80 backdrop-blur-2xl"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            }}
          >
            {String(label)}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
}

const edgeTypes = {
  labeled: LabeledSmoothStepEdge,
};

/* ------------------------------ Node renderer ----------------------------- */

function AgentNode({ data, selected }: NodeProps<AgentNodeData>) {
  const headerH = 44;
  const rowGap = 22;

  return (
    <div
      className={cn(
        "min-w-[240px] max-w-[320px] rounded-2xl border bg-black/10 shadow-[0px_18px_50px_rgba(0,0,0,0.55)] backdrop-blur-2xl",
        selected ? "border-[hsl(var(--tp-blue))]" : "border-[hsl(var(--tp-border))]",
      )}
    >
      <div
        className={cn(
          "flex items-start justify-between gap-3 border-b px-4 py-3",
          selected ? "border-[hsl(var(--tp-blue))]/50" : "border-[hsl(var(--tp-border))]",
        )}
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: kindDot(data.kind) }} />
            <div className="truncate text-[12px] font-semibold text-white/90">{data.title}</div>
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-2">
            <div className="text-[10px] text-white/45">{data.kind.toUpperCase()}</div>
            {data.tag ? (
              <div className="inline-flex items-center rounded-full border border-[hsl(var(--tp-border))] bg-black/20 px-2 py-0.5 text-[10px] text-white/70">
                {data.tag}
              </div>
            ) : null}
          </div>
        </div>

        <div className="text-[10px] text-white/45">out: {data.outputs.length}</div>
      </div>

      <div className="px-4 py-3 text-[11px] text-white/75">
        {data.description ? <div className="mb-2 text-white/70">{data.description}</div> : null}
        <NodePreview data={data} />
      </div>

      {/* Handles */}
      {data.inputs.map((p, idx) => (
        <Handle
          key={`in-${p.id}`}
          id={p.id}
          type="target"
          position={Position.Left}
          className="!h-2.5 !w-2.5 !border !border-[hsl(var(--tp-border))] !bg-black/80"
          style={{ top: headerH + 18 + idx * rowGap }}
        />
      ))}
      {data.outputs.map((p, idx) => (
        <Handle
          key={`out-${p.id}`}
          id={p.id}
          type="source"
          position={Position.Right}
          className="!h-2.5 !w-2.5 !border !border-[hsl(var(--tp-border))] !bg-black/80"
          style={{ top: headerH + 18 + idx * rowGap }}
        />
      ))}
    </div>
  );
}

function NodePreview({ data }: { data: AgentNodeData }) {
  const cfg = data.config;

  if (data.kind === "llm") {
    return (
      <div className="rounded-xl border border-[hsl(var(--tp-border))] bg-black/20 px-3 py-2">
        <div className="text-[10px] text-white/45">Model</div>
        <div className="mt-0.5 text-[11px] text-white/85">{cfg.model ?? "Select model…"}</div>
      </div>
    );
  }

  if (data.kind === "prompt") {
    const text = cfg.systemInstruction || cfg.prompt || "";
    return (
      <div className="rounded-xl border border-[hsl(var(--tp-border))] bg-black/20 px-3 py-2 text-[11px] text-white/80">
        {text ? truncate(text, 140) : "Type your prompt…"}
      </div>
    );
  }

  if (data.kind === "tool") {
    return (
      <div className="rounded-xl border border-[hsl(var(--tp-border))] bg-black/20 px-3 py-2">
        <div className="text-[10px] text-white/45">Tool</div>
        <div className="mt-0.5 text-[11px] text-white/85">{cfg.toolName ?? "Tool name"}</div>
      </div>
    );
  }

  if (data.kind === "output") {
    return (
      <div className="rounded-xl border border-[hsl(var(--tp-border))] bg-black/20 px-3 py-2">
        <div className="text-[10px] text-white/45">Output key</div>
        <div className="mt-0.5 text-[11px] text-white/85">{cfg.outputKey ?? "answer"}</div>
      </div>
    );
  }

  // note
  return (
    <div className="rounded-xl border border-[hsl(var(--tp-border))] bg-black/20 px-3 py-2 text-[11px] text-white/80">
      {cfg.commentary ? truncate(cfg.commentary, 160) : "Write something…"}
    </div>
  );
}

const nodeTypes = {
  agent: AgentNode,
};

/* --------------------------- Initial graph + templates ---------------------- */

const initialNodes: Node<AgentNodeData>[] = [
  {
    id: "sys",
    type: "agent",
    position: { x: 60, y: 140 },
    data: {
      kind: "prompt",
      title: "System Instruction",
      tag: "var: system",
      description: "System rules / role for the model.",
      inputs: [],
      outputs: [{ id: "out", label: "system" }],
      config: {
        systemInstruction: "Ты — помощник. Отвечай кратко и по делу.",
        timeoutSec: 60,
        retry: 1,
        commentary: "",
      },
    },
  },
  {
    id: "prompt",
    type: "agent",
    position: { x: 60, y: 330 },
    data: {
      kind: "prompt",
      title: "User Prompt",
      tag: "input",
      description: "What user asks.",
      inputs: [],
      outputs: [{ id: "out", label: "prompt" }],
      config: {
        prompt: "Сделай краткую сводку по задаче…",
        timeoutSec: 60,
        retry: 1,
      },
    },
  },
  {
    id: "llm",
    type: "agent",
    position: { x: 420, y: 230 },
    data: {
      kind: "llm",
      title: "llm_local",
      tag: "Model",
      description: "LLM node. Connect prompts and get text.",
      inputs: [
        { id: "system", label: "system" },
        { id: "prompt", label: "prompt" },
      ],
      outputs: [{ id: "text", label: "text" }],
      config: {
        model: "DeepSeek-R1",
        timeoutSec: 90,
        retry: 1,
      },
    },
  },
  {
    id: "out",
    type: "agent",
    position: { x: 760, y: 255 },
    data: {
      kind: "output",
      title: "Output",
      tag: "result",
      description: "Final output of the workflow.",
      inputs: [{ id: "in", label: "in" }],
      outputs: [],
      config: {
        outputKey: "answer",
        timeoutSec: 10,
        retry: 0,
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
    type: "labeled",
    label: "system",
    style: { stroke: "rgba(230,237,243,0.26)", strokeWidth: 1.25 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(230,237,243,0.35)" },
  },
  {
    id: "e-prompt-llm",
    source: "prompt",
    sourceHandle: "out",
    target: "llm",
    targetHandle: "prompt",
    type: "labeled",
    label: "prompt",
    style: { stroke: "rgba(230,237,243,0.26)", strokeWidth: 1.25 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(230,237,243,0.35)" },
  },
  {
    id: "e-llm-out",
    source: "llm",
    sourceHandle: "text",
    target: "out",
    targetHandle: "in",
    type: "labeled",
    label: "text",
    style: { stroke: "rgba(230,237,243,0.26)", strokeWidth: 1.25 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(230,237,243,0.35)" },
  },
];

const templates: NodeTemplate[] = [
  {
    title: "LLM",
    description: "Model execution node.",
    kind: "llm",
    makeData: () => ({
      kind: "llm",
      title: "llm_local",
      tag: "Model",
      description: "LLM node.",
      inputs: [
        { id: "system", label: "system" },
        { id: "prompt", label: "prompt" },
      ],
      outputs: [{ id: "text", label: "text" }],
      config: { model: "DeepSeek-R1", timeoutSec: 90, retry: 1 },
    }),
  },
  {
    title: "Prompt",
    description: "Instruction / prompt text.",
    kind: "prompt",
    makeData: () => ({
      kind: "prompt",
      title: "Prompt",
      tag: "text",
      description: "Prompt node.",
      inputs: [],
      outputs: [{ id: "out", label: "out" }],
      config: { prompt: "", timeoutSec: 60, retry: 1 },
    }),
  },
  {
    title: "Tool",
    description: "External tool / function call.",
    kind: "tool",
    makeData: () => ({
      kind: "tool",
      title: "Tool",
      tag: "tool",
      description: "Tool node.",
      inputs: [{ id: "in", label: "in" }],
      outputs: [{ id: "out", label: "out" }],
      config: { toolName: "", toolDescription: "", timeoutSec: 60, retry: 1 },
    }),
  },
  {
    title: "Output",
    description: "Workflow output.",
    kind: "output",
    makeData: () => ({
      kind: "output",
      title: "Output",
      tag: "result",
      description: "Final output.",
      inputs: [{ id: "in", label: "in" }],
      outputs: [],
      config: { outputKey: "answer", timeoutSec: 10, retry: 0 },
    }),
  },
  {
    title: "Note",
    description: "Just a note on canvas.",
    kind: "note",
    makeData: () => ({
      kind: "note",
      title: "Note",
      tag: "",
      description: "",
      inputs: [],
      outputs: [],
      config: { commentary: "", timeoutSec: 0, retry: 0 },
    }),
  },
];

/* --------------------------------- Page ---------------------------------- */

export function WorkflowBuilderPage() {
  return (
    <ReactFlowProvider>
      <WorkflowBuilderInner />
    </ReactFlowProvider>
  );
}

function WorkflowBuilderInner() {
  const wrapperRef = React.useRef<HTMLDivElement | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);

  const [rf, setRf] = React.useState<ReactFlowInstance | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<AgentNodeData>(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const [selectedNodeId, setSelectedNodeId] = React.useState<string | null>(null);
  const selectedNode = React.useMemo(
    () => (selectedNodeId ? nodes.find((n) => n.id === selectedNodeId) ?? null : null),
    [nodes, selectedNodeId],
  );

  const [leftOpen, setLeftOpen] = React.useState(true);
  const [rightOpen, setRightOpen] = React.useState(true);

  const [menu, setMenu] = React.useState<ContextMenuState>({ open: false });
  const [bindMenu, setBindMenu] = React.useState<BindMenuState>({ open: false });

  const [globals, setGlobals] = React.useState<GlobalVar[]>([
    { id: "gv-system", name: "system", value: "Ты — помощник." },
    { id: "gv-user", name: "user_id", value: "" },
  ]);

  const [nodeSearch, setNodeSearch] = React.useState("");

  const defaultEdgeOptions = React.useMemo(
    () => ({
      type: "labeled",
      style: { stroke: "rgba(230,237,243,0.26)", strokeWidth: 1.25 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(230,237,243,0.35)" },
    }),
    [],
  );

  const screenToFlow = React.useCallback(
    (clientX: number, clientY: number) => {
      const bounds = wrapperRef.current?.getBoundingClientRect();
      const x = clientX - (bounds?.left ?? 0);
      const y = clientY - (bounds?.top ?? 0);
      if (!rf) return { x, y };
      return rf.project({ x, y });
    },
    [rf],
  );

  const focusNode = React.useCallback(
    (id: string) => {
      if (!rf) return;
      const n = nodes.find((x) => x.id === id);
      if (!n) return;
      rf.setCenter(n.position.x + 140, n.position.y + 60, { zoom: 1.05, duration: 380 });
    },
    [nodes, rf],
  );

  const addNodeFromTemplate = React.useCallback(
    (tpl: NodeTemplate, position: { x: number; y: number }) => {
      const newNode: Node<AgentNodeData> = {
        id: uid("n"),
        type: "agent",
        position,
        data: tpl.makeData(),
      };
      setNodes((prev) => [...prev, newNode]);
      setSelectedNodeId(newNode.id);
      setRightOpen(true);
      requestAnimationFrame(() => focusNode(newNode.id));
    },
    [focusNode, setNodes],
  );

  const onConnect = React.useCallback(
    (conn: Connection) => {
      setEdges((prev) =>
        addEdge(
          {
            ...conn,
            type: "labeled",
            label: conn.targetHandle ?? "",
            markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(230,237,243,0.35)" },
            style: { stroke: "rgba(230,237,243,0.26)", strokeWidth: 1.25 },
          },
          prev,
        ),
      );
    },
    [setEdges],
  );

  const updateNodeData = React.useCallback(
    (nodeId: string, updater: (prev: AgentNodeData) => AgentNodeData) => {
      setNodes((prev) => prev.map((n) => (n.id === nodeId ? { ...n, data: updater(n.data) } : n)));
    },
    [setNodes],
  );

  const deleteSelectedNode = React.useCallback(() => {
    if (!selectedNodeId) return;
    setNodes((prev) => prev.filter((n) => n.id !== selectedNodeId));
    setEdges((prev) => prev.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId));
    setSelectedNodeId(null);
  }, [selectedNodeId, setEdges, setNodes]);

  const zoomIn = () => rf?.zoomIn({ duration: 150 });
  const zoomOut = () => rf?.zoomOut({ duration: 150 });
  const fitView = () => rf?.fitView({ padding: 0.2, duration: 220 });

  const exportJson = () => {
    const payload = { nodes, edges, globals };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "workflow.json";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const importJson = async (file: File) => {
    const text = await file.text();
    const parsed = JSON.parse(text) as { nodes: Node<AgentNodeData>[]; edges: Edge[]; globals?: GlobalVar[] };
    setNodes(parsed.nodes ?? []);
    setEdges(parsed.edges ?? []);
    if (parsed.globals) setGlobals(parsed.globals);
    setSelectedNodeId(null);
  };

  // Close menus when clicking outside.
  React.useEffect(() => {
    const onPointerDown = () => {
      if (menu.open) setMenu({ open: false });
      if (bindMenu.open) setBindMenu({ open: false });
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMenu({ open: false });
        setBindMenu({ open: false });
      }
    };
    window.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [bindMenu.open, menu.open]);

  const incomingEdges = React.useMemo(() => {
    if (!selectedNodeId) return [] as Edge[];
    return edges.filter((e) => e.target === selectedNodeId);
  }, [edges, selectedNodeId]);

  const nodeIndex = React.useMemo(() => {
    const map = new Map<string, Node<AgentNodeData>>();
    nodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [nodes]);

  const bindSources = React.useMemo(() => {
    // Global vars + incoming edges (outputs of connected nodes)
    const globalsList = globals.map((g) => ({ id: g.id, label: g.name }));

    const connected = incomingEdges
      .map((e) => {
        const src = nodeIndex.get(e.source);
        const srcTitle = src?.data.title ?? e.source;
        const out = e.sourceHandle ?? "out";
        return { edgeId: e.id, label: `${srcTitle}.${out}` };
      })
      .filter(Boolean);

    return { globalsList, connected };
  }, [globals, incomingEdges, nodeIndex]);

  const setFieldBinding = (fieldKey: string, binding?: FieldBinding) => {
    if (!selectedNodeId) return;

    updateNodeData(selectedNodeId, (prev) => {
      const nextCfg: AgentNodeConfig = {
        ...prev.config,
        bindings: { ...(prev.config.bindings ?? {}) },
      };
      if (!binding) {
        delete nextCfg.bindings?.[fieldKey];
      } else {
        nextCfg.bindings![fieldKey] = binding;
      }
      return { ...prev, config: nextCfg };
    });

    // If binding to an edge: set edge label (condition) in the center.
    if (binding?.type === "edge") {
      setEdges((prev) => prev.map((e) => (e.id === binding.edgeId ? { ...e, label: fieldKey } : e)));
    }
  };

  const filteredNodes = React.useMemo(() => {
    const q = nodeSearch.trim().toLowerCase();
    if (!q) return nodes;
    return nodes.filter((n) => n.data.title.toLowerCase().includes(q) || n.data.kind.includes(q));
  }, [nodeSearch, nodes]);

  const leftOffset = leftOpen ? 360 + 28 : 16;

  return (
    <div className="relative h-full text-white">
      {/* Background */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(1100px_circle_at_65%_18%,rgba(40,96,255,0.22),transparent_62%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(900px_circle_at_18%_88%,rgba(86,161,138,0.10),transparent_60%)]" />
      </div>

      <div
        ref={wrapperRef}
        className={cn(
          "relative h-full w-full overflow-hidden rounded-2xl border border-[hsl(var(--tp-border))] bg-black/5",
          "shadow-[0_18px_50px_rgba(0,0,0,0.55)]",
        )}
      >
        {/* Top toolbar */}
        <div className="absolute left-4 right-4 top-4 z-30 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <TopPill>
              <ArrowLeft className="h-4 w-4" />
              Workflow
              <ChevronDown className="h-4 w-4" />
            </TopPill>

            <TopPill>
              Edit
              <ChevronDown className="h-4 w-4" />
            </TopPill>

            <TopPill>
              Help
              <ChevronDown className="h-4 w-4" />
            </TopPill>
          </div>

          <div className="flex items-center gap-2">
            <TopPill className="bg-white text-black hover:bg-white/90">
              <Play className="h-4 w-4" />
              Run
            </TopPill>

            <IconButton title="Export JSON" onClick={exportJson}>
              <Download className="h-4 w-4" />
            </IconButton>

            <IconButton title="Import JSON" onClick={() => fileInputRef.current?.click()}>
              <FileUp className="h-4 w-4" />
            </IconButton>

            <IconButton title="Share (placeholder)">
              <Share2 className="h-4 w-4" />
            </IconButton>
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
        </div>

        {/* Left dock: public variables */}
        {leftOpen ? (
          <SidePanel
            side="left"
            title="Public variables"
            subtitle="Values available for nodes"
            onClose={() => setLeftOpen(false)}
          >
            <GlobalsPanel vars={globals} setVars={setGlobals} />
          </SidePanel>
        ) : (
          <SideToggleButton side="left" title="Show variables" onClick={() => setLeftOpen(true)}>
            <Layers className="h-4 w-4" />
          </SideToggleButton>
        )}

        {/* Right dock: node settings or node list */}
        {rightOpen ? (
          <SidePanel
            side="right"
            title={selectedNode ? "Node settings" : "Nodes"}
            subtitle={selectedNode ? selectedNode.data.title : "Workflow structure"}
            onClose={() => setRightOpen(false)}
          >
            {selectedNode ? (
              <NodeSettingsPanel
                key={selectedNode.id}
                node={selectedNode}
                edges={incomingEdges}
                bindSources={bindSources}
                onDeselect={() => setSelectedNodeId(null)}
                onDelete={deleteSelectedNode}
                onUpdate={(updater) => updateNodeData(selectedNode.id, updater)}
                onOpenBindMenu={(fieldKey, rect) => {
                  setBindMenu({ open: true, fieldKey, x: rect.left, y: rect.bottom + 8 });
                }}
              />
            ) : (
              <NodesListPanel
                nodes={filteredNodes}
                search={nodeSearch}
                setSearch={setNodeSearch}
                selectedId={selectedNodeId}
                onSelect={(id) => {
                  setSelectedNodeId(id);
                  focusNode(id);
                }}
                onAdd={() => addNodeFromTemplate(templates[0], { x: 260, y: 160 })}
              />
            )}
          </SidePanel>
        ) : (
          <SideToggleButton side="right" title="Show nodes/settings" onClick={() => setRightOpen(true)}>
            <Settings2 className="h-4 w-4" />
          </SideToggleButton>
        )}

        {/* Zoom toolbar bottom-left */}
        <div
          className="absolute bottom-4 z-30 flex items-center gap-2"
          style={{ left: leftOffset }}
        >
          <MiniTool title="Zoom in" onClick={zoomIn}>
            <ZoomIn className="h-4 w-4" />
          </MiniTool>
          <MiniTool title="Zoom out" onClick={zoomOut}>
            <ZoomOut className="h-4 w-4" />
          </MiniTool>
          <MiniTool title="Fit view" onClick={fitView}>
            <Wand2 className="h-4 w-4" />
          </MiniTool>
        </div>

        {/* Canvas */}
        <div className="absolute inset-0">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onInit={(instance) => setRf(instance)}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onPaneClick={() => setSelectedNodeId(null)}
            onSelectionChange={(sel) => setSelectedNodeId(sel.nodes?.[0]?.id ?? null)}
            onEdgeDoubleClick={(ev, e) => {
              ev.preventDefault();
              ev.stopPropagation();
              const next = window.prompt("Edge label (condition)", String(e.label ?? ""));
              if (next === null) return;
              setEdges((prev) => prev.map((x) => (x.id === e.id ? { ...x, label: next } : x)));
            }}
            onPaneContextMenu={(e) => {
              e.preventDefault();
              const bounds = wrapperRef.current?.getBoundingClientRect();
              const x = e.clientX - (bounds?.left ?? 0);
              const y = e.clientY - (bounds?.top ?? 0);
              setMenu({ open: true, clientX: e.clientX, clientY: e.clientY, x, y });
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
            <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="rgba(230,237,243,0.10)" />
          </ReactFlow>
        </div>

        {/* Pane context menu */}
        {menu.open ? (
          <div
            className="absolute z-50"
            style={{ left: menu.x, top: menu.y }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="w-[270px] overflow-hidden rounded-2xl border border-[hsl(var(--tp-border))] bg-black/60 shadow-[0_25px_80px_rgba(0,0,0,0.65)] backdrop-blur-2xl">
              <div className="flex items-center justify-between border-b border-white/10 px-3 py-2">
                <div className="text-[11px] font-semibold text-white/90">Add node</div>
                <button
                  className="inline-flex h-7 w-7 items-center justify-center rounded-xl border border-[hsl(var(--tp-border))] bg-black/30 text-white/70 hover:text-white"
                  onClick={() => setMenu({ open: false })}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="p-2">
                {templates.map((tpl) => (
                  <button
                    key={tpl.title}
                    className="w-full rounded-xl px-3 py-2 text-left hover:bg-white/10"
                    onClick={() => {
                      const pos = screenToFlow(menu.clientX, menu.clientY);
                      addNodeFromTemplate(tpl, pos);
                      setMenu({ open: false });
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: kindDot(tpl.kind) }} />
                          <div className="truncate text-[11px] font-semibold text-white/90">{tpl.title}</div>
                        </div>
                        <div className="mt-0.5 text-[10px] text-white/50">{tpl.description}</div>
                      </div>
                      <div className="text-[10px] text-white/35">⏎</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : null}

        {/* Bind menu (for per-field links) */}
        {bindMenu.open ? (
          <div
            className="fixed z-[80]"
            style={{ left: bindMenu.x, top: bindMenu.y }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="w-[280px] overflow-hidden rounded-2xl border border-[hsl(var(--tp-border))] bg-black/70 shadow-[0_25px_80px_rgba(0,0,0,0.65)] backdrop-blur-2xl">
              <div className="flex items-center justify-between border-b border-white/10 px-3 py-2">
                <div className="text-[11px] font-semibold text-white/90">Bind: {bindMenu.fieldKey}</div>
                <button
                  className="inline-flex h-7 w-7 items-center justify-center rounded-xl border border-[hsl(var(--tp-border))] bg-black/30 text-white/70 hover:text-white"
                  onClick={() => setBindMenu({ open: false })}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="p-2">
                <div className="px-2 pb-1 text-[10px] font-semibold text-white/50">Global variables</div>
                {bindSources.globalsList.length ? (
                  <div className="space-y-1">
                    {bindSources.globalsList.map((g) => (
                      <button
                        key={g.id}
                        className="w-full rounded-xl px-3 py-2 text-left text-[11px] text-white/85 hover:bg-white/10"
                        onClick={() => {
                          setFieldBinding(bindMenu.fieldKey, { type: "global", varId: g.id });
                          setBindMenu({ open: false });
                        }}
                      >
                        {g.label}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="px-3 py-2 text-[11px] text-white/45">No globals</div>
                )}

                <div className="my-2 h-px bg-white/10" />

                <div className="px-2 pb-1 text-[10px] font-semibold text-white/50">Connected outputs</div>
                {bindSources.connected.length ? (
                  <div className="space-y-1">
                    {bindSources.connected.map((c) => (
                      <button
                        key={c.edgeId}
                        className="w-full rounded-xl px-3 py-2 text-left text-[11px] text-white/85 hover:bg-white/10"
                        onClick={() => {
                          setFieldBinding(bindMenu.fieldKey, { type: "edge", edgeId: c.edgeId });
                          setBindMenu({ open: false });
                        }}
                      >
                        {c.label}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="px-3 py-2 text-[11px] text-white/45">No incoming edges</div>
                )}

                <div className="mt-2">
                  <button
                    className="w-full rounded-xl px-3 py-2 text-left text-[11px] text-red-200 hover:bg-red-500/15"
                    onClick={() => {
                      setFieldBinding(bindMenu.fieldKey, undefined);
                      setBindMenu({ open: false });
                    }}
                  >
                    Clear binding
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {/* Click-catcher for pane menu */}
        {menu.open ? (
          <button
            className="absolute inset-0 z-40 cursor-default"
            onClick={() => setMenu({ open: false })}
            aria-label="Close context menu"
          />
        ) : null}
      </div>
    </div>
  );
}

/* ------------------------------ UI components ------------------------------ */

function TopPill({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex h-10 items-center gap-2 rounded-2xl border border-[hsl(var(--tp-border))] bg-black/10 px-3 text-[11px] font-semibold text-white/85",
        "shadow-[0_18px_50px_rgba(0,0,0,0.55)] backdrop-blur-2xl hover:bg-white/5",
        className,
      )}
    >
      {children}
    </button>
  );
}

function IconButton({
  title,
  onClick,
  children,
}: {
  title: string;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={cn(
        "inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[hsl(var(--tp-border))] bg-black/10",
        "shadow-[0_18px_50px_rgba(0,0,0,0.55)] backdrop-blur-2xl hover:bg-white/5",
      )}
    >
      {children}
    </button>
  );
}

function MiniTool({
  title,
  onClick,
  children,
}: {
  title: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[hsl(var(--tp-border))] bg-black/10 text-white/85 shadow-[0_18px_50px_rgba(0,0,0,0.55)] backdrop-blur-2xl hover:bg-white/5"
    >
      {children}
    </button>
  );
}

function SideToggleButton({
  side,
  title,
  onClick,
  children,
}: {
  side: "left" | "right";
  title: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={cn(
        "absolute top-1/2 z-40 -translate-y-1/2 rounded-2xl border border-[hsl(var(--tp-border))] bg-black/35 p-2 shadow-[0_18px_50px_rgba(0,0,0,0.55)] backdrop-blur-2xl hover:bg-white/10",
        side === "left" ? "left-3" : "right-3",
      )}
    >
      {children}
    </button>
  );
}

function SidePanel({
  side,
  title,
  subtitle,
  onClose,
  children,
}: {
  side: "left" | "right";
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "absolute inset-y-0 z-40 w-[360px] overflow-hidden border border-[hsl(var(--tp-border))] bg-black/20 shadow-[0_18px_50px_rgba(0,0,0,0.55)] backdrop-blur-2xl",
        side === "left" ? "left-0 border-l-0 rounded-r-2xl" : "right-0 border-r-0 rounded-l-2xl",
      )}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div className="min-w-0">
          <div className="text-[12px] font-semibold text-white/90">{title}</div>
          {subtitle ? <div className="mt-0.5 truncate text-[10px] text-white/45">{subtitle}</div> : null}
        </div>

        <button
          type="button"
          className="inline-flex h-9 w-9 items-center justify-center rounded-2xl border border-[hsl(var(--tp-border))] bg-black/20 text-white/70 hover:text-white"
          onClick={onClose}
          title="Close"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="h-[calc(100%-52px)]">
        <ScrollArea className="h-full">
          <div className="p-4">{children}</div>
        </ScrollArea>
      </div>
    </div>
  );
}

function GlobalsPanel({
  vars,
  setVars,
}: {
  vars: GlobalVar[];
  setVars: React.Dispatch<React.SetStateAction<GlobalVar[]>>;
}) {
  return (
    <div className="space-y-4">
      <div className="text-[11px] text-white/55">Название — значение (публичные переменные)</div>

      <div className="space-y-2">
        {vars.map((v) => (
          <div key={v.id} className="grid grid-cols-[1fr_1fr_36px] items-center gap-2">
            <Input
              value={v.name}
              onChange={(e) =>
                setVars((prev) => prev.map((x) => (x.id === v.id ? { ...x, name: e.target.value } : x)))
              }
              className="h-10 rounded-xl border-[hsl(var(--tp-border))] bg-black/10 text-[11px] text-white/90"
              placeholder="name"
            />
            <Input
              value={v.value}
              onChange={(e) =>
                setVars((prev) => prev.map((x) => (x.id === v.id ? { ...x, value: e.target.value } : x)))
              }
              className="h-10 rounded-xl border-[hsl(var(--tp-border))] bg-black/10 text-[11px] text-white/90"
              placeholder="value"
            />
            <button
              type="button"
              title="Delete"
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[hsl(var(--tp-border))] bg-black/10 text-white/60 hover:text-white"
              onClick={() => setVars((prev) => prev.filter((x) => x.id !== v.id))}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      <Button
        type="button"
        variant="outline"
        className="h-10 rounded-xl bg-black/10 text-[11px]"
        onClick={() => setVars((prev) => [...prev, { id: uid("gv"), name: "var", value: "" }])}
      >
        <Plus className="mr-2 h-4 w-4" />
        Add variable
      </Button>
    </div>
  );
}

function NodesListPanel({
  nodes,
  search,
  setSearch,
  selectedId,
  onSelect,
  onAdd,
}: {
  nodes: Node<AgentNodeData>[];
  search: string;
  setSearch: (v: string) => void;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAdd: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 rounded-2xl border border-[hsl(var(--tp-border))] bg-black/10 px-3 py-2">
        <Search className="h-4 w-4 text-white/55" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-6 w-full bg-transparent text-[11px] text-white/85 outline-none placeholder:text-white/35"
          placeholder="Search nodes…"
        />
      </div>

      <div className="flex items-center justify-between">
        <div className="text-[10px] font-semibold text-white/60">Nodes ({nodes.length})</div>
        <Button type="button" variant="outline" className="h-8 rounded-xl bg-black/10 px-3 text-[11px]" onClick={onAdd}>
          <Plus className="mr-2 h-4 w-4" />
          Add
        </Button>
      </div>

      <div className="space-y-2">
        {nodes.map((n) => (
          <button
            key={n.id}
            type="button"
            onClick={() => onSelect(n.id)}
            className={cn(
              "w-full rounded-2xl border bg-black/10 px-3 py-2 text-left transition-colors",
              selectedId === n.id
                ? "border-[hsl(var(--tp-blue))]"
                : "border-[hsl(var(--tp-border))] hover:bg-white/5",
            )}
          >
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: kindDot(n.data.kind) }} />
              <div className="truncate text-[11px] font-semibold text-white/90">{n.data.title}</div>
            </div>
            <div className="mt-0.5 truncate text-[10px] text-white/45">{n.data.tag ?? n.data.kind}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

function NodeSettingsPanel({
  node,
  edges,
  bindSources,
  onDeselect,
  onDelete,
  onUpdate,
  onOpenBindMenu,
}: {
  node: Node<AgentNodeData>;
  edges: Edge[];
  bindSources: {
    globalsList: Array<{ id: string; label: string }>;
    connected: Array<{ edgeId: string; label: string }>;
  };
  onDeselect: () => void;
  onDelete: () => void;
  onUpdate: (updater: (prev: AgentNodeData) => AgentNodeData) => void;
  onOpenBindMenu: (fieldKey: string, rect: DOMRect) => void;
}) {
  const [fields, setFields] = React.useState<SettingField[] | null>(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    setLoading(true);
    requestSettingsSchema(node.data.kind)
      .then((f) => setFields(f))
      .finally(() => setLoading(false));
  }, [node.data.kind, node.id]);

  const bindings = node.data.config.bindings ?? {};

  const getFieldValue = (key: string) => {
    if (key === "title") return node.data.title;
    return (node.data.config as any)[key];
  };

  const setFieldValue = (key: string, value: any) => {
    onUpdate((prev) => {
      if (key === "title") return { ...prev, title: String(value) };
      return { ...prev, config: { ...prev.config, [key]: value } };
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: kindDot(node.data.kind) }} />
            <div className="truncate text-[12px] font-semibold text-white/90">{node.data.title}</div>
          </div>
          <div className="mt-1 text-[10px] text-white/45">Double click an edge to edit its label.</div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="inline-flex h-9 items-center justify-center rounded-2xl border border-[hsl(var(--tp-border))] bg-black/10 px-3 text-[11px] text-white/80 hover:bg-white/5"
            onClick={onDeselect}
            title="Close selection"
          >
            <X className="mr-2 h-4 w-4" />
            Unselect
          </button>

          <button
            type="button"
            className="inline-flex h-9 items-center justify-center rounded-2xl border border-[hsl(var(--tp-border))] bg-black/10 px-3 text-[11px] text-red-200 hover:bg-red-500/15"
            onClick={onDelete}
            title="Delete node"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </button>
        </div>
      </div>

      <div className="h-px bg-white/10" />

      {loading || !fields ? (
        <div className="space-y-3">
          <div className="h-4 w-44 animate-pulse rounded bg-white/10" />
          <div className="h-10 w-full animate-pulse rounded bg-white/5" />
          <div className="h-10 w-full animate-pulse rounded bg-white/5" />
          <div className="h-28 w-full animate-pulse rounded bg-white/5" />
        </div>
      ) : (
        <div className="space-y-4">
          {fields.map((f) => (
            <FieldRow
              key={f.key}
              field={f}
              value={getFieldValue(f.key)}
              binding={bindings[f.key]}
              onChange={(v) => setFieldValue(f.key, v)}
              onBind={(el) => {
                const rect = el.getBoundingClientRect();
                onOpenBindMenu(f.key, rect);
              }}
            />
          ))}

          <div className="rounded-2xl border border-[hsl(var(--tp-border))] bg-black/10 p-3">
            <div className="text-[10px] font-semibold text-white/60">Incoming edges</div>
            <div className="mt-2 space-y-1 text-[11px] text-white/75">
              {edges.length ? (
                edges.map((e) => (
                  <div key={e.id} className="flex items-center justify-between gap-2">
                    <span className="truncate">{e.sourceHandle ?? "out"} → {e.targetHandle ?? "in"}</span>
                    <span className="text-white/40">{String(e.label ?? "")}</span>
                  </div>
                ))
              ) : (
                <div className="text-white/45">No incoming edges</div>
              )}
            </div>

            <div className="mt-3 text-[10px] text-white/45">
              Для привязки настройки к выходу другой ноды — сначала соедините ноды, потом нажмите
              кнопку “link” у нужного поля.
            </div>
          </div>

          {/* Small hint about available bind sources */}
          <div className="text-[10px] text-white/35">
            Available globals: {bindSources.globalsList.length}. Connected outputs: {bindSources.connected.length}.
          </div>
        </div>
      )}
    </div>
  );
}

function FieldRow({
  field,
  value,
  binding,
  onChange,
  onBind,
}: {
  field: SettingField;
  value: any;
  binding?: FieldBinding;
  onChange: (v: any) => void;
  onBind: (el: HTMLButtonElement) => void;
}) {
  const bindingLabel =
    binding?.type === "global"
      ? "bound: global"
      : binding?.type === "edge"
        ? "bound: edge"
        : "";

  return (
    <div className="flex items-start gap-2">
      <div className="flex-1">
        <div className="flex items-center justify-between gap-2">
          <div className="text-[11px] text-white/70">{field.label}</div>
          {bindingLabel ? <div className="text-[10px] text-white/40">{bindingLabel}</div> : null}
        </div>

        {field.type === "textarea" ? (
          <textarea
            value={value ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="mt-1 min-h-[96px] w-full resize-none rounded-xl border border-[hsl(var(--tp-border))] bg-black/10 px-3 py-2 text-[11px] text-white/90 outline-none placeholder:text-white/40"
          />
        ) : field.type === "number" ? (
          <Input
            type="number"
            value={value ?? 0}
            onChange={(e) => onChange(Number(e.target.value || 0))}
            className="mt-1 h-10 rounded-xl border-[hsl(var(--tp-border))] bg-black/10 text-[11px] text-white/90"
          />
        ) : field.type === "toggle" ? (
          <div className="mt-1 flex h-10 items-center rounded-xl border border-[hsl(var(--tp-border))] bg-black/10 px-3">
            <input
              type="checkbox"
              checked={Boolean(value)}
              onChange={(e) => onChange(e.target.checked)}
              className="h-4 w-4"
            />
          </div>
        ) : (
          <Input
            value={value ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="mt-1 h-10 rounded-xl border-[hsl(var(--tp-border))] bg-black/10 text-[11px] text-white/90"
          />
        )}
      </div>

      <button
        type="button"
        title="Bind to global variable / connected output"
        className="mt-5 inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[hsl(var(--tp-border))] bg-black/10 text-white/70 hover:bg-white/5 hover:text-white"
        onClick={(e) => {
          e.stopPropagation();
          onBind(e.currentTarget);
        }}
      >
        <Link2 className="h-4 w-4" />
      </button>
    </div>
  );
}
