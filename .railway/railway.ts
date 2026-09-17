import { defineRailway, project, service } from "railway/iac";

export const partial = "cryptotrada";

export default defineRailway(() => {
  const cryptotrada = service("cryptotrada");
  return project("cryptotrada", {
    resources: [cryptotrada],
  });
});
