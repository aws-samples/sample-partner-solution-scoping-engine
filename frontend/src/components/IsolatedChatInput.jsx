import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Textarea, Button } from '@cloudscape-design/components';

const IsolatedChatInput = ({ onSendMessage, isLoading, isConnected, disabled = false, pocMode = false, wafrMode = false, selectedFiles = [] }) => {
  const [inputValue, setInputValue] = useState('');
  const textareaRef = useRef(null);
  
  // Check if we have files selected
  const hasSelectedFiles = selectedFiles.length > 0;

  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current?.querySelector('textarea');
    if (textarea) {
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = 'auto';
      // Force a reflow
      textarea.offsetHeight;
      // Set the new height based on content
      const newHeight = Math.min(Math.max(textarea.scrollHeight, 60), 300);
      textarea.style.height = `${newHeight}px`;
    }
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [inputValue, adjustHeight]);

  const handleInputChange = useCallback(({ detail }) => {
    setInputValue(detail.value);
  }, []);

  const handleKeyPress = useCallback((event) => {
    const key = event.detail?.key || event.key;
    const shiftKey = event.detail?.shiftKey || event.shiftKey;

    if (key === 'Enter' && !shiftKey) {
      event.preventDefault();
      if (inputValue.trim() || hasSelectedFiles) {
        onSendMessage(inputValue);
        setInputValue('');
      }
    }
  }, [inputValue, onSendMessage, hasSelectedFiles]);

  const handleSend = useCallback(() => {
    if (inputValue.trim() || hasSelectedFiles) {
      onSendMessage(inputValue);
      setInputValue('');
    }
  }, [inputValue, onSendMessage, hasSelectedFiles]);

  return (
    <div style={{ position: 'relative' }} ref={textareaRef}>
      <Textarea
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyPress}
        placeholder={disabled ? "Chat is disabled during review" : pocMode ? "Ask about POC funding or upload documents for analysis..." : wafrMode ? "Ask about WAFR or upload architecture documents for assessment..." : "Type your message..."}
        rows={3}
        disabled={disabled || isLoading || !isConnected}
      />
      <Button
        iconName="send"
        variant="primary"
        onClick={handleSend}
        disabled={disabled || isLoading || !isConnected || (!inputValue.trim() && !hasSelectedFiles)}
        loading={isLoading}
        className="send-button-overlay"
        ariaLabel="Send message"
      />
    </div>
  );
};

export default IsolatedChatInput;
