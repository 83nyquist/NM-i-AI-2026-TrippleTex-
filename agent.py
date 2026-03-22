import httpx
import logging
from google import genai
from google.genai import types
import contextvars

from mcp_client import MCPClient

from typing import Optional, List, Any

logger = logging.getLogger(__name__)

# Global variables to hold the current request context for the tools
current_base_url = contextvars.ContextVar("current_base_url", default="")
current_session_token = contextvars.ContextVar("current_session_token", default="")
current_mcp: contextvars.ContextVar[Any] = contextvars.ContextVar("current_mcp", default=None)

def search_tripletex_docs(query: str) -> dict:
    """
    Search the Tripletex API documentation for endpoints, schemas, and descriptions.
    Args:
        query: The search term (e.g., 'invoice', 'customer', 'project').
    """
    logger.info(f"Searching MCP docs for: {query}")
    mcp = current_mcp.get()
    if mcp:
        return mcp.call_tool("search_docs", {"query": query})
    return {"error": "MCP Client not initialized"}

def read_tripletex_resource(uri: str) -> dict:
    """
    Read a specific documentation resource from the MCP server.
    Args:
        uri: The URI of the resource (e.g., 'challenge://tripletex/endpoint').
    """
    logger.info(f"Reading MCP resource: {uri}")
    mcp = current_mcp.get()
    if mcp:
        return mcp.read_resource(uri)
    return {"error": "MCP Client not initialized"}

import json
import re
import os

_openapi_spec = None

def get_tripletex_schema(endpoint: str) -> dict:
    """
    Get the OpenAPI schema for a specific Tripletex endpoint (e.g. '/invoice', '/customer').
    Use this to understand the required JSON body fields and query parameters for an endpoint.
    Returns the supported methods (GET, POST, PUT, DELETE) and their required parameters/body schemas.
    Args:
        endpoint: The API path, starting with / (e.g., '/employee', '/customer').
    """
    global _openapi_spec
    if _openapi_spec is None:
        try:
            openapi_path = os.path.join(os.path.dirname(__file__), "openapi.json")
            with open(openapi_path, "r", encoding="utf-8") as f:
                _openapi_spec = json.load(f)
        except Exception as e:
            return {"error": f"Could not load openapi.json: {e}"}
            
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
        
    paths = _openapi_spec.get("paths", {})
    results = {}
    
    # Exact match and sub-paths (e.g., /invoice, /invoice/{id})
    for path, path_data in paths.items():
        if path == endpoint or path.startswith(endpoint + '/') or path.startswith(endpoint + '?'):
            results[path] = path_data
            
    if not results:
        return {"error": f"Endpoint {endpoint} not found in schema."}
        
    # Extract $refs to include related models so the agent knows the structure
    result_str = json.dumps(results)
    refs = set(re.findall(r'"\$ref":\s*"([^"]+)"', result_str))
    
    schemas = {}
    components = _openapi_spec.get("components", {}).get("schemas", {})
    
    resolved_refs = set(refs)
    current_refs = set(refs)
    
    while current_refs:
        new_refs = set()
        for ref in current_refs:
            if ref.startswith("#/components/schemas/"):
                model_name = ref.split("/")[-1]
                if model_name in components:
                    schemas[model_name] = components[model_name]
                    # Find deeper refs
                    model_str = json.dumps(components[model_name])
                    deeper = set(re.findall(r'"\$ref":\s*"([^"]+)"', model_str))
                    for d in deeper:
                        if d not in resolved_refs:
                            resolved_refs.add(d)
                            new_refs.add(d)
        current_refs = new_refs
        
    # Replace "$ref" with "openapi_ref" to avoid confusing the Gemini API
    # Since we are returning this dict as a function response, Gemini might interpret "$ref"
    # as an internal schema reference.
    def replace_refs(obj):
        if isinstance(obj, dict):
            new_obj = {}
            for k, v in obj.items():
                if k == "$ref":
                    new_obj["openapi_ref"] = v
                else:
                    new_obj[k] = replace_refs(v)
            return new_obj
        elif isinstance(obj, list):
            return [replace_refs(i) for i in obj]
        return obj

    paths = replace_refs(paths)
    schemas = replace_refs(schemas)
    
    # Minimize schema size by removing descriptions and examples
    def strip_fluff(obj):
        if isinstance(obj, dict):
            keys_to_remove = ["description", "example", "examples", "summary"]
            for k in keys_to_remove:
                if k in obj:
                    del obj[k]
            for k, v in obj.items():
                strip_fluff(v)
        elif isinstance(obj, list):
            for i in obj:
                strip_fluff(i)
                
    strip_fluff(paths)
    strip_fluff(schemas)

    return {
        "endpoint": endpoint,
        "paths": paths,
        "related_models": schemas
    }

