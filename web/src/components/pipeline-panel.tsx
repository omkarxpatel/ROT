"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AstView } from "@/components/ast-view";
import { SnapshotTimeline } from "@/components/snapshot-timeline";
import { TokensView } from "@/components/tokens-view";
import type { AstNode, RotSnapshot, RotToken } from "@/lib/pyodide-runtime";

interface PipelinePanelProps {
  tokens: RotToken[];
  ast: AstNode | null;
  trace: string;
  // Bumped on every run so the token stagger animation re-fires.
  runKey: number;
  // Mode-aware rendering. In animate mode the Tokens accordion item
  // is dropped (it's redundant — Step Detail's per-statement Tokens
  // stage shows the same data, but scoped). A snapshot timeline is
  // shown at the top instead so the user can jump between steps.
  mode?: "run" | "animate";
  snapshots?: RotSnapshot[];
  stepIndex?: number;
  onStepChange?: (next: number) => void;
}

export function PipelinePanel({
  tokens,
  ast,
  trace,
  runKey,
  mode = "run",
  snapshots,
  stepIndex,
  onStepChange,
}: PipelinePanelProps) {
  const isAnimate = mode === "animate";
  const defaultOpen = isAnimate ? ["ast", "trace"] : ["tokens", "ast", "trace"];
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border/60 px-3 py-2 text-xs uppercase tracking-wider text-muted-foreground">
        Pipeline
      </div>
      <ScrollArea className="min-h-0 flex-1">
        {isAnimate && snapshots && onStepChange && (
          <div className="border-b border-border/60">
            <SnapshotTimeline
              snapshots={snapshots}
              stepIndex={stepIndex ?? -1}
              onStepChange={onStepChange}
            />
          </div>
        )}
        <Accordion
          type="multiple"
          defaultValue={defaultOpen}
          className="w-full"
        >
          {!isAnimate && (
            <AccordionItem value="tokens" className="border-b border-border/60">
              <AccordionTrigger>
                <span>
                  Tokens{" "}
                  {tokens.length > 0 && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      ({tokens.length})
                    </span>
                  )}
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <TokensView
                  tokens={tokens}
                  runKey={runKey}
                  empty="No tokens yet. Run the program to populate."
                />
              </AccordionContent>
            </AccordionItem>
          )}
          <AccordionItem value="ast" className="border-b border-border/60">
            <AccordionTrigger>
              <span>AST</span>
            </AccordionTrigger>
            <AccordionContent>
              <AstView ast={ast} empty="No AST yet. Run a program that parses cleanly." />
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="trace" className="border-b-0">
            <AccordionTrigger>
              <span>Trace</span>
            </AccordionTrigger>
            <AccordionContent>
              <TraceView trace={trace} />
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </ScrollArea>
    </div>
  );
}

function TraceView({ trace }: { trace: string }) {
  if (!trace) {
    return (
      <div className="text-xs text-muted-foreground">
        No trace yet. Run the program first.
      </div>
    );
  }
  return (
    <pre className="whitespace-pre-wrap font-mono text-[12px] text-foreground/80">
      {trace}
    </pre>
  );
}
