from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from services import (
    chapter_service,
    dashboard_service,
    data_service,
    entity_service,
    outline_service,
    workflow_service,
)

router = APIRouter(prefix="/api")


class ChapterDraftPayload(BaseModel):
    title: str
    content: str


class ChapterLedgerPayload(BaseModel):
    content: str


class CharacterContextPayload(BaseModel):
    chapter_content: str = ""
    requested_names: list[str] = Field(default_factory=list)

@router.get("/dashboard/alerts")
def get_alerts():
    return dashboard_service.get_dashboard_alerts()

@router.get("/chapters")
def get_chapters():
    return chapter_service.get_all_chapters()

@router.get("/chapters/{chapter_no}")
def get_chapter(chapter_no: int):
    chapter = chapter_service.get_chapter_by_no(chapter_no)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.get("/workflow/current")
def get_current_workflow():
    workflow = workflow_service.get_current_workflow()
    if not workflow:
        raise HTTPException(status_code=404, detail="No workflow chapter found")
    return workflow


@router.get("/workflow/{chapter_no}")
def get_workflow(chapter_no: int):
    workflow = workflow_service.get_workflow_by_chapter(chapter_no)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow chapter not found")
    return workflow


@router.post("/workflow/{chapter_no}/save-draft")
def save_workflow_draft(chapter_no: int, payload: ChapterDraftPayload):
    try:
        return workflow_service.save_chapter_draft(chapter_no, payload.title, payload.content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workflow/{chapter_no}/save-ledger")
def save_workflow_ledger(chapter_no: int, payload: ChapterLedgerPayload):
    try:
        return workflow_service.save_chapter_ledger(chapter_no, payload.content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workflow/{chapter_no}/generate-radar")
def generate_workflow_radar(chapter_no: int):
    result = workflow_service.generate_radar(chapter_no)
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["stderr"] or result["stdout"] or "战术靶点雷达生成失败",
        )
    return result


@router.post("/workflow/{chapter_no}/finalize")
def finalize_workflow(chapter_no: int):
    result = workflow_service.finalize_chapter(chapter_no)
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["stderr"] or result["stdout"] or "章节闭环失败",
        )
    return result


@router.post("/workflow/{chapter_no}/character-context")
def get_workflow_character_context(chapter_no: int, payload: CharacterContextPayload):
    result = workflow_service.get_character_context(
        chapter_no,
        payload.chapter_content,
        payload.requested_names,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Workflow chapter not found")
    return result



@router.get("/entities")
def get_entities():
    return entity_service.get_all_entities()

@router.get("/assets")
def get_assets():
    return data_service.get_all_assets()

@router.get("/reports/matrix")
def get_progress_matrix():
    return dashboard_service.get_progress_matrix()

@router.get("/relationships")
def get_relationships():
    return entity_service.get_relationships_graph()

@router.get("/hooks")
def get_hooks():
    return data_service.get_all_hooks()

@router.get("/facts")
def get_facts():
    return data_service.get_all_facts()

# 新增大纲解析接口
@router.get("/outline/tree")
def get_outline_tree():
    return outline_service.parse_outline_structure()

@router.get("/outline/content")
def get_outline_content(path: str):
    result = outline_service.get_outline_content(path)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