_beta_regexes = None

def _is_beta_endpoint(endpoint: str, method: str) -> bool:
    global _openapi_spec, _beta_regexes
    if _beta_regexes is None:
        _beta_regexes = []
        if _openapi_spec is None:
            # Force load
            get_tripletex_schema("/force-load")
        if _openapi_spec:
            for p, path_data in _openapi_spec.get("paths", {}).items():
                for m, info in path_data.items():
                    if isinstance(info, dict):
                        desc = info.get("description", "").upper()
                        summary = info.get("summary", "").upper()
                        if "[BETA]" in desc or "[BETA]" in summary:
                            pattern = re.sub(r'\{[^}]+\}', r'[^/]+', p)
                            _beta_regexes.append((re.compile('^' + pattern + '$'), m.lower()))
                            
    base_endpoint = endpoint.split('?')[0]
    method_lower = method.lower()
    for regex, m in _beta_regexes:
        if m == method_lower and regex.match(base_endpoint):
            return True
    return False

def _get_auth():
    return ("0", current_session_token.get())

def get_tripletex(endpoint: str, params: Optional[dict] = None) -> dict:
    """
    Make a GET request to the Tripletex API. 
    Use this to search for existing entities, find required IDs, or verify creations.
    Args:
        endpoint: The API path, starting with / (e.g., '/employee', '/customer').
        params: Query parameters (e.g., {'fields': 'id,name', 'count': 100}).
    """
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
        
    url = f"{current_base_url.get()}{endpoint}"
    logger.info(f"GET {url} {params}")
    try:
        response = httpx.get(url, auth=_get_auth(), params=params, timeout=30.0)
        return {"status_code": response.status_code, "data": response.json()}
    except Exception as e:
        return {"error": str(e)}

