"""
Maintenance Mode API
GET /api/maintenance - Check maintenance mode status
POST /api/maintenance - Enable/disable maintenance mode (ADMIN ONLY)
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Maintenance Mode Control
    
    GET - Returns current maintenance mode status
    POST - Enable/disable maintenance mode (turns off chat for EVERYONE)
    """
    logging.info('Maintenance API triggered')
    
    # Path to maintenance_mode.json (in backend root)
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'maintenance_mode.json')
    
    method = req.method
    
    try:
        if method == 'GET':
            return handle_get_status(file_path)
        elif method == 'POST':
            return handle_toggle_maintenance(req, file_path)
        else:
            return func.HttpResponse(
                json.dumps({"error": "Method not allowed"}),
                status_code=405,
                mimetype="application/json"
            )
    
    except Exception as e:
        logging.error(f"Maintenance API error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def handle_get_status(file_path: str) -> func.HttpResponse:
    """
    GET /api/maintenance
    
    Returns current maintenance mode status
    """
    logging.info('Getting maintenance mode status')
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                status = json.load(f)
        else:
            status = {
                "enabled": False,
                "message": "QChat is temporarily under maintenance. Please try again later.",
                "updated_at": None,
                "updated_by": None
            }
        
        logging.info(f'Maintenance mode enabled: {status.get("enabled", False)}')
        
        return func.HttpResponse(
            json.dumps(status),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logging.error(f'Error reading maintenance status: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": f"Failed to read status: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )


def handle_toggle_maintenance(req: func.HttpRequest, file_path: str) -> func.HttpResponse:
    """
    POST /api/maintenance
    
    Enable/disable maintenance mode
    When enabled: ALL USERS (including admins) cannot use chat
    """
    logging.info('Toggling maintenance mode')
    
    try:
        req_body = req.get_json()
        enabled = req_body.get('enabled')
        message = req_body.get('message', 'QChat is temporarily under maintenance. Please try again later.')
        updated_by = req_body.get('updated_by', 'admin')
        
        if enabled is None or not isinstance(enabled, bool):
            return func.HttpResponse(
                json.dumps({"error": "enabled field is required (true/false)"}),
                status_code=400,
                mimetype="application/json"
            )
        
        status = {
            "enabled": enabled,
            "message": message,
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": updated_by
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2)
        
        action = "ENABLED - CHAT DISABLED FOR ALL USERS" if enabled else "DISABLED - CHAT ENABLED"
        logging.warning(f'🚨 MAINTENANCE MODE {action} by {updated_by}')
        
        return func.HttpResponse(
            json.dumps({"success": True, **status}),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logging.error(f'Error toggling maintenance mode: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": f"Failed to update maintenance mode: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )