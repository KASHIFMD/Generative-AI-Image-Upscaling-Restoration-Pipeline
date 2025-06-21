from fastapi import APIRouter, BackgroundTasks # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from fastapi import Request # type: ignore
from rabbitmq import RabbitMQ
from helper import getConfigInfo
from pydantic import BaseModel
from typing import Optional
import cv2
import numpy as np
from utils.upload import UploadFile
from prompts import prompts
from jinja2 import Template
import os
import json
import requests
import random

# Used to keep track of last used GPU for round-robin (can also be persisted to Redis or file)
ROUND_ROBIN_INDEX_KEY = "ROUND_ROBIN_INDEX"

router = APIRouter(prefix="/v1")

class EnhanceDataFormat(BaseModel):
    docid: str
    product_id: str
    product_url: str
    org_product_url: str
    image_type: str
    force: Optional[int] = 0  # ✅ Default is False, indicating no force enhancement
    
class RelevanceDataFormat(BaseModel):
    docid: str
    product_id: str
    product_url: str
    prompt: Optional[str] = None  # ✅ Default is None
    prompt_name: Optional[str] = None  # ✅ Default is None
    cat_name: Optional[str] = None  # ✅ Default is None
    is_json: Optional[int] = 0  # ✅ Default is False, indicating no JSON response
 
@router.post("/img_enhance")
def image_enhancement(request: Request, data: EnhanceDataFormat, background_tasks: BackgroundTasks):
    """
    Received request to enhance image using GPU
    """
    loadModel = True if os.environ["LOAD_MODEL"] == "True" else False
    if loadModel:
        try:
            # Extract data from the request
            docid = data.docid
            product_id = data.product_id
            product_url = data.product_url
            org_product_url = data.org_product_url
            image_type = data.image_type
            force = data.force

            # Create a dictionary to hold the data
            data = {
                "docid": docid,
                "product_id": product_id,
                "product_url": product_url,
                "org_product_url": org_product_url,
                "image_type": image_type,
                "force": force
            }
            print(f"Data received: {data}")
            
            if not all([docid, product_id, product_url, org_product_url, image_type]):
                return JSONResponse(status_code=400, content={"error_code": 1, "message": "Invalid request data"})
            # Check if the image type is valid
            
            # New function to handle the image optimization request -- start
            # Access model handler from app state
            model_handler = request.app.state.model_handler

            try:
                # Get the enhanced image using the model handler
                enhanced_image, message, err, status_code = model_handler.process(data)
                if enhanced_image is None:
                    return JSONResponse(status_code=status_code, content = {"error_code": 1, "err": str(err), "message":message})
                
                # Object instantiation for uploading file to S3
                upload_file = UploadFile()

                upload_data = {
                    "docid": docid,
                    "product_id": product_id,
                    "product_url": product_url,
                    "image_type": "enhanced",
                    "SOURCE": enhanced_image,
                    "DESTINATION": product_url,
                }
                _, message, err, status_code = upload_file.UploadImageFileToS3(upload_data, db_update=False, path = False)
            except Exception as err:
                return JSONResponse(status_code=500, content = {"error_code": 1, "err": err, "message": "Error in processing image enhancement"})

            # End of new function to handle the image optimization request
            return JSONResponse(status_code=status_code, content={"error_code": 0, "err": err, "message": "Image optimization request processed successfully"})
        except Exception as err:
            return JSONResponse(status_code=500, content={"error_code": 1, "err": err, "message": "Error in processing image enhancement"})
    else:
        return JSONResponse(status_code=501, content={"error_code": 1, "message": "Not Implemented: API disabled on CPU server, not loading model"})
