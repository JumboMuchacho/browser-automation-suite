#!/usr/bin/env python3
"""
Process Manager for Popup Detection
Allows easy addition of new processes to the detection flow
"""

import os
import time
import logging
import subprocess
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class ProcessStep(ABC):
    """Abstract base class for process steps"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)
    
    @abstractmethod
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the process step and return updated data"""
        pass
    
    def __str__(self):
        return f"{self.name} ({'enabled' if self.enabled else 'disabled'})"

class PopupDetectionStep(ProcessStep):
    """Popup detection process step"""
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            return data
            
        logger.info(f"Executing {self.name}")
        # Popup detection logic here
        data["popup_detected"] = True  # Placeholder
        return data

class TelegramNotificationStep(ProcessStep):
    """Telegram notification process step"""
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            return data
            
        logger.info(f"Executing {self.name}")
        # Telegram notification logic here
        data["notification_sent"] = True  # Placeholder
        return data

class AlarmSoundStep(ProcessStep):
    """Alarm sound process step"""
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            return data
            
        logger.info(f"Executing {self.name}")
        # Alarm sound logic here
        data["alarm_played"] = True  # Placeholder
        return data

class ScreenshotStep(ProcessStep):
    """Screenshot capture process step"""
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            return data
            
        logger.info(f"Executing {self.name}")
        # Screenshot logic here
        data["screenshot_taken"] = True  # Placeholder
        return data

class CustomProcessStep(ProcessStep):
    """Custom process step for user-defined actions"""
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            return data
            
        logger.info(f"Executing custom step: {self.name}")
        
        # Execute custom command if specified
        command = self.config.get("command")
        if command:
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                data[f"{self.name}_output"] = result.stdout
                data[f"{self.name}_error"] = result.stderr
                data[f"{self.name}_return_code"] = result.returncode
                logger.info(f"Custom command executed: {command}")
            except Exception as e:
                logger.error(f"Custom command failed: {e}")
                data[f"{self.name}_error"] = str(e)
        
        return data

class ProcessManager:
    """Manages the execution flow of process steps"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.steps: List[ProcessStep] = []
        self._load_steps()
    
    def _load_steps(self):
        """Load process steps from configuration"""
        steps_config = self.config.get("process_steps", {})
        
        # Default steps
        default_steps = {
            "popup_detection": PopupDetectionStep,
            "screenshot": ScreenshotStep,
            "telegram_notification": TelegramNotificationStep,
            "alarm_sound": AlarmSoundStep
        }
        
        # Load default steps
        for step_name, step_class in default_steps.items():
            step_config = steps_config.get(step_name, {})
            step = step_class(step_name, step_config)
            self.steps.append(step)
        
        # Load custom steps
        custom_steps = steps_config.get("custom", [])
        for custom_step_config in custom_steps:
            step_name = custom_step_config.get("name", "custom_step")
            step = CustomProcessStep(step_name, custom_step_config)
            self.steps.append(step)
    
    def add_step(self, step: ProcessStep):
        """Add a new process step"""
        self.steps.append(step)
        logger.info(f"Added process step: {step}")
    
    def execute_flow(self, initial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all process steps in sequence"""
        data = initial_data.copy()
        
        logger.info(f"Starting process flow with {len(self.steps)} steps")
        
        for step in self.steps:
            if step.enabled:
                try:
                    data = step.execute(data)
                    logger.info(f"Step {step.name} completed")
                except Exception as e:
                    logger.error(f"Step {step.name} failed: {e}")
                    data[f"{step.name}_error"] = str(e)
            else:
                logger.info(f"Skipping disabled step: {step.name}")
        
        logger.info("Process flow completed")
        return data
    
    def list_steps(self):
        """List all process steps"""
        print("Process Steps:")
        for i, step in enumerate(self.steps, 1):
            print(f"  {i}. {step}")

# Example usage and configuration
def create_example_config():
    """Create an example configuration with custom steps"""
    return {
        "process_steps": {
            "popup_detection": {
                "enabled": True,
                "timeout": 5
            },
            "screenshot": {
                "enabled": True,
                "format": "png"
            },
            "telegram_notification": {
                "enabled": True,
                "include_screenshot": True
            },
            "alarm_sound": {
                "enabled": True,
                "volume": 0.8
            },
            "custom": [
                {
                    "name": "log_to_file",
                    "enabled": True,
                    "command": "echo 'Popup detected at $(date)' >> popup_log.txt"
                },
                {
                    "name": "send_email",
                    "enabled": False,
                    "command": "mail -s 'Popup Alert' admin@example.com < popup_log.txt"
                }
            ]
        }
    }

if __name__ == "__main__":
    # Example usage
    config = create_example_config()
    manager = ProcessManager(config)
    
    print("Available process steps:")
    manager.list_steps()
    
    # Execute flow
    initial_data = {"popup_window": "CDwindow", "timestamp": time.time()}
    result = manager.execute_flow(initial_data)
    
    print(f"Flow result: {result}") 