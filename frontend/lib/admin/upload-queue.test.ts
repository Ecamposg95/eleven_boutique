import { describe, expect, it } from "vitest";
import { countUploads, createUploadQueue, validateImageFile } from "./upload-queue";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("createUploadQueue", () => {
  it("nunca supera la concurrencia y procesa todo", async () => {
    let running = 0;
    let peak = 0;
    const queue = createUploadQueue<number, number>({
      concurrency: 3,
      worker: async (n) => {
        running += 1;
        peak = Math.max(peak, running);
        await tick();
        running -= 1;
        return n * 2;
      },
    });
    queue.add(Array.from({ length: 300 }, (_, i) => i));
    await queue.idle();
    expect(peak).toBe(3);
    expect(countUploads(queue.snapshot())).toMatchObject({ total: 300, done: 300, error: 0 });
    expect(queue.snapshot()[10]?.result).toBe(20);
  });

  it("un fallo no detiene a los demás y se puede reintentar", async () => {
    let fail = true;
    const queue = createUploadQueue<string, string>({
      concurrency: 1,
      worker: async (name) => {
        if (name === "b" && fail) throw new Error("rechazada");
        return name;
      },
    });
    queue.add(["a", "b", "c"]);
    await queue.idle();
    expect(queue.snapshot().map((item) => item.status)).toEqual(["done", "error", "done"]);
    expect(queue.snapshot()[1]?.error).toBe("rechazada");
    fail = false;
    queue.retryFailed();
    await queue.idle();
    expect(countUploads(queue.snapshot())).toMatchObject({ done: 3, error: 0 });
  });

  it("no intenta lo inválido ni lo reintenta", async () => {
    const seen: string[] = [];
    const queue = createUploadQueue<string, void>({
      validate: (name) => (name.endsWith(".gif") ? "Formato" : null),
      worker: async (name) => {
        seen.push(name);
      },
    });
    queue.add(["a.jpg", "b.gif"]);
    await queue.idle();
    queue.retryFailed();
    await queue.idle();
    expect(seen).toEqual(["a.jpg"]);
    expect(queue.snapshot()[1]?.status).toBe("error");
  });

  it("reporta progreso y cancela solo lo que no empezó", async () => {
    const gate = deferred<void>();
    let report: (fraction: number) => void = () => {};
    const queue = createUploadQueue<string, void>({
      concurrency: 1,
      worker: (_, onProgress) => {
        report = onProgress;
        return gate.promise;
      },
    });
    queue.add(["a", "b", "c"]);
    report(0.5);
    expect(queue.snapshot()[0]).toMatchObject({ status: "uploading", progress: 0.5 });
    queue.cancelQueued();
    expect(queue.snapshot().map((item) => item.file)).toEqual(["a"]);
    gate.resolve();
    await queue.idle();
    expect(queue.snapshot()[0]?.status).toBe("done");
  });

  it("clearFinished conserva lo pendiente", async () => {
    const gate = deferred<void>();
    const queue = createUploadQueue<string, void>({
      concurrency: 1,
      worker: (name) => (name === "b" ? gate.promise : Promise.resolve()),
    });
    queue.add(["a"]);
    await queue.idle();
    queue.add(["b"]);
    queue.clearFinished();
    expect(queue.snapshot().map((item) => item.file)).toEqual(["b"]);
    gate.resolve();
    await queue.idle();
  });
});

describe("validateImageFile", () => {
  const file = (name: string, type: string, size = 100) => ({ name, type, size });
  it("acepta JPEG, PNG y WebP", () => {
    expect(validateImageFile(file("a.jpg", "image/jpeg"))).toBeNull();
    expect(validateImageFile(file("a.webp", "image/webp"))).toBeNull();
    expect(validateImageFile(file("a.PNG", ""))).toBeNull();
  });
  it("rechaza otros formatos, vacíos y más de 20 MB", () => {
    expect(validateImageFile(file("a.gif", "image/gif"))).toMatch(/Formato/);
    expect(validateImageFile(file("a.heic", ""))).toMatch(/Formato/);
    expect(validateImageFile(file("a.jpg", "image/jpeg", 21 * 1024 * 1024))).toMatch(/20 MB/);
    expect(validateImageFile(file("a.jpg", "image/jpeg", 0))).toMatch(/vacío/);
  });
});
