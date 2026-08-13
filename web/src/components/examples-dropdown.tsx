"use client";

import { useEffect, useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { EXAMPLES, loadExamples } from "@/lib/examples";
import { cn } from "@/lib/utils";

interface ExamplesDropdownProps {
  currentKey: string;
  onSelect: (key: string, source: string) => void;
}

export function ExamplesDropdown({
  currentKey,
  onSelect,
}: ExamplesDropdownProps) {
  const [examples, setExamples] = useState<Record<string, string> | null>(null);
  const selected = EXAMPLES.find((e) => e.key === currentKey);

  useEffect(() => {
    let cancelled = false;
    loadExamples()
      .then((e) => {
        if (!cancelled) setExamples(e);
      })
      .catch(() => {
        // Non-fatal: dropdown still renders but selection becomes a no-op
        // until the fetch succeeds. The user can keep using the default
        // source pre-loaded into the editor.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Select
      value={currentKey}
      onValueChange={(key) => {
        const src = examples?.[key];
        if (src !== undefined) onSelect(key, src);
      }}
    >
      <SelectTrigger
        className="h-8 w-[140px] text-xs"
        aria-label="Load an example"
      >
        {/* Own span instead of <SelectValue>: SelectItem wraps every
            child in Radix's ItemText, which the trigger mirrors — so
            the default echoes the blurb too and overflows the toolbar.
            Passing children to SelectValue isn't an option either;
            Radix uses that node as a portal container. */}
        <span className={cn("truncate", !selected && "text-muted-foreground")}>
          {selected?.label ?? "Examples"}
        </span>
      </SelectTrigger>
      <SelectContent>
        {EXAMPLES.map((e) => (
          <SelectItem
            key={e.key}
            value={e.key}
            textValue={e.label}
            className="text-xs"
          >
            <span className="font-medium">{e.label}</span>
            <span className="ml-2 text-muted-foreground">{e.blurb}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
