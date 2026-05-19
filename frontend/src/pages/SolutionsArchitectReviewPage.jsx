import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/apiClient';
import Table from '@cloudscape-design/components/table';
import Box from '@cloudscape-design/components/box';
import Button from '@cloudscape-design/components/button';
import Modal from '@cloudscape-design/components/modal';
import Icon from '@cloudscape-design/components/icon';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Pagination from '@cloudscape-design/components/pagination';
import Header from '@cloudscape-design/components/header';
import Alert from '@cloudscape-design/components/alert';
import ReactMarkdown from 'react-markdown';
import { getAllChats, getChatSession } from '../services/chatService';
import { getDocumentCFSignedUrl } from '../services/fileService';
import { formatDate } from '../utils/dateUtils';

// Component to process S3 URLs in preview
const PreviewMessage = ({ content, chatId, messageType }) => {
    const [processedContent, setProcessedContent] = useState(content || '');

    useEffect(() => {
        const processS3Urls = async () => {
            if (!content || !content.includes('s3://')) {
                setProcessedContent(content || '');
                return;
            }

            const s3Pattern = /s3:\/\/([^\/]+)\/(.*?\.(jpg|jpeg|png|gif|bmp|svg|webp))(?:\?versionId=([^\s)]+))?/gi;
            let processed = content;
            
            const matches = [...content.matchAll(s3Pattern)];
            for (const match of matches) {
                const s3Url = match[0];
                const fullPath = match[2];
                const versionId = match[4]; // Version ID from the regex
                
                try {
                    // Use the same logic as ChatPage - pass version ID as third parameter
                    const response = await getDocumentCFSignedUrl(chatId, fullPath, versionId);
                    const signedUrl = response.url || response;
                    processed = processed.replace(s3Url, signedUrl);
                } catch (error) {
                    console.error('Error getting signed URL:', error);
                    processed = processed.replace(s3Url, '[Image unavailable]');
                }
            }
            
            setProcessedContent(processed);
        };

        processS3Urls();
    }, [content, chatId]);

    if (messageType === 'assistant') {
        return (
            <div style={{ maxWidth: '100%' }}>
                <style>
                {`
                    .preview-markdown img {
                        max-width: 500px !important;
                        max-height: 400px !important;
                        width: auto !important;
                        height: auto !important;
                    }
                `}
                </style>
                <div className="preview-markdown">
                    <ReactMarkdown>{processedContent}</ReactMarkdown>
                </div>
            </div>
        );
    } else {
        return <div style={{ whiteSpace: 'pre-wrap' }}>{processedContent}</div>;
    }
};
import SAReviewToolsColumn from '../components/SAReviewToolsColumn';

