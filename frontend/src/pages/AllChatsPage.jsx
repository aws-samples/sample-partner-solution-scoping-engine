import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Table from '@cloudscape-design/components/table';
import Box from '@cloudscape-design/components/box';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Toggle from '@cloudscape-design/components/toggle';
import Button from '@cloudscape-design/components/button';
import Pagination from '@cloudscape-design/components/pagination';
import Header from '@cloudscape-design/components/header';
import Alert from '@cloudscape-design/components/alert';
import { getAllChats } from '../services/chatService';
import { formatDate } from '../utils/dateUtils';
import ChatToolsColumn from '../components/ChatToolsColumn';
import ChatNameCell from '../components/ChatNameCell';

function AllChatsPage() {
    const [chats, setChats] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showFinalized, setShowFinalized] = useState(false);
    const [pagination, setPagination] = useState({ pageSize: 20, currentPage: 1 });
    const [totalChats, setTotalChats] = useState(0);
    const [successMessage, setSuccessMessage] = useState('');
    const [selectedChats, setSelectedChats] = useState([]);
    const [bulkDeleting, setBulkDeleting] = useState(false);
    const navigate = useNavigate();
    
    // Fetch chats when component mounts or filter changes
    const fetchChats = async () => {
        try {
            setLoading(true);
            const stageFilter = showFinalized ? 'SOLUTION_FINALIZED' : 'NOT_FINALIZED';
            const offset = (pagination.currentPage - 1) * pagination.pageSize;
            
            console.debug("DEBUG: AllChatsPage - Fetching chats with filter:", stageFilter);
            console.debug("DEBUG: AllChatsPage - Pagination:", { page: pagination.currentPage, pageSize: pagination.pageSize, offset });
            
            const response = await getAllChats(stageFilter, pagination.pageSize, offset);
            
            console.debug("DEBUG: AllChatsPage - API response:", response);
            console.debug("DEBUG: AllChatsPage - Chats received:", response.chats?.length || 0);
            console.debug("DEBUG: AllChatsPage - Total chats:", response.total);
            
            setChats(response.chats);
            setTotalChats(response.total);
            setError(null);
        } catch (err) {
            setError('Failed to load chats. Please try again.');
            console.error('Error fetching chats:', err);
        } finally {
            setLoading(false);
        }
    };
    
    useEffect(() => {
        console.debug("DEBUG: AllChatsPage - Toggle changed to:", showFinalized);
        console.debug("DEBUG: AllChatsPage - Will fetch with stage filter:", showFinalized ? 'SOLUTION_FINALIZED' : 'NOT_FINALIZED');
        fetchChats();
    }, [showFinalized, pagination.currentPage, pagination.pageSize]);
    
    // Handle row click to navigate to chat
    const handleRowClick = (item) => {
        navigate(`/chat/${item.chatId}`);
    };
    
    // Handle chat name update
    const handleChatNameUpdate = (updatedChat) => {
        setChats(prevChats => 
            prevChats.map(chat => 
                chat.chatId === updatedChat.chatId 
                    ? { ...chat, chatName: updatedChat.chatName } 
                    : chat
            )
        );
        setSuccessMessage('Chat name updated successfully');
        setTimeout(() => setSuccessMessage(''), 3000);
    };
    
    // Handle bulk delete
    const handleBulkDelete = async () => {
        if (selectedChats.length === 0) return;
        
        setBulkDeleting(true);
        try {
            const { deleteChat } = await import('../services/chatService');
            
            // Delete all selected chats
            await Promise.all(selectedChats.map(chatId => deleteChat(chatId)));
            
            // Clear selection and refetch data
            setSelectedChats([]);
            setSuccessMessage(`${selectedChats.length} chats deleted successfully`);
            setTimeout(() => setSuccessMessage(''), 3000);
            
            // Reload page to refresh sidebar
            window.location.reload();
        } catch (error) {
            console.error('Error deleting chats:', error);
        } finally {
            setBulkDeleting(false);
        }
    };
    
    // Handle chat deletion
    const handleChatDelete = (chatId) => {
        setChats(prevChats => prevChats.filter(chat => chat.chatId !== chatId));
        setTotalChats(prevTotal => prevTotal - 1);
        setSuccessMessage('Chat deleted successfully');
        setTimeout(() => setSuccessMessage(''), 3000);
        
        // Reload page to refresh sidebar
        window.location.reload();
    };
    
    // Handle feedback submission
    const handleFeedbackSubmit = (result) => {
        setSuccessMessage('Feedback submitted successfully');
        setTimeout(() => setSuccessMessage(''), 3000);
    };
    
    return (
        <Box padding="l">
            <SpaceBetween size="l">
                <Header
                    key="page-header"
                    variant="h1"
                    actions={
                        <SpaceBetween direction="horizontal" size="s" alignItems="center">
                            <Button
                                key="bulk-delete-button"
                                variant="normal"
                                size="small"
                                loading={bulkDeleting}
                                disabled={selectedChats.length === 0}
                                onClick={handleBulkDelete}
                            >
                                Delete {selectedChats.length > 0 ? selectedChats.length : ''} chat{selectedChats.length !== 1 ? 's' : ''}
                            </Button>
                            <Toggle
                                key="finalized-toggle"
                                onChange={({ detail }) => {
                                    console.debug("DEBUG: AllChatsPage - Toggle clicked, new value:", detail.checked);
                                    setShowFinalized(detail.checked);
                                }}
                                checked={showFinalized}
                            >
                                {showFinalized ? 'Showing finalized solutions' : 'Showing in-progress chats'}
                            </Toggle>
                        </SpaceBetween>
                    }
                >
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <img
                            src="/aws_icon_32.jpg" 
                            alt="AWS Logo"
                            style={{ 
                                height: '32px', 
                                marginRight: '10px',
                                display: 'inline-block'
                            }}
                            onError={(e) => {
                                console.error("Failed to load image");
                                e.target.style.display = 'none';
                            }}
                        />
                        <span>All Chats ({totalChats})</span>
                    </div>
                </Header>
                
                {successMessage && (
                    <Alert key="success-alert" type="success" dismissible onDismiss={() => setSuccessMessage('')}>
                        {successMessage}
                    </Alert>
                )}
                
                {error && (
                    <Box key="error-box" color="text-status-error">
                        {error}
                    </Box>
                )}
                
                <Table
                    key="chats-table"
                    variant="embedded"
                    contentDensity="compact"
                    loading={loading}
                    items={chats}
                    selectedItems={selectedChats.map(id => chats.find(chat => chat.chatId === id)).filter(Boolean)}
                    onSelectionChange={({ detail }) => {
                        setSelectedChats(detail.selectedItems.map(item => item.chatId));
                    }}
                    selectionType="multi"
                    columnDefinitions={[
                        {
                            id: 'chatName',
                            header: 'Chat Name',
                            cell: item => (
                                <ChatNameCell 
                                    chatId={item.chatId}
                                    chatName={item.chatName}
                                    onSuccess={handleChatNameUpdate}
                                />
                            ),
                            sortingField: 'chatName'
                        },
                        {
                            id: 'stage',
                            header: 'Stage',
                            cell: item => item.stage,
                            sortingField: 'stage'
                        },
                        {
                            id: 'userId',
                            header: 'Created By',
                            cell: item => item.userId,
                            sortingField: 'userId'
                        },
                        {
                            id: 'createdAt',
                            header: 'Created',
                            cell: item => formatDate(item.createdAt),
                            sortingField: 'createdAt'
                        },
                        {
                            id: 'updatedAt',
                            header: 'Last Updated',
                            cell: item => formatDate(item.updatedAt),
                            sortingField: 'updatedAt'
                        },
                        {
                            id: 'tools',
                            header: 'Tools',
                            cell: item => (
                                <ChatToolsColumn 
                                    chat={item}
                                    onChatNameUpdate={handleChatNameUpdate}
                                    onChatDelete={handleChatDelete}
                                    onFeedbackSubmit={handleFeedbackSubmit}
                                />
                            )
                        }
                    ]}
                    onRowClick={({ detail, event }) => {
                        // Check if the click is coming from the tools column or edit button
                        const toolsColumn = event.target.closest('[data-testid="tools-column"]');
                        const editButton = event.target.closest('[aria-label="Edit chat name"]');
                        if (!toolsColumn && !editButton) {
                            handleRowClick(detail.item);
                        }
                    }}
                    trackBy="chatId"
                    empty={
                        <Box textAlign="center" color="inherit">
                            <b>No chats</b>
                            <Box padding={{ bottom: "s" }} variant="p" color="inherit">
                                {showFinalized 
                                    ? "No finalized solution chats found." 
                                    : "No in-progress chats found."}
                            </Box>
                        </Box>
                    }
                />
                
                {totalChats > pagination.pageSize && (
                    <Pagination
                        key="pagination"
                        currentPageIndex={pagination.currentPage}
                        pagesCount={Math.ceil(totalChats / pagination.pageSize)}
                        onChange={({ detail }) => 
                            setPagination(prev => ({ ...prev, currentPage: detail.currentPageIndex }))}
                    />
                )}
            </SpaceBetween>
        </Box>
    );
}

export default AllChatsPage;
