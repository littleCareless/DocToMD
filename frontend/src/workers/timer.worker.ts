let startTime: number | null = null;
let timerId: number | null = null;

self.onmessage = (e: MessageEvent) => {
  if (e.data === "start") {
    // 如果已经在计时，不要重新开始
    if (startTime !== null) {
      return;
    }

    startTime = Date.now();
    timerId = self.setInterval(() => {
      const elapsed = Date.now() - startTime!;
      const hours = Math.floor(elapsed / (1000 * 60 * 60));
      const minutes = Math.floor((elapsed % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((elapsed % (1000 * 60)) / 1000);

      self.postMessage({
        elapsed,
        formatted: `${hours.toString().padStart(2, "0")}:${minutes
          .toString()
          .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`,
      });
    }, 1000);
  } else if (e.data === "stop") {
    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }
    startTime = null;
  }
};
