import * as React from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Edge,
  Handle,
  Node,
  NodeProps,
  Position,
  ReactFlowProvider,
  applyEdgeChanges,
  applyNodeChanges,
} from "reactflow";
import "reactflow/dist/style.css";

import {
  ArrowLeft,
  ChevronDown,
  Circle,
  Image as ImageIcon,
  Layers,
  Play,
  Plus,
  Send,
  Settings2,
  Share2,
  Sparkles,
  Wand2,
} from "lucide-react";

import { cn } from "@/lib/utils";

type Dot = {
  label: string;
  color: string;
};

type TPNodeData = {
  title: string;
  subtitle?: string;
  dots?: Dot[];
  body?: React.ReactNode;
};

function TPNode({ data }: NodeProps<TPNodeData>) {
  return (
    <div className="min-w-[220px] max-w-[260px] rounded-[18px] border border-[#2a2a2c] bg-[#1c1c1e] shadow-[0_25px_80px_rgba(0,0,0,0.65)]">
      <div className="flex items-start justify-between gap-3 border-b border-[#2a2a2c] px-4 py-3">
        <div>
          <div className="text-[12px] font-semibold text-white/90">{data.title}</div>
          {data.subtitle && <div className="mt-0.5 text-[10px] text-white/45">{data.subtitle}</div>}
        </div>
        {data.dots && data.dots.length > 0 && (
          <div className="flex flex-wrap items-center justify-end gap-2">
            {data.dots.map((d) => (
              <div key={d.label} className="inline-flex items-center gap-1 rounded-full border border-[#2a2a2c] bg-[#151517] px-2 py-0.5 text-[10px] text-white/70">
                <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: d.color }} />
                {d.label}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="px-4 py-3 text-[11px] text-white/75">{data.body}</div>

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2.5 !w-2.5 !border !border-[#2a2a2c] !bg-[#0f0f10]"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!h-2.5 !w-2.5 !border !border-[#2a2a2c] !bg-[#0f0f10]"
      />
    </div>
  );
}

const nodeTypes = {
  tp: TPNode,
};

const initialNodes: Node<TPNodeData>[] = [
  {
    id: "model",
    type: "tp",
    position: { x: 60, y: 220 },
    data: {
      title: "Model",
      subtitle: "Select an inference model",
      dots: [{ label: "DreamShaper", color: "#4054b4" }],
      body: (
        <div className="space-y-2">
          <div className="flex items-center justify-between rounded-xl border border-[#2a2a2c] bg-[#151517] px-3 py-2">
            <div className="text-[11px] text-white/80">DreamShaper (SD 1.5)</div>
            <div className="inline-flex items-center gap-1 rounded-full bg-[#283454] px-2 py-0.5 text-[10px] text-[#acb3c8]">
              <Circle className="h-2.5 w-2.5 fill-[#acb3c8] text-[#acb3c8]" />
              local
            </div>
          </div>
          <div className="text-[10px] text-white/45">Change model in the right panel</div>
        </div>
      ),
    },
  },
  {
    id: "prompt-pos",
    type: "tp",
    position: { x: 360, y: 150 },
    data: {
      title: "Prompt",
      subtitle: "Positive",
      dots: [{ label: "Generate", color: "#56a18a" }],
      body: (
        <div className="space-y-2">
          <div className="rounded-xl border border-[#2a2a2c] bg-[#151517] px-3 py-2 text-[11px] text-white/80">
            A black cat with pink coat, minimal style, soft glow.
          </div>
          <div className="text-[10px] text-white/45">Type what you want to get</div>
        </div>
      ),
    },
  },
  {
    id: "prompt-neg",
    type: "tp",
    position: { x: 360, y: 340 },
    data: {
      title: "Negative",
      subtitle: "Avoid",
      dots: [{ label: "No", color: "#c05b5b" }],
      body: (
        <div className="space-y-2">
          <div className="rounded-xl border border-[#2a2a2c] bg-[#151517] px-3 py-2 text-[11px] text-white/75">
            Low-res, unnecessary details, background clutter, watermark.
          </div>
          <div className="text-[10px] text-white/45">What model should not generate</div>
        </div>
      ),
    },
  },
  {
    id: "generator",
    type: "tp",
    position: { x: 690, y: 235 },
    data: {
      title: "Image Generator",
      subtitle: "Settings",
      dots: [{ label: "1024", color: "#8a79d6" }],
      body: (
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-xl border border-[#2a2a2c] bg-[#151517] px-3 py-2">
            <div className="text-[10px] text-white/45">Steps</div>
            <div className="text-[11px] text-white/80">30</div>
          </div>
          <div className="rounded-xl border border-[#2a2a2c] bg-[#151517] px-3 py-2">
            <div className="text-[10px] text-white/45">Scale</div>
            <div className="text-[11px] text-white/80">7.5</div>
          </div>
          <div className="rounded-xl border border-[#2a2a2c] bg-[#151517] px-3 py-2">
            <div className="text-[10px] text-white/45">Seed</div>
            <div className="text-[11px] text-white/80">Random</div>
          </div>
          <div className="rounded-xl border border-[#2a2a2c] bg-[#151517] px-3 py-2">
            <div className="text-[10px] text-white/45">Sampler</div>
            <div className="text-[11px] text-white/80">DPM++</div>
          </div>
        </div>
      ),
    },
  },
];

const initialEdges: Edge[] = [
  {
    id: "e1",
    source: "model",
    target: "prompt-pos",
    animated: false,
    style: { stroke: "rgba(255,255,255,0.28)", strokeWidth: 1.2 },
  },
  {
    id: "e2",
    source: "prompt-pos",
    target: "generator",
    style: { stroke: "rgba(255,255,255,0.28)", strokeWidth: 1.2 },
  },
  {
    id: "e3",
    source: "prompt-neg",
    target: "generator",
    style: { stroke: "rgba(255,255,255,0.28)", strokeWidth: 1.2 },
  },
];

export function WorkflowBuilderPage() {
  const [nodes, setNodes] = React.useState(initialNodes);
  const [edges, setEdges] = React.useState(initialEdges);

  return (
    <div className="h-full">
      <div
        className="relative h-full overflow-hidden rounded-[22px] border border-[hsl(var(--tp-border))]"
        style={{
          backgroundColor: "#171717",
          backgroundImage:
            "radial-gradient(circle, rgba(255,255,255,0.07) 1px, transparent 1px)",
          backgroundSize: "22px 22px",
        }}
      >
        {/* Top toolbar */}
        <div className="absolute left-4 top-4 z-20 flex items-center gap-2">
          <TopPill>
            <Sparkles className="h-4 w-4" />
            Workflow
          </TopPill>
          <TopPill>Edit</TopPill>
          <TopPill>Help</TopPill>
        </div>

        <div className="absolute left-1/2 top-4 z-20 flex -translate-x-1/2 items-center gap-2">
          <IconPill>
            <ArrowLeft className="h-4 w-4" />
          </IconPill>
          <TopPill className="min-w-[180px] justify-center">
            my_agent_generation_v2
          </TopPill>
        </div>

        <div className="absolute right-4 top-4 z-20 flex items-center gap-2">
          <TopPill className="gap-2">
            <Play className="h-4 w-4" />
            Run
            <ChevronDown className="h-4 w-4 opacity-70" />
          </TopPill>
          <IconPill>
            <Settings2 className="h-4 w-4" />
          </IconPill>
          <TopPill className="bg-white text-black hover:bg-white/90">
            <Share2 className="h-4 w-4" />
            Share
          </TopPill>
          <TopPill className="border-[#2a2a2c] bg-[#1c1c1e]">
            Make Public
          </TopPill>
        </div>

        {/* Left collaborators */}
        <div className="absolute left-4 top-20 z-20 flex items-center gap-2">
          <AvatarDot label="JD" />
          <AvatarDot label="AI" />
        </div>

        {/* Right preview */}
        <div className="absolute right-4 top-24 z-20 w-[300px]">
          <div className="overflow-hidden rounded-[18px] border border-[#2a2a2c] bg-[#1c1c1e] shadow-[0_25px_80px_rgba(0,0,0,0.65)]">
            <div className="border-b border-[#2a2a2c] p-3">
              <div className="text-[11px] font-semibold text-white/80">Preview image</div>
            </div>
            <div className="p-3">
              <div className="relative aspect-[4/3] overflow-hidden rounded-[14px] border border-[#2a2a2c] bg-gradient-to-b from-white/10 to-white/0">
                <div className="absolute inset-0 flex items-center justify-center text-white/50">
                  <ImageIcon className="h-6 w-6" />
                </div>
              </div>
              <div className="mt-3 space-y-1">
                <div className="text-[12px] font-semibold text-white/90">final_result</div>
                <div className="text-[10px] text-white/45">
                  Minimal, soft glow, smooth. Click nodes to edit their parameters.
                </div>
              </div>
            </div>
          </div>

          <div className="mt-3 flex justify-end gap-2">
            <MiniTool>
              <Layers className="h-4 w-4" />
            </MiniTool>
            <MiniTool>
              <Wand2 className="h-4 w-4" />
            </MiniTool>
            <MiniTool>
              <Plus className="h-4 w-4" />
            </MiniTool>
          </div>
        </div>

        {/* Bottom prompt bar */}
        <div className="absolute bottom-4 left-1/2 z-20 w-[480px] -translate-x-1/2">
          <div className="flex items-center gap-2 rounded-[18px] border border-[#2a2a2c] bg-[#1c1c1e] px-3 py-2 shadow-[0_25px_80px_rgba(0,0,0,0.65)]">
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl border border-[#2a2a2c] bg-[#151517] text-white/80">
              <Sparkles className="h-4 w-4" />
            </div>
            <input
              className="h-9 w-full bg-transparent text-[11px] text-white/85 outline-none placeholder:text-white/35"
              placeholder="Describe your task, then connect nodes to build an agent…"
            />
            <button className="flex h-9 w-9 items-center justify-center rounded-2xl bg-[#4054b4] text-white shadow-[0_10px_30px_rgba(64,84,180,0.35)] hover:brightness-110">
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* React Flow canvas */}
        <div className="absolute inset-0">
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={(changes) => setNodes((nds) => applyNodeChanges(changes, nds))}
              onEdgesChange={(changes) => setEdges((eds) => applyEdgeChanges(changes, eds))}
              fitView
              proOptions={{ hideAttribution: true }}
              nodesDraggable
              zoomOnScroll
              panOnScroll
              className="!bg-transparent"
            >
              <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="rgba(255,255,255,0.09)" />
            </ReactFlow>
          </ReactFlowProvider>
        </div>
      </div>
    </div>
  );
}

function TopPill({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div
      className={cn(
        "inline-flex h-9 items-center gap-2 rounded-[14px] border border-[#2a2a2c] bg-[#1c1c1e] px-3 text-[11px] font-semibold text-white/85 shadow-[0_25px_80px_rgba(0,0,0,0.65)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

function IconPill({ children }: { children: React.ReactNode }) {
  return (
    <div className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] border border-[#2a2a2c] bg-[#1c1c1e] text-white/80 shadow-[0_25px_80px_rgba(0,0,0,0.65)]">
      {children}
    </div>
  );
}

function MiniTool({ children }: { children: React.ReactNode }) {
  return (
    <button className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] border border-[#2a2a2c] bg-[#1c1c1e] text-white/70 shadow-[0_25px_80px_rgba(0,0,0,0.65)] hover:text-white">
      {children}
    </button>
  );
}

function AvatarDot({ label }: { label: string }) {
  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-2xl border border-[#2a2a2c] bg-[#1c1c1e] text-[10px] font-semibold text-white/80 shadow-[0_25px_80px_rgba(0,0,0,0.65)]">
      {label}
    </div>
  );
}
