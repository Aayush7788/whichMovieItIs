import { createServer } from "vite";

const port = Number.parseInt(process.env.PORT || "5173", 10);

if (!Number.isInteger(port)) {
  throw new Error("PORT must be an integer");
}

const server = await createServer({
  server: {
    host: "127.0.0.1",
    port,
    strictPort: true,
  },
});

await server.listen();
server.printUrls();
