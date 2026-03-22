import json

def get_tripletex_schema(endpoint: str) -> dict:
    """
    Get the OpenAPI schema for a specific Tripletex endpoint (e.g. '/invoice', '/customer').
    """
    try:
        with open("/home/devstar18111/nmai/openapi.json", "r", encoding="utf-8") as f:
            openapi_spec = json.load(f)
    except Exception as e:
        return {"error": f"Could not load openapi.json: {e}"}
        
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
        
    paths = openapi_spec.get("paths", {})
    results = {}
    
    for path, path_data in paths.items():
        if path == endpoint or path.startswith(endpoint + '/') or path.startswith(endpoint + '?'):
            results[path] = path_data
            
    if not results:
        return {"error": f"Endpoint {endpoint} not found in schema."}
        
    # Extract $refs to include related models
    import re
    result_str = json.dumps(results)
    refs = set(re.findall(r'"\$ref":\s*"([^"]+)"', result_str))
    
    schemas = {}
    components = openapi_spec.get("components", {}).get("schemas", {})
    
    resolved_refs = set()
    while refs:
        new_refs = set()
        for ref in refs:
            if ref in resolved_refs: continue
            resolved_refs.add(ref)
            
            if ref.startswith("#/components/schemas/"):
                model_name = ref.split("/")[-1]
                if model_name in components:
                    schemas[model_name] = components[model_name]
                    # Find deeper refs
                    deeper = set(re.findall(r'"\$ref":\s*"([^"]+)"', json.dumps(components[model_name])))
                    new_refs.update(deeper)
        refs = new_refs
        
    return {
        "endpoint": endpoint,
        "paths": results,
        "related_models": schemas
    }

if __name__ == "__main__":
    res = get_tripletex_schema("/invoice")
    print("Paths:", len(res["paths"]))
    print("Models:", len(res["related_models"]))
    print("Total size:", len(json.dumps(res)))
