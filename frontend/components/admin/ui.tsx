"use client";

import Link from "next/link";
import {
  type ChangeEvent,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { CatalogImage } from "@/components/CatalogImage";
import { STATUS_LABEL } from "@/lib/admin/rules";
import type { Status } from "@/lib/admin/types";

type FieldShell = { label: string; error?: string | null; hint?: ReactNode };

/** Une etiqueta, ayuda y error con el control por `aria-describedby`. */
function useFieldIds(error?: string | null, hint?: ReactNode) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  return { id, hintId, errorId, describedBy: [errorId, hintId].filter(Boolean).join(" ") || undefined };
}

function FieldNotes({ error, hint, errorId, hintId }: FieldShell & { errorId?: string; hintId?: string }) {
  return (
    <>
      {error ? (
        <p id={errorId} className="a-error">
          {error}
        </p>
      ) : null}
      {hint ? (
        <p id={hintId} className="a-hint">
          {hint}
        </p>
      ) : null}
    </>
  );
}

type TextFieldProps = FieldShell &
  Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange"> & {
    value: string;
    onChange: (value: string) => void;
  };

export function TextField({ label, error, hint, value, onChange, className, ...rest }: TextFieldProps) {
  const { id, hintId, errorId, describedBy } = useFieldIds(error, hint);
  return (
    <div className={className}>
      <label htmlFor={id} className="a-label">
        {label}
      </label>
      <input
        id={id}
        className="a-input"
        value={value}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        onChange={(event: ChangeEvent<HTMLInputElement>) => onChange(event.target.value)}
        {...rest}
      />
      <FieldNotes error={error} hint={hint} errorId={errorId} hintId={hintId} label={label} />
    </div>
  );
}

type TextAreaProps = FieldShell &
  Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "value" | "onChange"> & {
    value: string;
    onChange: (value: string) => void;
  };

export function TextAreaField({ label, error, hint, value, onChange, className, rows = 4, ...rest }: TextAreaProps) {
  const { id, hintId, errorId, describedBy } = useFieldIds(error, hint);
  return (
    <div className={className}>
      <label htmlFor={id} className="a-label">
        {label}
      </label>
      <textarea
        id={id}
        rows={rows}
        className="a-input"
        value={value}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        onChange={(event) => onChange(event.target.value)}
        {...rest}
      />
      <FieldNotes error={error} hint={hint} errorId={errorId} hintId={hintId} label={label} />
    </div>
  );
}

type SelectProps = FieldShell &
  Omit<SelectHTMLAttributes<HTMLSelectElement>, "value" | "onChange"> & {
    value: string;
    onChange: (value: string) => void;
    children: ReactNode;
  };

export function SelectField({ label, error, hint, value, onChange, className, children, ...rest }: SelectProps) {
  const { id, hintId, errorId, describedBy } = useFieldIds(error, hint);
  return (
    <div className={className}>
      <label htmlFor={id} className="a-label">
        {label}
      </label>
      <select
        id={id}
        className="a-input"
        value={value}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        onChange={(event) => onChange(event.target.value)}
        {...rest}
      >
        {children}
      </select>
      <FieldNotes error={error} hint={hint} errorId={errorId} hintId={hintId} label={label} />
    </div>
  );
}

