import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { WebSocketClientTransport } from "@modelcontextprotocol/sdk/client/websocket.js";
import WebSocket from 'ws';

// Polyfill WebSocket for the SDK
global.WebSocket = WebSocket;

async function main() {
    console.log("Connecting to WebSocket proxy...");
    const transport = new WebSocketClientTransport(new URL("ws://127.0.0.1:6277"));
    const client = new Client({ name: "cli", version: "1.0.0" }, { capabilities: {} });
    
    await client.connect(transport);
    console.log("Connected!");
    
    const tools = await client.listTools();
    console.log("Tools:", tools);

    const searchDocs = await client.callTool({
        name: "search_docs",
        arguments: { query: "Tripletex" }
    });
    console.log("Search Docs Tripletex:", JSON.stringify(searchDocs, null, 2));

    const listDocs = await client.callTool({
        name: "list_docs",
        arguments: {}
    });
    console.log("List Docs:", JSON.stringify(listDocs, null, 2));
    
    // Attempting to search more things if listDocs shows other categories
    process.exit(0);
}

main().catch(console.error);