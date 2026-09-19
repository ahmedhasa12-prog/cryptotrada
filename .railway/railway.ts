import { defineRailway, project, service } from "railway/iac";

export const partial = "cryptotrada";

export default defineRailway(() => {
  const app = service("cryptotrada");
  return project("cryptotrada", {
    resources: [app],
  });
});