export function CheckField({
  label,
  checked,
  onChange,
  hint,
  className = "",
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  hint?: ReactNode;
  className?: string;
}) {
  const id = useId();
  return (
    <div className={className}>
      <label htmlFor={id} className="inline-flex min-h-10 cursor-pointer items-center gap-2">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          aria-describedby={hint ? `${id}-hint` : undefined}
          onChange={(event) => onChange(event.target.checked)}
        />
        {label}
      </label>
      {hint ? (
        <p id={`${id}-hint`} className="a-hint mt-0">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function StatusLabel({ status }: { status: Status }) {
  return (
    <span className="a-status" data-status={status}>
      {STATUS_LABEL[status]}
    </span>
  );
}

export function PageHead({ title, children, back }: { title: string; children?: ReactNode; back?: { href: string; label: string } }) {
  return (
    <>
      {back ? (
        <p className="mb-1">
          <Link href={back.href} prefetch={false} className="link">
            {back.label}
          </Link>
        </p>
      ) : null}
      <div className="a-page-head">
        <h1 className="a-h1">{title}</h1>
        {children ? <div className="flex flex-wrap items-center gap-2">{children}</div> : null}
      </div>
    </>
  );
}

/** Estado vacío con la siguiente acción. */
export function Empty({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <div className="py-10">
      <p className="serif measure text-22">{message}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

/** Mensaje de resultado de una acción, anunciado por lectores de pantalla. */
export function Notice({ kind, children }: { kind: "error" | "ok"; children: ReactNode }) {
  return kind === "error" ? (
    <p role="alert" className="a-alert">
      {children}
    </p>
  ) : (
    <p role="status" className="a-notice">
      {children}
    </p>
  );
}

export function Thumb({
  src,
  alt = "",
  size = "3.5rem",
  ratio = "4 / 5",
  sizes = "96px",
  contain,
  emptyLabel = "Sin foto",
}: {
  src: string | null | undefined;
  alt?: string;
  size?: string;
  ratio?: string;
  sizes?: string;
  contain?: boolean;
  emptyLabel?: string;
}) {
  return (
    <span className="a-thumb" style={{ width: size, aspectRatio: ratio }}>
      {src ? (
        <CatalogImage src={src} alt={alt} sizes={sizes} className={contain ? "object-contain" : "object-cover"} />
      ) : (
        <span className="a-no-photo" style={{ fontSize: "0.75rem" }}>
          {emptyLabel || <span className="sr-only">Sin foto</span>}
        </span>
      )}
    </span>
  );
}

type ConfirmOptions = {
  title: string;
  body?: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
};

/**
 * Confirmación con `<dialog>`: foco atrapado, Esc y retorno de foco nativos.
 * `const [confirm, dialog] = useConfirm()`; renderizar `dialog` y usar `await confirm({...})`.
 */
export function useConfirm(): [(options: ConfirmOptions) => Promise<boolean>, ReactNode] {
  const ref = useRef<HTMLDialogElement>(null);
  const resolver = useRef<((value: boolean) => void) | null>(null);
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const titleId = useId();

  useEffect(() => {
    if (options && !ref.current?.open) ref.current?.showModal();
  }, [options]);

  const finish = (value: boolean) => {
    ref.current?.close();
    resolver.current?.(value);
    resolver.current = null;
    setOptions(null);
  };

  const confirm = useCallback(
    (next: ConfirmOptions) =>
      new Promise<boolean>((resolve) => {
        resolver.current = resolve;
        setOptions(next);
      }),
    [],
  );

  const node = options ? (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      className="a-dialog"
      onCancel={(event) => {
        event.preventDefault();
        finish(false);
      }}
    >
      <h2 id={titleId} className="a-h2">
        {options.title}
      </h2>
      {options.body ? <div className="mt-2">{options.body}</div> : null}
      <div className="mt-5 flex flex-wrap justify-end gap-2">
        <button type="button" className="a-btn a-btn-quiet" onClick={() => finish(false)}>
          {options.cancelLabel ?? "Cancelar"}
        </button>
        <button type="button" className="a-btn a-btn-primary" onClick={() => finish(true)}>
          {options.confirmLabel}
        </button>
      </div>
    </dialog>
  ) : null;

  return [confirm, node];
}

const LEAVE_MESSAGE = "Hay cambios sin guardar. ¿Salir sin guardar?";

/** Avisa al cerrar la pestaña y al seguir enlaces internos, que el router no permite interceptar. */
export function useUnsavedWarning(dirty: boolean) {
  useEffect(() => {
    if (!dirty) return;
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    const onClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return;
      const anchor = (event.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!anchor || anchor.target === "_blank" || anchor.hasAttribute("download")) return;
      if (!window.confirm(LEAVE_MESSAGE)) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    document.addEventListener("click", onClick, true);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      document.removeEventListener("click", onClick, true);
    };
  }, [dirty]);
}

/** Arrastre nativo. El teclado usa los botones de mover, así que esto es solo para el puntero. */
export function useDragReorder(onMove: (from: number, to: number) => void) {
  const [dragging, setDragging] = useState<number | null>(null);
  const [over, setOver] = useState<number | null>(null);

  const handleProps = (index: number) => ({
    draggable: true,
    onDragStart: (event: React.DragEvent) => {
      setDragging(index);
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", String(index));
    },
    onDragEnd: () => {
      setDragging(null);
      setOver(null);
    },
  });

  const targetProps = (index: number) => ({
    "data-drop-target": over === index && dragging !== null && dragging !== index ? true : undefined,
    "data-dragging": dragging === index ? true : undefined,
    onDragOver: (event: React.DragEvent) => {
      if (dragging === null) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      if (over !== index) setOver(index);
    },
    onDrop: (event: React.DragEvent) => {
      if (dragging === null) return;
      event.preventDefault();
      if (dragging !== index) onMove(dragging, index);
      setDragging(null);
      setOver(null);
    },
  });

  return { handleProps, targetProps };
}

export function Pager({
  page,
  pageSize,
  total,
  hrefFor,
  onPage,
}: {
  page: number;
  pageSize: number;
  total: number;
  hrefFor?: (page: number) => string;
  onPage?: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  const control = (target: number, label: string, disabled: boolean) => {
    if (disabled) {
      return (
        <button type="button" className="a-btn a-btn-quiet" disabled>
          {label}
        </button>
      );
    }
    if (hrefFor) {
      return (
        <Link href={hrefFor(target)} prefetch={false} className="a-btn a-btn-quiet">
          {label}
        </Link>
      );
    }
    return (
      <button type="button" className="a-btn a-btn-quiet" onClick={() => onPage?.(target)}>
        {label}
      </button>
    );
  };
  return (
    <nav aria-label="Paginación" className="mt-4 flex flex-wrap items-center gap-3">
      {control(page - 1, "Anterior", page <= 1)}
      <span className="muted">
        Página {page} de {pages}
      </span>
      {control(page + 1, "Siguiente", page >= pages)}
    </nav>
  );
}
