import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

async function main() {
    console.log("Connecting...");
    const transport = new SSEClientTransport(new URL("https://mcp-docs.ainm.no/sse"));
    const client = new Client({ name: "cli", version: "1.0.0" }, { capabilities: {} });
    await client.connect(transport);
    console.log("Connected!");
    
    const queries = ["optional API key", "API key", "submit", "Tripletex"];
    for (const query of queries) {
        console.log(`\n\n--- SEARCH RESULTS FOR: ${query} ---`);
        try {
            const searchDocs = await client.callTool({
                name: "search_docs",
                arguments: { query: query }
            });
            console.log(JSON.stringify(searchDocs, null, 2));
        } catch(e) {
            console.error(`Error querying ${query}:`, e);
        }
    }
    process.exit(0);
}

main().catch(console.error);
