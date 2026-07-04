import json
from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class PluginMapper(BaseMapper):
    def __init__(self):
        self.servertype_to_plugin_id = {}
        self.next_plugin_id = 1
        self.emitted_plugins = set()

    def extract_plugins(self, row: Dict[str, Any]):
        """Pass 1: Collect unique servertypes and assign plugin IDs."""
        servertype = str(row.get("servertype", "")).strip().lower()
        if not servertype or servertype == "none":
            return
            
        if servertype not in self.servertype_to_plugin_id:
            self.servertype_to_plugin_id[servertype] = self.next_plugin_id
            self.next_plugin_id += 1

    def map_plugins(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Pass 2: Emit the actual plugin instances for the target database."""
        servertype = str(row.get("servertype", "")).strip().lower()
        if not servertype or servertype == "none":
            return []
            
        plugin_id = self.servertype_to_plugin_id.get(servertype)
        if not plugin_id:
            return []
            
        if plugin_id in self.emitted_plugins:
            return []
            
        self.emitted_plugins.add(plugin_id)
        
        # We only generate basic plugins for provisioning based on servertype
        plugin_dict = {
            "id": plugin_id,
            "provider": servertype,
            "name": f"Imported {servertype.capitalize()}",
            "type": "provisioning",
            "is_active": 0, # Needs manual configuration after migration
            "config": None,
            "created_at": None,
            "updated_at": None
        }
        
        return [("plugins", plugin_dict)]
