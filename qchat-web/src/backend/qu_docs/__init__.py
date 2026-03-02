"""
QU Docs API
GET /api/qu_docs - Get list of URLs
POST /api/qu_docs - Save list of URLs
"""

import azure.functions as func
import logging
import json
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    QU Docs URL Management
    
    GET - Returns list of URLs from qu_docs.txt
    POST - Saves list of URLs to qu_docs.txt
    """
    logging.info('QU Docs API triggered')
    
    # Path to qu_docs.txt (in backend root)
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'qu_docs.txt')
    
    method = req.method
    
    try:
        if method == 'GET':
            return handle_get_urls(file_path)
        elif method == 'POST':
            return handle_save_urls(req, file_path)
        else:
            return func.HttpResponse(
                json.dumps({"error": "Method not allowed"}),
                status_code=405,
                mimetype="application/json"
            )
    
    except Exception as e:
        logging.error(f"QU Docs API error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def handle_get_urls(file_path: str) -> func.HttpResponse:
    """
    GET /api/qu_docs
    
    Returns list of URLs from qu_docs.txt
    """
    logging.info(f'Getting URLs from {file_path}')
    
    try:
        if not os.path.exists(file_path):
            logging.warning(f'qu_docs.txt not found at {file_path}')
            return func.HttpResponse(
                json.dumps({"urls": []}),
                status_code=200,
                mimetype="application/json"
            )
        
        # Read URLs from file
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        logging.info(f'Found {len(urls)} URLs')
        
        return func.HttpResponse(
            json.dumps({"urls": urls}),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logging.error(f'Error reading URLs: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": f"Failed to read URLs: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )


def handle_save_urls(req: func.HttpRequest, file_path: str) -> func.HttpResponse:
    """
    POST /api/qu_docs
    
    Saves list of URLs to qu_docs.txt
    
    Body: {"urls": ["url1", "url2", ...]}
    """
    logging.info(f'Saving URLs to {file_path}')
    
    try:
        # Get request body
        req_body = req.get_json()
        urls = req_body.get('urls', [])
        
        if not isinstance(urls, list):
            return func.HttpResponse(
                json.dumps({"error": "urls must be a list"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Write URLs to file
        with open(file_path, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(f"{url}\n")
        
        logging.info(f'Saved {len(urls)} URLs')
        
        return func.HttpResponse(
            json.dumps({"success": True, "urls": urls}),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logging.error(f'Error saving URLs: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": f"Failed to save URLs: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )