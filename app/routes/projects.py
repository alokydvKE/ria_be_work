'''
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import engine
from app.models.projects import Projects, ProjectCreate
from app.services.auth import get_current_user
import logging

#
#logger = logging.getLogger(__name__)
#security_logger = logging.getLogger("security")

router = APIRouter()


@router.get("/projects")
def get_projects(user=Depends(get_current_user)):
    with Session(engine) as session:
        #logger.info(f"GETTING PROJECTS | user_id={user.get('user_id')}")
        return session.exec(select(Projects).where(Projects.is_archived == False)).all()


@router.get("/projects/{project_id}")
def get_project(project_id: int, user=Depends(get_current_user)):
    with Session(engine) as session:
        #logger.info(f"GETTING PROJECT | project_id={project_id} | user_id={user.get('user_id')}")
        db_project = session.get(Projects, project_id)
        if not db_project:
            #security_logger.warning(f"GETTING PROJECT | project_id={project_id} | user_id={user.get('user_id')} | reason=project not found")
            raise HTTPException(status_code=404, detail="Project not found")
        if db_project.is_archived:
            #security_logger.warning(f"GETTING PROJECT | project_id={project_id} | user_id={user.get('user_id')} | reason=project is deleted")
            raise HTTPException(status_code=404, detail="Project not found")
        return db_project


@router.post("/projects")
def create_project(project: ProjectCreate, user=Depends(get_current_user)):
    print(f"DEBUG: Received project data: {project.model_dump()}")
    #if not user.get("can_add"):
        #security_logger.warning(f"ADDING PROJECT | project_name={project.project_name} | user_id={user.get('user_id')}")
        #raise HTTPException(status_code=403, detail="Not authorized to add projects")
        
    with Session(engine) as session:
        new_project = Projects(**project.dict())
        session.add(new_project)
        session.commit()
        session.refresh(new_project)
        #security_logger.info(f"PROJECT ADDED | project_id={new_project.project_id} | user_id={user.get('user_id')}")
        return new_project


@router.put("/projects/{project_id}")
def update_project(project_id: int, project: ProjectCreate, user=Depends(get_current_user)):
    #if not user.get("can_edit"):
        #raise HTTPException(status_code=403, detail="Not authorized to edit projects")
    with Session(engine) as session:
        db_project = session.get(Projects, project_id)
        if not db_project or db_project.is_archived:
            raise HTTPException(status_code=404, detail="Project not found")
        db_project.project_name = project.project_name
        db_project.location     = project.location
        db_project.start_date   = project.start_date
        db_project.end_date     = project.end_date
        db_project.is_live      = project.is_live
        session.commit()
        session.refresh(db_project)
        return db_project

@router.delete("/projects/{project_id}")
def delete_project(project_id: int, user=Depends(get_current_user)):
    #if not user.get("can_delete"):
        #security_logger.warning(f"DELETING PROJECT | project_id={project_id} | user_id={user.get('user_id')}")
        #raise HTTPException(status_code=403, detail="Not authorized to delete projects")
    
    with Session(engine) as session:
        db_project = session.get(Projects, project_id)
        if not db_project:
            #security_logger.warning(f"DELETING PROJECT | project_id={project_id} | user_id={user.get('user_id')} | reason=project not found")
            raise HTTPException(status_code=404, detail="Project not found")
        if db_project.is_deleted:
            #security_logger.warning(f"DELETING PROJECT | project_id={project_id} | user_id={user.get('user_id')} | reason=project already deleted")
            raise HTTPException(status_code=404, detail="Project not found")
        
        db_project.is_deleted = True
        session.commit()
        #security_logger.info(f"PROJECT DELETED | project_id={project_id} | user_id={user.get('user_id')}")
        return {"success": True}

'''


from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import engine
from app.models.projects import Projects, ProjectCreate
from app.services.auth import get_current_user
from datetime import datetime, date

router = APIRouter()

@router.get("/projects")
def get_projects(user=Depends(get_current_user)):
    with Session(engine) as session:
        return session.exec(select(Projects).where(Projects.is_archived == False)).all()

@router.get("/projects/{project_id}")
def get_project(project_id: int, user=Depends(get_current_user)):
    with Session(engine) as session:
        db_project = session.get(Projects, project_id)
        if not db_project or db_project.is_archived:
            raise HTTPException(status_code=404, detail="Project not found")
        return db_project

@router.post("/projects")
def create_project(project: ProjectCreate, user=Depends(get_current_user)):
    print(f"DEBUG: Received project data: {project}")
    with Session(engine) as session:
        new_project = Projects(
            name=project.name,         
            location=project.location,
            start_date=project.start_date,
            end_date=project.end_date,
            is_live=project.is_live,
            is_archived=False,
            is_deleted=False,
        )
        session.add(new_project)
        session.commit()
        session.refresh(new_project)
        return new_project

@router.put("/projects/{project_id}")
def update_project(project_id: int, project: ProjectCreate, user=Depends(get_current_user)):
    with Session(engine) as session:
        db_project = session.get(Projects, project_id)
        if not db_project or db_project.is_archived:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Update fields
        db_project.name = project.name  
        db_project.location = project.location
        db_project.start_date = project.start_date
        db_project.end_date = project.end_date
        db_project.is_live = project.is_live
        session.commit()
        session.refresh(db_project)
        return db_project

@router.delete("/projects/{project_id}")
def delete_project(project_id: int, user=Depends(get_current_user)):
    with Session(engine) as session:
        db_project = session.get(Projects, project_id)
        if not db_project:
            raise HTTPException(status_code=404, detail="Project not found")
        if db_project.is_deleted:
            raise HTTPException(status_code=404, detail="Project already deleted")
        db_project.is_deleted = True
        session.commit()
        return {"success": True}