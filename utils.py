import json
import inspect
from typing import Callable, Any, Dict

class AgentUtils:
    """Simple utilities for function signature extraction and tool execution"""
    
    @staticmethod
    def get_function_signatures(functions: list[Callable]) -> str:
        """
        Extract function signatures for LLM prompt
        
        Args:
            functions: List of callable functions
            
        Returns:
            JSON string with all function signatures
        """
        signatures = []
        
        for func in functions:
            # Get function signature
            sig = inspect.signature(func)
            
            # Build signature dict
            signature = {
                "name": func.__name__,
                "description": func.__doc__.strip() if func.__doc__ else "",
                "parameters": {
                    "properties": {}
                }
            }
            
            # Extract parameters
            for param_name, param in sig.parameters.items():
                param_type = "str"  # default
                if param.annotation != inspect.Parameter.empty:
                    param_type = param.annotation.__name__
                
                signature["parameters"]["properties"][param_name] = {
                    "type": param_type
                }
            
            signatures.append(signature)
        
        return json.dumps(signatures, indent=2)
    
    @staticmethod
    def run_tool(tool_call_json: str, functions: list[Callable]) -> Any:
        """
        Execute a tool call
        
        Args:
            tool_call_json: JSON string with tool call info
            functions: List of available functions
            
        Returns:
            Result of function execution
        """
        tool_call = json.loads(tool_call_json)
        function_name = tool_call["name"]
        arguments = tool_call["arguments"]
        
        # Find the function
        func_dict = {f.__name__: f for f in functions}
        
        if function_name not in func_dict:
            return f"Error: Function {function_name} not found"
        
        func = func_dict[function_name]
        
        try:
            # Execute function
            result = func(**arguments)
            return result
        except Exception as e:
            return f"Error executing {function_name}: {str(e)}"