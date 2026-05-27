"use client";

import { useEffect, useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EXAMPLES, loadExamples } from "@/lib/examples";

interface ExamplesDropdownProps {
  currentKey: string;
  onSelect: (key: string, source: string) => void;
}

export function ExamplesDropdown({
  currentKey,
  onSelect,
}: ExamplesDropdownProps) {
  const [examples, setExamples] = useState<Record<string, string> | null>(null);

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
      <SelectTrigger className="h-8 w-[180px] text-xs">
        <SelectValue placeholder="Examples" />
      </SelectTrigger>
      <SelectContent>
        {EXAMPLES.map((e) => (
          <SelectItem key={e.key} value={e.key} className="text-xs">
            <span className="font-medium">{e.label}</span>
            <span className="ml-2 text-muted-foreground">{e.blurb}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
