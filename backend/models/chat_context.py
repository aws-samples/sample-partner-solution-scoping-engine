# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Chat context management module.
"""

import logging
import re
from .chat import get_chat, save_chat

logger = logging.getLogger(__name__)

def extract_context_variables(messages):
    """
    Extract context variables from previous messages.
    
    Args:
        messages (list): List of message dictionaries with 'role' and 'content'
        
    Returns:
        dict: Dictionary of extracted context variables
    """
    context = {}
    
    # Extract initial question from first user message
    user_messages = [m for m in messages if m['role'] == 'user']
    if user_messages:
        context['initial-question'] = user_messages[0]['content']
    
    # Extract high-level and deep-dive questions from assistant messages
    for msg in messages:
        if msg['role'] == 'assistant':
            content = msg['content']
            
            # Extract high-level questions
            high_level_match = re.search(r'High-level questions:(.*?)(?=Deep-dive|$)', content, re.DOTALL)
            if high_level_match:
                context['high-level-questions'] = high_level_match.group(1).strip()
            
            # Extract deep-dive questions
            deep_dive_match = re.search(r'Deep-dive (?:technical )?questions:(.*?)(?=\n\n|$)', content, re.DOTALL)
            if deep_dive_match:
                context['deep-dive-questions'] = deep_dive_match.group(1).strip()
    
    return context

def update_chat_context_variables(chat_id, context_variables):
    """
    Update context variables for a specific chat session.
    
    Args:
        chat_id (str): The ID of the chat session
        context_variables (dict): Dictionary of context variables to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the current chat data
        chat_data = get_chat(chat_id)
        if not chat_data:
            logger.warning(f"Chat not found for context update: chat_id={chat_id}")
            return False
        
        # Update or add context variables
        if 'ContextVariables' not in chat_data:
            chat_data['ContextVariables'] = {}
        
        for key, value in context_variables.items():
            chat_data['ContextVariables'][key] = value
        
        # Save the updated chat data
        save_chat(chat_data)
        logger.info(f"Context variables updated: chat_id={chat_id}, vars={len(context_variables)}")
        return True
    except Exception as e:
        logger.error(f"Update context variables failed: chat_id={chat_id}, error={str(e)}")
        return False
