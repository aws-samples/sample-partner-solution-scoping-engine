import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from "@cloudscape-design/components/box";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Spinner from "@cloudscape-design/components/spinner";
import Link from "@cloudscape-design/components/link";
import Button from "@cloudscape-design/components/button";
import Modal from "@cloudscape-design/components/modal";
import FormField from "@cloudscape-design/components/form-field";
import Input from "@cloudscape-design/components/input";
import Alert from "@cloudscape-design/components/alert";
import { getRecentChats, updateChatName } from '../services/chatService';

const RecentChats = () => {
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingChat, setEditingChat] = useState(null);
  const [newChatName, setNewChatName] = useState('');
  const [nameError, setNameError] = useState('');
  const [updateError, setUpdateError] = useState('');
  const navigate = useNavigate();

  // Fetch recent chats on component mount
  useEffect(() => {
    fetchRecentChats();
  }, []);

  const fetchRecentChats = async () => {
    setLoading(true);
    setError(null);
    try {
      console.debug('RECENT-CHATS-FEATURE-TROUBLESHOOTING: Fetching recent chats');
      const recentChats = await getRecentChats();
      console.debug('RECENT-CHATS-FEATURE-TROUBLESHOOTING: Received recent chats:', recentChats);
      setChats(recentChats);
    } catch (err) {
      console.error('RECENT-CHATS-FEATURE-TROUBLESHOOTING: Error fetching recent chats:', err);
      setError('Failed to load recent chats');
    } finally {
      setLoading(false);
    }
  };

  const handleChatClick = (chatId) => {
    navigate(`/chat/${chatId}`);
  };

  const handleEditClick = (e, chat) => {
    e.stopPropagation(); // Prevent navigation
    setEditingChat(chat);
    setNewChatName(chat.chatName);
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
    setNameError('');
    return true;
  };

  const handleSave = async () => {
    if (!validateChatName(newChatName)) {
      return;
    }

    try {
      const updatedChat = await updateChatName(editingChat.chatId, newChatName);
      
      // Update the chat in the local state
      setChats(chats.map(chat => 
        chat.chatId === editingChat.chatId 
          ? { ...chat, chatName: updatedChat.chatName } 
          : chat
      ));
      
      setEditModalVisible(false);
    } catch (err) {
      console.error('Error updating chat name:', err);
      setUpdateError('Sorry! Something went wrong');
    }
  };

  // Generate navigation items for each chat
  const renderChatItems = () => {
    if (chats.length === 0) {
      return (
        <Box color="text-status-inactive" fontSize="body-s" padding="s">
          No recent chats
        </Box>
      );
    }

    return chats.map((chat) => (
      <Box key={chat.chatId} padding="xs">
        <SpaceBetween direction="horizontal" size="xs">
          <Link 
            href="#" 
            onFollow={(e) => {
              e.preventDefault();
              handleChatClick(chat.chatId);
            }}
          >
            {chat.chatName || `Chat ${chat.chatId.substring(0, 8)}...`}
          </Link>
          <Button 
            iconName="edit" 
            variant="icon" 
            onClick={(e) => handleEditClick(e, chat)}
            ariaLabel={`Edit ${chat.chatName}`}
          />
        </SpaceBetween>
      </Box>
    ));
  };

  if (loading) {
    return (
      <Box padding="s" textAlign="center">
        <Spinner size="normal" />
        <Box padding="s">Loading recent chats...</Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box padding="s">
        <Alert type="error" header="Error loading recent chats">
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <>
      {renderChatItems()}

      {/* Edit Modal */}
      <Modal
        visible={editModalVisible}
        onDismiss={() => setEditModalVisible(false)}
        header="Edit Chat Name"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <div key="cancel-btn">
                <Button variant="link" onClick={() => setEditModalVisible(false)}>
                  Cancel
                </Button>
              </div>
              <div key="save-btn">
                <Button variant="primary" onClick={handleSave}>
                  Save
                </Button>
              </div>
            </SpaceBetween>
          </Box>
        }
      >
        <FormField
          label="Chat Name"
          errorText={nameError}
          description="Maximum 50 characters"
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

export default RecentChats;
