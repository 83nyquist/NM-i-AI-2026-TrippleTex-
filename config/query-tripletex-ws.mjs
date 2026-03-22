import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { WebSocketClientTransport } from "@modelcontextprotocol/sdk/client/websocket.js";
import WebSocket from 'ws';

global.WebSocket = WebSocket;

async function main() {
    console.log("Connecting to WebSocket proxy...");
    const transport = new WebSocketClientTransport(new URL("ws://127.0.0.1:6277"));
    const client = new Client({ name: "cli", version: "1.0.0" }, { capabilities: {} });
    
    await client.connect(transport);
    console.log("Connected!");
    
    const queries = ["Tripletex submission", "Tripletex deploy", "Tripletex scoring", "how to submit"];
    
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