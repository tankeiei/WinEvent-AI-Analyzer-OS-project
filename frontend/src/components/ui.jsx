import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as AlertDialogPrimitive from "@radix-ui/react-alert-dialog";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { Command as CommandPrimitive } from "cmdk";
import { X } from "lucide-react";
import { cn } from "../lib/utils";

export function Button({ className, variant = "default", size = "default", ...props }) {
  const variants = {
      default: "bg-cyan-200 text-slate-950 hover:bg-cyan-100 shadow-[0_10px_26px_rgba(34,211,238,0.12)]",
    secondary: "bg-white/[0.08] text-slate-100 hover:bg-white/[0.13] border border-white/10",
    ghost: "text-slate-300 hover:bg-white/[0.07] hover:text-white",
    danger: "bg-rose-500/15 text-rose-200 border border-rose-400/25 hover:bg-rose-500/25",
    warning: "bg-amber-400/12 text-amber-100 border border-amber-300/20 hover:bg-amber-400/20",
  };
  const sizes = {
    default: "h-10 px-4 text-sm",
    sm: "h-8 rounded-lg px-3 text-xs",
    icon: "h-9 w-9 p-0",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/80 disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  );
}

export function Card({ className, ...props }) {
  return <div className={cn("rounded-2xl border border-slate-400/10 bg-[#0A1322]/90 shadow-[0_18px_60px_rgba(2,8,23,0.20)]", className)} {...props} />;
}

export function Badge({ className, tone = "neutral", ...props }) {
  const tones = {
    neutral: "border-white/10 bg-white/[0.06] text-slate-300",
    cyan: "border-cyan-300/20 bg-cyan-300/10 text-cyan-100",
    red: "border-rose-300/25 bg-rose-400/10 text-rose-100",
    amber: "border-amber-300/25 bg-amber-400/10 text-amber-100",
    violet: "border-violet-300/25 bg-violet-400/10 text-violet-100",
    green: "border-emerald-300/25 bg-emerald-400/10 text-emerald-100",
  };
  return <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.13em]", tones[tone], className)} {...props} />;
}

export const Tabs = TabsPrimitive.Root;
export const TabsList = ({ className, ...props }) => <TabsPrimitive.List className={cn("inline-flex rounded-xl border border-slate-400/10 bg-slate-950/60 p-1", className)} {...props} />;
export const TabsTrigger = ({ className, ...props }) => <TabsPrimitive.Trigger className={cn("rounded-lg px-3 py-2 text-xs font-semibold text-slate-400 transition-colors hover:text-slate-100 data-[state=active]:bg-cyan-300/10 data-[state=active]:text-cyan-100 data-[state=active]:shadow-[inset_0_0_0_1px_rgba(103,232,249,.16)]", className)} {...props} />;
export const TabsContent = ({ className, ...props }) => <TabsPrimitive.Content className={cn("mt-4 outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/70", className)} {...props} />;

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export function DialogContent({ className, children, ...props }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-slate-950/75 backdrop-blur-sm" />
      <DialogPrimitive.Content className={cn("fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-white/10 bg-[#0c1728] p-6 text-slate-100 shadow-2xl focus:outline-none", className)} {...props}>
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded-lg p-1 text-slate-500 transition hover:bg-white/10 hover:text-white focus:outline-none focus:ring-2 focus:ring-cyan-300/70">
          <X className="h-4 w-4" />
          <span className="sr-only">ปิด</span>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
export const DialogTitle = DialogPrimitive.Title;
export const DialogDescription = DialogPrimitive.Description;

export const AlertDialog = AlertDialogPrimitive.Root;
export const AlertDialogTrigger = AlertDialogPrimitive.Trigger;
export const AlertDialogCancel = AlertDialogPrimitive.Cancel;
export const AlertDialogAction = AlertDialogPrimitive.Action;
export const AlertDialogTitle = AlertDialogPrimitive.Title;
export const AlertDialogDescription = AlertDialogPrimitive.Description;
export function AlertDialogContent({ className, children, ...props }) {
  return (
    <AlertDialogPrimitive.Portal>
      <AlertDialogPrimitive.Overlay className="fixed inset-0 z-40 bg-slate-950/75 backdrop-blur-sm" />
      <AlertDialogPrimitive.Content className={cn("fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-white/10 bg-[#0c1728] p-6 text-slate-100 shadow-2xl focus:outline-none", className)} {...props}>
        {children}
      </AlertDialogPrimitive.Content>
    </AlertDialogPrimitive.Portal>
  );
}

export function Skeleton({ className, ...props }) {
  return <div className={cn("animate-pulse rounded-xl bg-white/[0.08]", className)} {...props} />;
}

export function Separator({ className, ...props }) {
  return <div className={cn("h-px w-full bg-white/[0.08]", className)} {...props} />;
}

export function CommandDialog({ open, onOpenChange, children }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="overflow-hidden p-0">
        <CommandPrimitive className="flex max-h-[min(520px,80vh)] flex-col overflow-hidden rounded-2xl bg-[#0c1728] text-slate-100">
          {children}
        </CommandPrimitive>
      </DialogContent>
    </Dialog>
  );
}

export function CommandInput({ className, ...props }) {
  return <CommandPrimitive.Input className={cn("h-12 w-full border-b border-white/[0.08] bg-transparent px-4 text-sm outline-none placeholder:text-slate-600", className)} {...props} />;
}

export function CommandList({ className, ...props }) {
  return <CommandPrimitive.List className={cn("max-h-[360px] overflow-y-auto p-2", className)} {...props} />;
}

export function CommandEmpty({ className, ...props }) {
  return <CommandPrimitive.Empty className={cn("py-8 text-center text-xs text-slate-500", className)} {...props} />;
}

export function CommandGroup({ className, ...props }) {
  return <CommandPrimitive.Group className={cn("overflow-hidden p-1 text-slate-400 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-bold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.15em]", className)} {...props} />;
}

export function CommandItem({ className, ...props }) {
  return <CommandPrimitive.Item className={cn("flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-xs text-slate-300 outline-none data-[selected=true]:bg-cyan-300/10 data-[selected=true]:text-cyan-100", className)} {...props} />;
}
