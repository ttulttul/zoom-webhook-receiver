import importlib
import os
from fastapi import FastAPI

def load_hooks(app: FastAPI):
    hooks_dir = os.path.dirname(__file__)
    for filename in os.listdir(hooks_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = f'app.hooks.{filename[:-3]}'
            module = importlib.import_module(module_name)
            if hasattr(module, 'setup'):
                module.setup(app)