function SolutionsArchitectReviewPage() {
    const [chats, setChats] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [previewModalVisible, setPreviewModalVisible] = useState(false);
    const [previewChat, setPreviewChat] = useState(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [pagination, setPagination] = useState({ pageSize: 20, currentPage: 1 });
    const [totalChats, setTotalChats] = useState(0);
    const [successMessage, setSuccessMessage] = useState('');
    const navigate = useNavigate();
    
    // Fetch chats when component mounts
    const fetchChats = async () => {
        try {
            setLoading(true);
            // Only show SOLUTION_PROPOSED or SOLUTION_FINALIZED chats
            const stageFilter = 'SOLUTION_REVIEW';
            const offset = (pagination.currentPage - 1) * pagination.pageSize;
            
            const response = await getAllChats(stageFilter, pagination.pageSize, offset);
            
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
        fetchChats();
    }, [pagination.currentPage, pagination.pageSize]);
    
    const handlePreview = async (chat) => {
        setPreviewLoading(true);
        try {
            const chatData = await getChatSession(chat.chatId);
            console.log('Preview chat data:', chatData);
            console.log('Messages:', chatData.messages);
            setPreviewChat(chatData);
            setPreviewModalVisible(true);
        } catch (error) {
            console.error('Error loading chat preview:', error);
        } finally {
            setPreviewLoading(false);
        }
    };
    
    // Handle row click to navigate to chat
    const handleRowClick = async (item) => {
        console.log('handleRowClick called with:', item);
        try {
            setLoading(true);
            
            // Start SA review (create copy if needed)
            console.log('Making API call to:', `/api/sa-review/start/${item.chatId}`);
            const result = await apiClient.post(`/sa-review/start/${item.chatId}`);
            
            console.log('API result:', result);
            
            if (result.success) {
                // Navigate to the SA copy chat
                console.log('Navigating to:', `/chat/${result.sa_copy_chat_id}`);
                
                // Refresh the sidebar
                if (window.refreshRecentChats) {
                    window.refreshRecentChats();
                }
                
                navigate(`/chat/${result.sa_copy_chat_id}`);
            } else {
                console.error('API error:', result.error);
                setError(`Failed to start review: ${result.error}`);
            }
        } catch (err) {
            console.error('Error starting SA review:', err);
            setError('Failed to start review. Please try again.');
        } finally {
            setLoading(false);
        }
    };
    
    // Handle feedback submission
    const handleFeedbackSubmit = (result) => {
        setSuccessMessage('Feedback submitted successfully');
        setTimeout(() => setSuccessMessage(''), 3000);
    };
    
    return (
        <Box padding="l">
            <SpaceBetween size="l">
                <Header key="page-header" variant="h1">
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
                        <span>Review Queue</span>
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
                    key="review-table"
                    variant="embedded"
                    contentDensity="compact"
                    loading={loading}
                    items={chats}
                    columnDefinitions={[
                        {
                            id: 'chatName',
                            header: 'Chat Name',
                            cell: item => (
                                <Button
                                    variant="link"
                                    onClick={() => handlePreview(item)}
                                >
                                    {item.chatName || `Chat ${item.chatId.substring(0, 8)}...`}
                                </Button>
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
                            id: 'actions',
                            header: 'Actions',
                            cell: item => (
                                <Button
                                    variant="primary"
                                    size="small"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        handleRowClick(item);
                                    }}
                                >
                                    Take Review
                                </Button>
                            )
                        }
                    ]}
                    onRowClick={() => {}} // Disable row click since we have buttons
                    trackBy="chatId"
                    empty={
                        <Box textAlign="center" color="inherit">
                            <b>No chats to review</b>
                            <Box padding={{ bottom: "s" }} variant="p" color="inherit">
                                No chats with requested SA reviews found.
                            </Box>
                        </Box>
                    }
                />
                
                {totalChats > pagination.pageSize && (
                    <Pagination
                        currentPageIndex={pagination.currentPage}
                        pagesCount={Math.ceil(totalChats / pagination.pageSize)}
                        onChange={({ detail }) => 
                            setPagination(prev => ({ ...prev, currentPage: detail.currentPageIndex }))}
                    />
                )}
            </SpaceBetween>
            
            {/* Preview Modal */}
            <Modal
                visible={previewModalVisible}
                onDismiss={() => setPreviewModalVisible(false)}
                header={`Preview: ${previewChat?.chat_name || previewChat?.chatName || 'Chat'}`}
                size="large"
                footer={
                    <Box float="right">
                        <SpaceBetween direction="horizontal" size="xs">
                            <Button key="close-button" onClick={() => setPreviewModalVisible(false)}>
                                Close
                            </Button>
                            <Button 
                                key="take-review-button"
                                variant="primary"
                                onClick={() => {
                                    setPreviewModalVisible(false);
                                    // Create a proper item object for handleRowClick
                                    const chatItem = {
                                        chatId: previewChat.chat_id || previewChat.chatId,
                                        chatName: previewChat.chat_name || previewChat.chatName
                                    };
                                    handleRowClick(chatItem);
                                }}
                            >
                                Take Review
                            </Button>
                        </SpaceBetween>
                    </Box>
                }
            >
                {previewChat ? (
                    <Box>
                        <SpaceBetween direction="vertical" size="m">
                            <div>
                                <strong>Stage:</strong> {previewChat.stage || 'Unknown'}
                            </div>
                            <div>
                                <strong>Created by:</strong> {previewChat.user_id || previewChat.userId || 'Unknown'}
                            </div>
                            <div>
                                <strong>Messages ({previewChat.messages?.length || 0}):</strong>
                                <Box padding={{ top: "s" }} style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                    {previewChat.messages?.length > 0 ? (
                                        previewChat.messages.map((msg, index) => {
                                            // Handle DynamoDB format {M: {role: {S: "user"}, content: {S: "text"}}}
                                            const role = msg.M?.role?.S || msg.role;
                                            const content = msg.M?.content?.S || msg.content;
                                            const timestamp = msg.M?.message_timestamp?.S || msg.message_timestamp || new Date().toISOString();
                                            const messageType = role === 'user' ? 'user' : role === 'system' ? 'system' : 'assistant';
                                            
                                return (
                                                <div key={index} style={{ 
                                                    display: 'flex', 
                                                    alignItems: 'flex-start',
                                                    marginBottom: '6px',
                                                    paddingBottom: '6px',
                                                    borderBottom: index < previewChat.messages.length - 1 ? '1px solid #e9ebed' : 'none',
                                                    width: '90%'
                                                }}>
                                                    {messageType === 'assistant' && (
                                                        <div style={{ 
                                                            width: '20px', 
                                                            height: '20px', 
                                                            borderRadius: '50%', 
                                                            backgroundColor: '#0073bb', 
                                                            display: 'flex', 
                                                            alignItems: 'center', 
                                                            justifyContent: 'center',
                                                            marginRight: '8px',
                                                            marginTop: '12px',
                                                            flexShrink: 0
                                                        }}>
                                                            <Icon name="gen-ai" variant="inverted" size="small" />
                                                        </div>
                                                    )}
                                                    {messageType === 'user' && (
                                                        <div style={{ 
                                                            width: '20px', 
                                                            height: '20px', 
                                                            borderRadius: '50%', 
                                                            backgroundColor: '#687078', 
                                                            display: 'flex', 
                                                            alignItems: 'center', 
                                                            justifyContent: 'center',
                                                            marginRight: '8px',
                                                            marginTop: '12px',
                                                            color: 'white',
                                                            fontSize: '10px',
                                                            fontWeight: 'bold',
                                                            flexShrink: 0
                                                        }}>
                                                            U
                                                        </div>
                                                    )}
                                                    {messageType === 'system' && (
                                                        <div style={{ 
                                                            width: '20px', 
                                                            height: '20px', 
                                                            borderRadius: '50%', 
                                                            backgroundColor: '#0073bb', 
                                                            display: 'flex', 
                                                            alignItems: 'center', 
                                                            justifyContent: 'center',
                                                            marginRight: '8px',
                                                            marginTop: '12px',
                                                            flexShrink: 0
                                                        }}>
                                                            <Icon name="notification" variant="inverted" size="small" />
                                                        </div>
                                                    )}
                                                    <Box
                                                        padding={{ top: 's', bottom: 's', left: 'm', right: 'm' }}
                                                        color={messageType === 'user' ? 'text-body-secondary' : 'text-body-primary'}
                                                        backgroundColor={messageType === 'user' ? 'background-container' : 'background-container-alt'}
                                                        borderRadius="l"
                                                        fontSize="body-xs"
                                                        style={{ flex: 1 }}
                                                    >
                                                        <Box style={messageType === 'system' ? { fontStyle: 'italic' } : {}}>
                                                            <PreviewMessage 
                                                                content={content} 
                                                                chatId={previewChat.chat_id || previewChat.chatId}
                                                                messageType={messageType}
                                                            />
                                                        </Box>
                                                    </Box>
                                                </div>
                                            );
                                        })
                                    ) : (
                                        <div>No messages found</div>
                                    )}
                                </Box>
                            </div>
                        </SpaceBetween>
                    </Box>
                ) : (
                    <div>Loading preview...</div>
                )}
            </Modal>
        </Box>
    );
}

export default SolutionsArchitectReviewPage;
