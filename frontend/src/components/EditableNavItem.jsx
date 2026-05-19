import React, { useState } from 'react';
import Button from "@cloudscape-design/components/button";
import Modal from "@cloudscape-design/components/modal";
import Box from "@cloudscape-design/components/box";
import SpaceBetween from "@cloudscape-design/components/space-between";
import FormField from "@cloudscape-design/components/form-field";
import Input from "@cloudscape-design/components/input";
import Alert from "@cloudscape-design/components/alert";
import { updateChatName } from '../services/chatService';

/**
 * A component that renders an edit button for a chat item
 */
const EditableNavItem = ({ chat }) => {
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [newChatName, setNewChatName] = useState(chat.chatName || '');
  const [nameError, setNameError] = useState('');
  const [updateError, setUpdateError] = useState('');

  const handleEditClick = (e) => {
    e.stopPropagation();
    e.preventDefault();
    setNewChatName(chat.chatName || '');
    setNameError('');
    setUpdateError('');
    setEditModalVisible(true);
  };

  const validateChatName = (name) => {
    if (!name.trim()) {
      setNameError('Chat name cannot be empty');
      return false;
    }
    if (name.length > 50) {
      setNameError('Chat name cannot exceed 50 characters');
      return false;
    }
    // Only allow letters, numbers, and hyphens with no spaces
    const nameRegex = /^[a-zA-Z0-9-]+$/;
    if (!nameRegex.test(name)) {
      setNameError('Chat name can only contain letters, numbers, and hyphens (no spaces)');
      return false;
    }
    setNameError('');
    return true;
  };

  const handleSave = async () => {
    if (!validateChatName(newChatName)) {
      return;
    }

    try {
      await updateChatName(chat.chatId, newChatName);
      setEditModalVisible(false);
      // Force reload to update the navigation
      window.location.reload();
    } catch (err) {
      console.error('Error updating chat name:', err);
      setUpdateError('Sorry! Something went wrong');
    }
  };

  return (
    <>
      <Button 
        iconName="edit" 
        variant="icon" 
        onClick={handleEditClick}
        ariaLabel={`Edit ${chat.chatName}`}
      />

      {/* Edit Modal */}
      <Modal
        visible={editModalVisible}
        onDismiss={() => setEditModalVisible(false)}
        header="Edit Chat Name"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link" onClick={() => setEditModalVisible(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSave}>
                Save
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <FormField
          label="Chat Name"
          errorText={nameError}
          description="Use letters, numbers, and hyphens only (no spaces)"
        >
          <Input
            value={newChatName}
            onChange={({ detail }) => setNewChatName(detail.value)}
            autoFocus
            maxLength={50}
          />
        </FormField>
        
        {updateError && (
          <Alert type="error" header="Error">
            {updateError}
          </Alert>
        )}
      </Modal>
    </>
  );
};

export default EditableNavItem;
