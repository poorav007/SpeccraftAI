"""Generator script that synthesizes a ~10,000-line realistic FastAPI codebase for AST benchmarking."""

import os
from pathlib import Path


def generate_synthetic_codebase(output_dir: Path, target_loc: int = 10000) -> int:
    """Generate multiple realistic FastAPI routers and models until target LOC is reached."""
    output_dir.mkdir(parents=True, exist_ok=True)
    routers_dir = output_dir / "routers"
    models_dir = output_dir / "models"
    routers_dir.mkdir(exist_ok=True)
    models_dir.mkdir(exist_ok=True)

    total_lines = 0

    # 1. Generate Models
    models_file = models_dir / "schemas.py"
    models_code = [
        "from pydantic import BaseModel, Field",
        "from typing import Optional, List",
        "from datetime import datetime",
        "",
    ]
    # Generate 50 realistic Pydantic models
    for m_idx in range(1, 51):
        models_code.extend([
            f"class ResourceModel{m_idx}(BaseModel):",
            f"    '''Auto-generated Pydantic schema {m_idx} for 10k-LOC benchmark.'''",
            f"    id: int = Field(..., description='Unique ID for resource {m_idx}')",
            f"    name: str = Field(..., description='Title of item')",
            f"    score: float = Field(default=0.0, ge=0.0)",
            f"    is_active: bool = Field(default=True)",
            f"    tags: List[str] = Field(default_factory=list)",
            f"    description: Optional[str] = None",
            "",
            f"class ResourceCreate{m_idx}(BaseModel):",
            f"    name: str",
            f"    score: float = 0.0",
            f"    tags: List[str] = []",
            "",
        ])
    models_file.write_text("\n".join(models_code), encoding="utf-8")
    total_lines += len(models_code)

    # 2. Generate Routers until target LOC is reached
    router_idx = 1
    router_names = []
    while total_lines < target_loc - 100:
        r_file = routers_dir / f"service_{router_idx}.py"
        r_lines = [
            f"# Service Router {router_idx}",
            "from fastapi import APIRouter, HTTPException, status",
            "from typing import List, Optional",
            "from models.schemas import *",
            "",
            f"router = APIRouter(prefix='/service_{router_idx}', tags=['service_{router_idx}'])",
            "",
        ]
        # Add 4 endpoints per router with realistic handler logic
        for ep_idx in range(1, 5):
            m_id = (router_idx * 4 + ep_idx) % 50 + 1
            r_lines.extend([
                f"@router.get('/endpoint_{ep_idx}', response_model=List[ResourceModel{m_id}], summary='List Service {router_idx} items {ep_idx}')",
                f"def list_items_{router_idx}_{ep_idx}(skip: int = 0, limit: int = 20, query: Optional[str] = None):",
                f"    '''Fetch service {router_idx} items with pagination and query filtering.'''",
                f"    if skip < 0 or limit <= 0:",
                f"        raise HTTPException(status_code=400, detail='Invalid pagination parameters')",
                f"    results = []",
                "    for i in range(skip, skip + limit):",
                "        results.append({",
                "            'id': i,",
                "            'name': f'Resource {i}',",
                "            'score': float(i) * 1.5,",
                "            'is_active': True,",
                f"            'tags': ['service', 'service_{router_idx}'],",
                "            'description': f'Generated resource item {i}',",
                "        })",
                "    return results",
                "",
                f"@router.post('/endpoint_{ep_idx}', response_model=ResourceModel{m_id}, status_code=status.HTTP_201_CREATED, summary='Create Service {router_idx} item {ep_idx}')",
                f"def create_item_{router_idx}_{ep_idx}(payload: ResourceCreate{m_id}):",
                f"    '''Create a new resource under service {router_idx}.'''",
                f"    if not payload.name:",
                f"        raise HTTPException(status_code=422, detail='Resource name is required')",
                f"    return {{",
                f"        'id': 100,",
                f"        'name': payload.name,",
                f"        'score': payload.score,",
                f"        'is_active': True,",
                f"        'tags': payload.tags,",
                f"        'description': 'Newly created entity',",
                f"    }}",
                "",
                f"@router.get('/endpoint_{ep_idx}/{{item_id}}', response_model=ResourceModel{m_id}, summary='Get item details')",
                f"def get_item_{router_idx}_{ep_idx}(item_id: int):",
                f"    '''Retrieve single item details by integer ID.'''",
                f"    if item_id <= 0:",
                f"        raise HTTPException(status_code=404, detail='Resource not found')",
                f"    return {{'id': item_id, 'name': 'Item', 'score': 10.5, 'is_active': True, 'tags': []}}",
                "",
                f"@router.delete('/endpoint_{ep_idx}/{{item_id}}', status_code=status.HTTP_204_NO_CONTENT)",
                f"def delete_item_{router_idx}_{ep_idx}(item_id: int):",
                f"    '''Remove item permanently from service {router_idx}.'''",
                f"    if item_id <= 0:",
                f"        raise HTTPException(status_code=404, detail='Resource not found')",
                f"    return None",
                "",
            ])
        r_file.write_text("\n".join(r_lines), encoding="utf-8")
        total_lines += len(r_lines)
        router_names.append(f"service_{router_idx}")
        router_idx += 1

    # 3. Generate main.py
    main_file = output_dir / "main.py"
    main_lines = [
        "from fastapi import FastAPI",
        "",
        "app = FastAPI(title='10k Benchmark App', version='1.0.0')",
        "",
    ]
    for r_name in router_names:
        main_lines.append(f"from routers.{r_name} import router as {r_name}_router")
        main_lines.append(f"app.include_router({r_name}_router)")
    main_lines.extend([
        "",
        "@app.get('/health', tags=['system'])",
        "def health() -> dict: return {'status': 'ok'}",
        "",
    ])
    main_file.write_text("\n".join(main_lines), encoding="utf-8")
    total_lines += len(main_lines)

    return total_lines


if __name__ == "__main__":
    dest = Path(__file__).parent / "synthetic_app"
    loc = generate_synthetic_codebase(dest, 10000)
    print(f"Generated synthetic codebase at {dest} with {loc} lines of code.")
