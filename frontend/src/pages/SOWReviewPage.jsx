import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Table from '@cloudscape-design/components/table';
import Box from '@cloudscape-design/components/box';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Pagination from '@cloudscape-design/components/pagination';
import Header from '@cloudscape-design/components/header';
import Alert from '@cloudscape-design/components/alert';
import Badge from '@cloudscape-design/components/badge';
import Link from '@cloudscape-design/components/link';
import { getSOWsForReview } from '../services/sowService';
import { formatDate } from '../utils/dateUtils';
import SOWReviewToolsColumn from '../components/SOWReviewToolsColumn';

function SOWReviewPage() {
    const [sows, setSOWs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [pagination, setPagination] = useState({ pageSize: 20, currentPage: 1 });
    const [totalSOWs, setTotalSOWs] = useState(0);
    const [successMessage, setSuccessMessage] = useState('');
    const navigate = useNavigate();
    
    // Fetch SOWs when component mounts
    const fetchSOWs = async () => {
        try {
            setLoading(true);
            const limit = pagination.pageSize;
            const offset = (pagination.currentPage - 1) * pagination.pageSize;
            
            const response = await getSOWsForReview(limit, offset);
            
            setSOWs(response.sows);
            setTotalSOWs(response.total);
            setError(null);
        } catch (err) {
            setError('Failed to load SOWs for review. Please try again.');
            console.error('Error fetching SOWs:', err);
        } finally {
            setLoading(false);
        }
    };
    
    useEffect(() => {
        fetchSOWs();
    }, [pagination.currentPage, pagination.pageSize]);
    
    // Handle row click to navigate to chat
    const handleRowClick = (item) => {
        navigate(`/chat/${item.chat_id}`);
    };
    
    // Handle feedback submission
    const handleFeedbackSubmit = (result) => {
        setSuccessMessage('SOW feedback submitted successfully');
        setTimeout(() => setSuccessMessage(''), 3000);
        // Refresh the SOW list
        fetchSOWs();
    };
    
    // Format cost as currency
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    };
    
    // Get badge variant for stage
    const getStageVariant = (stage) => {
        switch (stage) {
            case 'SOW_GENERATED':
                return 'blue';
            case 'SOW_REVIEW':
                return 'orange';
            case 'SOW_APPROVED':
                return 'green';
            case 'SOW_REJECTED':
                return 'red';
            default:
                return 'grey';
        }
    };
    
    return (
        <Box padding="l">
            <SpaceBetween size="l">
                <Header variant="h1">
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
                        <span>Statement of Work Review</span>
                    </div>
                </Header>
                
                {successMessage && (
                    <Alert type="success" dismissible onDismiss={() => setSuccessMessage('')}>
                        {successMessage}
                    </Alert>
                )}
                
                {error && (
                    <Alert type="error" dismissible onDismiss={() => setError('')}>
                        {error}
                    </Alert>
                )}
                
                <Table
                    loading={loading}
                    items={sows}
                    columnDefinitions={[
                        {
                            id: 'chatId',
                            header: 'Chat ID',
                            cell: item => item.chat_id.substring(0, 8) + '...',
                            sortingField: 'chat_id'
                        },
                        {
                            id: 'chatName',
                            header: 'Chat Name',
                            cell: item => (
                                <Link
                                    href={`/chat/${item.chat_id}`}
                                    onFollow={(e) => {
                                        e.preventDefault();
                                        navigate(`/chat/${item.chat_id}`);
                                    }}
                                >
                                    {item.chat_name || item.project_title || `Chat ${item.chat_id.substring(0, 8)}...`}
                                </Link>
                            ),
                            sortingField: 'chat_name'
                        },
                        {
                            id: 'customerName',
                            header: 'Customer',
                            cell: item => item.customer_name,
                            sortingField: 'customer_name'
                        },
                        {
                            id: 'templateType',
                            header: 'Template Type',
                            cell: item => {
                                const typeMap = {
                                    'aws_map': 'AWS MAP',
                                    'aws_modernization': 'AWS Modernization',
                                    'custom': 'Custom'
                                };
                                return typeMap[item.template_type] || item.template_type;
                            },
                            sortingField: 'template_type'
                        },
                        {
                            id: 'stage',
                            header: 'Status',
                            cell: item => (
                                <Badge color={getStageVariant(item.stage)}>
                                    {item.stage?.replace('SOW_', '').replace('_', ' ')}
                                </Badge>
                            ),
                            sortingField: 'stage'
                        },
                        {
                            id: 'estimatedCost',
                            header: 'Estimated Cost',
                            cell: item => formatCurrency(item.estimated_project_cost || 0),
                            sortingField: 'estimated_project_cost'
                        },
                        {
                            id: 'generatedDate',
                            header: 'Generated',
                            cell: item => formatDate(item.sow_generated_date),
                            sortingField: 'sow_generated_date'
                        },
                        {
                            id: 'createdBy',
                            header: 'Created By',
                            cell: item => item.created_by,
                            sortingField: 'created_by'
                        },
                        {
                            id: 'actions',
                            header: 'Actions',
                            cell: item => (
                                <SOWReviewToolsColumn 
                                    sow={item}
                                    onFeedbackSubmit={handleFeedbackSubmit}
                                />
                            )
                        }
                    ]}
                    onRowClick={({ detail, event }) => {
                        // Check if the click is coming from the tools column
                        const toolsColumn = event.target.closest('[data-testid="sow-tools-column"]');
                        if (!toolsColumn) {
                            handleRowClick(detail.item);
                        }
                    }}
                    selectionType="single"
                    trackBy="chat_id"
                    empty={
                        <Box textAlign="center" color="inherit">
                            <b>No SOWs to review</b>
                            <Box padding={{ bottom: "s" }} variant="p" color="inherit">
                                No SOW documents found awaiting review.
                            </Box>
                        </Box>
                    }
                    header={
                        <Header
                            counter={`(${totalSOWs})`}
                            description="Review and approve Statement of Work documents"
                        >
                            SOW Documents
                        </Header>
                    }
                />
                
                {totalSOWs > pagination.pageSize && (
                    <Pagination
                        currentPageIndex={pagination.currentPage}
                        pagesCount={Math.ceil(totalSOWs / pagination.pageSize)}
                        onChange={({ detail }) => 
                            setPagination(prev => ({ ...prev, currentPage: detail.currentPageIndex }))}
                    />
                )}
            </SpaceBetween>
        </Box>
    );
}

export default SOWReviewPage;