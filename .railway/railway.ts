import { defineRailway, project, service } from "railway/iac";

export const partial = "cryptotrada";

export default defineRailway(() => {
  const app = service("cryptotrada", {
    build: {
      builder: "docker",
      dockerfile: "Dockerfile",
    },
    env: {
      PORT: "8080",
      OPERATING_MODE: "manual",
      AVAILABILITY: "online",
      LOG_LEVEL: "INFO",
      CB_IN_PAPER_MODE: "true",
      P2P_ASSET: "USDT",
      P2P_FIAT: "SDG",
    },
    mount: {
      source: "data",
      destination: "/app/data",
    },
    startCommand: "python3 main.py",
    healthcheck: {
      path: "/api/journal/summary",
    },
  });
  return project("cryptotrada", {
    resources: [app],
  });
});
