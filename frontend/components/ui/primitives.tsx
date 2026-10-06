"use client";
// shadcn/ui-style primitives, adapted to the MAVIRA token system.
import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

/* Button ------------------------------------------------------------------ */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[5px] text-[13px] font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-pine text-white hover:bg-[#264d42]",
        secondary: "bg-surface text-ink border border-rule hover:bg-rule-2",
        ghost: "text-ink-2 hover:bg-rule-2 hover:text-ink",
        danger: "bg-sev-critical text-white hover:bg-[#741818]",
      },
      size: { sm: "h-8 px-3", md: "h-9 px-4", lg: "h-11 px-5 text-sm" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild, ...props }, ref) => {
  const Comp = asChild ? Slot : "button";
  return <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
});
Button.displayName = "Button";

/* Panel: titled section, not a decorative card ---------------------------- */
export function Panel({ title, aside, children, className, bodyClass }: {
  title?: React.ReactNode; aside?: React.ReactNode; children: React.ReactNode; className?: string; bodyClass?: string;
}) {
  return (
    <section className={cn("bg-surface border border-rule rounded-md", className)}>
      {(title || aside) && (
        <header className="flex items-baseline justify-between gap-4 border-b border-rule-2 px-5 py-3">
          {title && <h2 className="text-[15px] font-semibold">{title}</h2>}
          {aside && <div className="text-[13px] text-ink-2">{aside}</div>}
        </header>
      )}
      <div className={cn("p-5", bodyClass)}>{children}</div>
    </section>
  );
}

/* Table ------------------------------------------------------------------- */
export const Table = ({ className, ...p }: React.HTMLAttributes<HTMLTableElement>) => (
  <div className="w-full overflow-x-auto"><table className={cn("w-full border-collapse text-[13px]", className)} {...p} /></div>
);
export const Th = ({ className, ...p }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
  <th className={cn("border-b border-rule px-3 py-2 text-left text-[12px] font-semibold text-ink-2", className)} {...p} />
);
export const Td = ({ className, ...p }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
  <td className={cn("border-b border-rule-2 px-3 py-2.5 align-top", className)} {...p} />
);

/* Tabs -------------------------------------------------------------------- */
export const Tabs = TabsPrimitive.Root;
export function TabsList({ className, ...p }: React.ComponentProps<typeof TabsPrimitive.List>) {
  return <TabsPrimitive.List className={cn("flex gap-1 border-b border-rule", className)} {...p} />;
}
export function TabsTrigger({ className, ...p }: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn("-mb-px border-b-2 border-transparent px-3 py-2 text-[13px] font-semibold text-ink-3 hover:text-ink",
        "data-[state=active]:border-pine data-[state=active]:text-ink", className)}
      {...p}
    />
  );
}
export const TabsContent = ({ className, ...p }: React.ComponentProps<typeof TabsPrimitive.Content>) => (
  <TabsPrimitive.Content className={cn("pt-5 outline-none", className)} {...p} />
);

/* Dialog ------------------------------------------------------------------ */
export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export function DialogContent({ title, children, wide }: { title: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-ink/40" />
      <DialogPrimitive.Content
        className={cn("fixed left-1/2 top-1/2 z-50 max-h-[88vh] w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-md border border-rule bg-surface shadow-xl",
          wide ? "max-w-4xl" : "max-w-lg")}
      >
        <div className="flex items-center justify-between border-b border-rule-2 px-5 py-3">
          <DialogPrimitive.Title className="text-[15px] font-semibold">{title}</DialogPrimitive.Title>
          <DialogPrimitive.Close className="rounded p-1 text-ink-3 hover:bg-rule-2" aria-label="Close"><X size={16} /></DialogPrimitive.Close>
        </div>
        <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>
        <div className="p-5">{children}</div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

/* Form controls ----------------------------------------------------------- */
export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...p }, ref) => (
  <input ref={ref} className={cn("h-9 w-full rounded-[5px] border border-rule bg-surface px-3 text-[13px] placeholder:text-ink-3", className)} {...p} />
));
Input.displayName = "Input";
export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...p }, ref) => (
  <textarea ref={ref} className={cn("w-full rounded-[5px] border border-rule bg-surface px-3 py-2 text-[13px] placeholder:text-ink-3", className)} {...p} />
));
Textarea.displayName = "Textarea";
export const Select = ({ className, ...p }: React.SelectHTMLAttributes<HTMLSelectElement>) => (
  <select className={cn("h-9 rounded-[5px] border border-rule bg-surface px-2 text-[13px]", className)} {...p} />
);
export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="block text-[13px] font-semibold">{label}</span>
      {children}
      {hint && <span className="block text-[12px] text-ink-3">{hint}</span>}
    </label>
  );
}

/* States ------------------------------------------------------------------ */
export function Empty({ title, children, action }: { title: string; children?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-md border border-dashed border-rule bg-surface p-8">
      <h3 className="text-[15px] font-semibold">{title}</h3>
      {children && <div className="max-w-prose text-ink-2">{children}</div>}
      {action}
    </div>
  );
}
export function ErrorNote({ children }: { children: React.ReactNode }) {
  return <div role="alert" className="rounded-md border border-sev-critical/30 bg-sev-critical-bg px-4 py-3 text-[13px] text-sev-critical">{children}</div>;
}
export function Loading({ label = "Loading" }: { label?: string }) {
  return <div className="py-10 text-ink-3" aria-live="polite">{label}…</div>;
}
