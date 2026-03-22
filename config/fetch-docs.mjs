import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

async function main() {
    const transport = new SSEClientTransport(new URL("https://mcp-docs.ainm.no/mcp"));
    const client = new Client({ name: "cli", version: "1.0.0" }, { capabilities: {} });
    await client.connect(transport);
    
    // List tools to see what arguments list_docs and search_docs take
    const tools = await client.listTools();
    console.log(JSON.stringify(tools, null, 2));

    const listDocs = await client.callTool({
        name: "list_docs",
        arguments: {}
    });
    console.log("LIST_DOCS:", JSON.stringify(listDocs, null, 2));

    const searchDocs = await client.callTool({
        name: "search_docs",
        arguments: { query: "Tripletex" }
    });
    console.log("SEARCH_DOCS:", JSON.stringify(searchDocs, null, 2));

    process.exit(0);
}

main().catch(console.error);