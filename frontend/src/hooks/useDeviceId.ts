import { useState, useEffect } from "react";
import FingerprintJS from "@fingerprintjs/fingerprintjs";

export function useDeviceId() {
  const [deviceId, setDeviceId] = useState<string>("");

  useEffect(() => {
    async function getDeviceId() {
      try {
        // 从 localStorage 获取缓存的设备 ID
        const cachedDeviceId = localStorage.getItem("device_id");
        if (cachedDeviceId) {
          setDeviceId(cachedDeviceId);
          return;
        }

        // 如果没有缓存，生成新的指纹
        const fp = await FingerprintJS.load();
        const result = await fp.get();
        const newDeviceId = result.visitorId;

        // 缓存设备 ID
        localStorage.setItem("device_id", newDeviceId);
        setDeviceId(newDeviceId);
      } catch (error) {
        console.error("Failed to generate device ID:", error);
        // 生成一个随机的后备 ID
        const fallbackId = Math.random().toString(36).substring(2);
        localStorage.setItem("device_id", fallbackId);
        setDeviceId(fallbackId);
      }
    }

    getDeviceId();
  }, []);

  return deviceId;
}