def post_tripletex(endpoint: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
        
    url = f"{current_base_url.get()}{endpoint}"
    logger.info(f"POST {url} with params {params} and payload {json.dumps(payload)}")
    try:
        response = httpx.post(url, auth=_get_auth(), params=params, json=payload, timeout=30.0)
        if response.status_code >= 400:
            logger.error(f"POST {url} failed with {response.status_code}: {response.text}")
        return {"status_code": response.status_code, "data": response.json() if response.text else None}
    except Exception as e:
        return {"error": str(e)}

def put_tripletex(endpoint: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
        
    url = f"{current_base_url.get()}{endpoint}"
    logger.info(f"PUT {url} with params {params} and payload {json.dumps(payload)}")
    try:
        response = httpx.put(url, auth=_get_auth(), params=params, json=payload, timeout=30.0)
        if response.status_code >= 400:
            logger.error(f"PUT {url} failed with {response.status_code}: {response.text}")
        return {"status_code": response.status_code, "data": response.json() if response.text else None}
    except Exception as e:
        return {"error": str(e)}

def delete_tripletex(endpoint: str) -> dict:
    """
    Make a DELETE request to the Tripletex API to remove an entity.
    Args:
        endpoint: The API path, starting with / and including the ID (e.g., '/employee/123').
    """
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
        
    url = f"{current_base_url.get()}{endpoint}"
    logger.info(f"DELETE {url}")
    try:
        response = httpx.delete(url, auth=_get_auth(), timeout=30.0)
        # DELETE might not return JSON
        if response.text:
            return {"status_code": response.status_code, "data": response.json()}
        return {"status_code": response.status_code, "data": None}
    except Exception as e:
        return {"error": str(e)}

def post_tripletex_multipart(endpoint: str, file_path: str) -> dict:
    """
    Make a POST request with multipart/form-data to upload a file to the Tripletex API.
    Args:
        endpoint: The API path, starting with / (e.g., '/documentArchive/customer/123').
        file_path: The absolute path to the local file you want to upload.
    """
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
        
    url = f"{current_base_url.get()}{endpoint}"
    logger.info(f"POST MULTIPART {url} (File: {file_path})")
    try:
        import os
        if not os.path.exists(file_path):
            return {"error": f"File not found at {file_path}"}
            
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            response = httpx.post(url, auth=_get_auth(), files=files, timeout=60.0)
            
        return {"status_code": response.status_code, "data": response.json() if response.text else None}
    except Exception as e:
        return {"error": str(e)}

import base64

def run_agent(client: genai.Client, base_url: str, session_token: str, prompt: str, files: Optional[List[Any]] = None):
    current_base_url.set(base_url)
    current_session_token.set(session_token)
    current_mcp.set(MCPClient())

    system_instruction = """
    You are an autonomous AI accounting agent for the Tripletex API (v2).
    Your goal is to parse a user's prompt (which may be in one of 7 languages), optionally read attached files, 
    and execute the necessary API calls against the Tripletex API to complete the task.
    
    You have tools to perform GET, POST, PUT, and DELETE requests against the Tripletex API.
    CRITICAL: For detailed API schemas (to know exact required fields for POST/PUT), ALWAYS use `get_tripletex_schema`.
    
    IMPORTANT RULES:
    1. Tripletex requires specific fields. If you do not know the exact schema or endpoint for an operation, use `get_tripletex_schema(endpoint)` to read its detailed schema from the OpenAPI spec.
    2. Before creating entities that require relationships (like creating an invoice that needs a customerId), you MUST first use GET to find the customer ID, or POST to create the customer if they don't exist.
    3. Minimize your API calls to maximize your efficiency score. If a POST or PUT returns the created/modified object in the response, DO NOT execute a follow-up GET request to verify it. You already have the data!
    4. If an API call fails (e.g., 400 Bad Request), use `get_tripletex_schema` to check what fields are missing or wrong, correct your payload, and try again.
    5. Norwegian characters (æ, ø, å) must be preserved.
    6. You should avoid using endpoints marked as [BETA] in the schema as they often return 403 Forbidden. ONLY use a [BETA] endpoint if it is the absolute ONLY way to accomplish the task (for example, assigning an Administrator role requires using the beta `PUT /employee/entitlement/:grantEntitlementsByTemplate` endpoint).
    7. When creating an Employee, the Tripletex API secretly requires a `dateOfBirth`. If the prompt does not provide one, invent a sensible default like `1990-01-01`. You MUST also always include `"userType": "STANDARD"` and you MUST assign them to a `department` (find a department ID first).
    8. When creating a Project, the Tripletex API secretly requires a `startDate`. If the prompt does not provide one, use the current date (e.g. `2026-03-21`).
    9. NEVER search for multiple entities by combining names with commas in GET requests (e.g. `GET /activity?name=Project manager,Consultant` is WRONG). Always perform separate GET requests for each entity name.
    10. Be extremely precise when extracting the exact first name, last name, and email from the prompt. Do not guess or modify them.
    11. For endpoints that end with a colon and an action (like `/invoice/{id}/:payment`), the required fields are passed as URL query parameters in the PUT/POST request. Use the `params` argument for query parameters, and the `payload` argument for JSON bodies.
    12. INVOICING FLOW: To create an invoice, you must FIRST create an order (`POST /order`) containing `orderLines` (which must include `product` and `count`). Never try to create an invoice directly via `POST /invoice` if the prompt asks to invoice a customer for a product. Also, when creating an order or invoice, ALWAYS fill in `orderDate` and `deliveryDate` (use current date like 2026-03-21 if not provided).
    13. NUMBER FORMATTING: Be extremely careful when parsing Norwegian numbers and prices (e.g., '29,50' means 29.50). ALWAYS convert commas to periods and ensure you pass them as proper float decimals in your JSON payload. Never accidentally drop the decimal point (e.g., 29,50 should be 29.50, NOT 2950).
    14. LEDGER ENDPOINTS: If a prompt asks you to search for or interact with accounts (like salary accounts), you MUST use the `/ledger/account` endpoint (NOT `/account`). If you need to create manual vouchers, use the `/ledger/voucher` endpoint (NOT `/voucher`).
    15. CRITICAL BANK ACCOUNT CHECK: The very first step of any task involving sending/creating an invoice is to ensure the company has a valid bank account. BEFORE attempting any `POST /order` or `PUT /order/{id}/:invoice`, you MUST proactively fetch a bank account in the ledger (`GET /ledger/account?isBankAccount=true`). If the `bankAccountNumber` field is missing or invalid, you must update it (`PUT /ledger/account/{id}`) with the guaranteed valid 11-digit Norwegian bank account number '10000000006'.
    16. INVOICE EMAILS: If a prompt provides an email address containing words like 'faktura', 'invoice', 'facture', 'billing', etc. for a customer or supplier, you MUST populate the `invoiceEmail` field in the JSON payload (in addition to the regular `email` field).
    17. PROJECT MANAGER & ACTIVITY TYPE: When creating an internal project (`"isInternal": true`), you MUST provide a `projectManager` (e.g., `{"id": <employee_id>}`). You can find an employee ID by searching for one or using the logged-in employee. When creating a `projectActivity`, you MUST include `"activityType": "PROJECT_SPECIFIC_ACTIVITY"` inside the `activity` object payload.
    18. SENDING INVOICES: If asked to "send" the invoice, pass `sendToCustomer=true` as a query parameter when calling the `PUT /order/{id}/:invoice` endpoint.
    19. POSTING ROWS & SUPPLIERS: When creating a manual voucher with a `postings` list, you MUST explicitly provide a `row` integer for each posting, starting from `1`. Never omit the `row` property and never use row `0`. CRITICAL: NEVER put a `supplier` field on the root `Voucher` object! It MUST go inside a specific `Posting` row (e.g., account 2400). Do not include a `voucherType` unless explicitly known.
    20. SUPPLIER INVOICES: NEVER use `/incomingInvoice` because you do not have permission. To register supplier invoices or receipts, you MUST use `POST /ledger/voucher` instead.
    21. PROJECT INVOICING: If asked to generate a project invoice based on recorded hours, you MUST create a new `POST /order` where the `orderLines` manually reflect the hours logged (using the hourly rate as the `unitPriceExcludingVatCurrency` and the hours as the `count`). Do not try to invoice empty, pre-existing orders.
    22. STRICT SCHEMA ADHERENCE: When creating entities (especially Orders and OrderLines), you MUST ONLY use field names that exist in the schema returned by `get_tripletex_schema`. NEVER invent fields (like `invoiceDate`, `isPrioritized`, `consumer`, `isInvoiced`, or `unitPriceExcludingVat` on orders). If a field ends in `Currency` in the schema (like `unitPriceExcludingVatCurrency`), you must use that exact name.
    23. LEDGER ANALYSIS: If a prompt asks you to analyze ledger data, costs, or balances over a date range, you MUST query `GET /ledger/posting` using the `dateFrom` and `dateTo` parameters. (Remember that cost accounts in Norway typically use account numbers `4000` to `7999`, so you can use `accountNumberFrom=4000` and `accountNumberTo=7999`). Do NOT try to pass date parameters directly to `/ledger/account`. After fetching the postings, manually sum the `amountCurrency` per account to find your answer.
    24. VAT ACCOUNTS: Never apply a `vatType` to an actual VAT ledger account (like 2710 or 2700) OR any account that is locked to VAT code 0 (like 7350 Representasjon). Omit the `vatType` field entirely for these locked posting rows.
    25. PROJECT ACTIVITIES: You MUST create project-specific activities via `POST /project/projectActivity`, NOT `/activity`.
    26. FIXED PRICE: The property for a project's fixed price is exactly `fixedprice` (all lowercase), NOT `fixedPrice`.
    27. ORDER DATES: Always ensure `deliveryDate` is populated when creating an `Order` (e.g. use the `orderDate` or the current date). Missing `deliveryDate` will cause a 422 error.
    28. QUERY PARAMS: Never invent query parameters for GET requests. For example, `GET /invoice` ONLY accepts `id`, `invoiceDateFrom`, `invoiceDateTo`, `invoiceNumber`, `kid`, `voucherId`, `customerId`, `from`, `count`, `sorting`, and `fields`. It does NOT accept `isPaid`, `amount`, `orderId`, `customer`, `invoiceDueDateTo`, or similar hallucinated params.
    29. SPELLING: You MUST strictly use American spelling for property names. E.g., `organizationNumber` (with a 'z') on Supplier, NEVER `organisationNumber`.
    30. TRAVEL EXPENSES: When creating a `travelExpense` (`POST /travelExpense`), if you include nested `perDiemCompensations`, each must have a `location`. If you include nested `costs`, each must have a `paymentType` (e.g., `{"id": <paymentTypeId>}`). Also applies to `POST /travelExpense/perDiemCompensation`.
    31. VOUCHER DUE DATES: When creating a manual voucher (`POST /ledger/voucher`), NEVER try to pass a `dueDate`, `invoiceDueDate`, or any due date field on either the Voucher or Posting objects. These fields do not exist for this endpoint.
    32. INVOICE PAYMENTS: There is NO endpoint to list payments for an invoice (e.g., `GET /invoice/{id}/payments` does not exist). If you need to know how much is paid, check the `amountPaid` field on the Invoice object itself.
    33. REGISTERING PAYMENTS: When registering a payment (`PUT /invoice/{id}/:payment`), you MUST FIRST fetch a valid `paymentTypeId` from `GET /invoice/paymentType`. Do not guess the ID.
    34. EMPLOYMENT: To add employment to an employee, use `POST /employee/employment` (not `POST /employment`). You MUST provide a non-null `startDate` on the root object, and you MUST use `annualSalary` (NOT `yearlySalary`) inside the nested `employmentDetails` list.
    35. PRODUCTS: When creating a Product (`POST /product`), you MUST NOT use fields like `vatTypeId` or `productNumber`. VAT is set using an object like `"vatType": {"id": ...}`.
    36. MANUAL VOUCHERS: When creating a manual voucher (`POST /ledger/voucher`), you MUST always provide a non-null `description` string on the root Voucher object. NEVER invent a `voucherType`, `voucherType.id`, `systemType`, `invoice`, or `dueDate` unless you have explicitly queried and verified it.
    37. ACCOUNTING DIMENSIONS: If asked to interact with accounting dimensions, use the schemas strictly. `POST /ledger/accountingDimensionName` requires `dimensionName` (NOT `name`), and `POST /ledger/accountingDimensionValue` requires `nameAndNumber` or `displayName` (NOT `name`). Do not use `POST /ledger/accountingDimension`.
    38. CREDIT NOTES: When creating a credit note (`PUT /invoice/{id}/:createCreditNote`), if you provide a `date` query parameter, it MUST NOT be earlier than the original invoice's date. If unsure, omit the `date` parameter entirely.
    39. SEARCH BEFORE CREATE: To prevent 409 Conflict errors and task failures, you MUST perform a `GET` request to search for a primary entity (e.g., Customer, Employee, Product) before making a `POST` request to create it. If the entity already exists, update it or use its existing ID. Do not blindly `POST`.
    40. STRICT DATE FORMATTING: Ensure all date fields strictly adhere to the `YYYY-MM-DD` format (e.g., `2026-03-21`) unless the schema explicitly requires a full datetime string.
    41. MANDATORY FIELDS CHECK: Before sending a payload, double-check the required fields for that endpoint in the OpenAPI spec you retrieved. Missing required fields (like `departmentId` or `vatType`) will automatically fail the task.
    42. PAYLOAD LIMITS: When using `GET` endpoints that return lists (like `/ledger/posting`, `/ledger/voucher`, `/invoice`), you MUST ALWAYS include `count=100` (or fewer) and use the `fields` parameter to limit the response size. Failure to do so will return massive payloads that crash your token context window and auto-fail the task.
    43. EXCHANGE RATES (AGIO/DISAGIO): If asked to register an invoice payment with an exchange rate difference, you must book currency gains (agio) to account 8060 and currency losses (disagio) to account 8160.
    44. DO NOT OVER-THINK: Once you receive a `201 Created` or `200 OK` confirming your `POST`/`PUT` was successful, DO NOT enter a loop to re-verify it. Conclude the task immediately by outputting your final summary text.
    45. If the prompt contains a file (like an image of a receipt or a PDF invoice), analyze the file to extract the required fields to complete the task. You can also upload these files to Tripletex (e.g. attaching a receipt to an expense) using the `post_tripletex_multipart` tool. For any attached files in the task, their absolute file paths on disk will be explicitly written out in the prompt so you can pass them to the tool.
    46. You have a hard timeout of 120 seconds to complete the entire task, so be efficient with your tool calls.
    47. When you are finished, output a final summary of what you did.
    """

    tools = [get_tripletex, post_tripletex, put_tripletex, delete_tripletex, post_tripletex_multipart, get_tripletex_schema]
    
    contents: List[Any] = [prompt]
    if files:
        for f in files:
            # Handle different competition payload schemas (f.data or f.content_base64)
            file_data = getattr(f, "content_base64", None) or getattr(f, "data", None)
            mime_type = getattr(f, "mime_type", "application/octet-stream")
            if file_data:
                contents.append(
                    types.Part.from_bytes(
                        data=base64.b64decode(file_data),
                        mime_type=mime_type
                    )
                )

    chat = client.chats.create(
        model="gemini-2.5-pro",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=tools,
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                maximum_remote_calls=30
            )
        )
    )

    logger.info("Starting agent execution loop...")
    
    # Send the message in a try-catch block to handle context length limits
    try:
        response = chat.send_message(contents)
        logger.info(f"Raw Gemini response: {response}")
        final_text = response.text if response and response.text else "Task completed with empty response from agent."
    except Exception as e:
        if "maximum number of tokens allowed" in str(e):
            logger.error("Token limit exceeded, returning partial summary.")
            return "Token limit exceeded during tool execution. Partial task completed."
        raise e
        
    logger.info(f"Agent finished. Final response: {final_text}")
    return final_text
