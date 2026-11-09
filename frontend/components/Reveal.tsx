"use client";

import { useEffect, useRef, type ReactNode } from "react";

/**
 * Aparición por opacidad, 400 ms, una vez. El HTML llega visible: solo se oculta,
 * ya con JavaScript, lo que aún está fuera de pantalla. Sin JS nada queda oculto.
 */
export function Reveal({ children, className }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (el.getBoundingClientRect().top < window.innerHeight) return;
    el.style.opacity = "0";
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry?.isIntersecting) return;
      el.style.transition = "opacity 400ms ease-out";
      el.style.opacity = "1";
      observer.disconnect();
    });
    observer.observe(el);
    return () => {
      observer.disconnect();
      el.style.opacity = "";
    };
  }, []);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
