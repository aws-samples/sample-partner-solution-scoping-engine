import React, { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import {
    SpaceBetween,
    Button,
    Modal,
    Box,
    RadioGroup,
    FormField,
    Spinner,
    Icon,
    Input,
    Alert,
    Textarea,
    ExpandableSection,
    Select
} from '@cloudscape-design/components';
// Removed uploadFile import - file upload handled by parent component
import { getChatSession } from '../services/chatService';
import { sendMessage } from '../services/chatService';
import { FileClassificationUtils } from '../services/fileService.js';
import FileClassificationModal from './FileClassificationModal';

// Custom Upload Icon
const UploadIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M5 5h22" />
        <path d="M16 23V9m0 0l-7 7m7-7l7 7" />
    </svg>
);

// Custom Calculator Icon
const CalculatorIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" viewBox="0 0 32 34">
        <rect x="4" y="2" width="24" height="26" rx="4" ry="4" stroke="currentColor" fill="none" strokeWidth="2" />
        <rect x="8" y="6" width="16" height="4" fill="currentColor" />
        <circle cx="10" cy="14" r="2" fill="currentColor" />
        <circle cx="16" cy="14" r="2" fill="currentColor" />
        <circle cx="22" cy="14" r="2" fill="currentColor" />
        <circle cx="10" cy="20" r="2" fill="currentColor" />
        <circle cx="16" cy="20" r="2" fill="currentColor" />
        <circle cx="22" cy="20" r="2" fill="currentColor" />
        <circle cx="16" cy="25" r="2" fill="currentColor" />
    </svg>
);

// Custom Share Icon (for Diagram)
const ShareIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 34" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="22" y="4" width="8" height="8" />
        <rect x="2" y="12" width="8" height="8" />
        <rect x="22" y="20" width="8" height="8" />
        <path d="m10 14 12-4" />
        <path d="m10 18 12 4" />
    </svg>
);

// Custom CloudFormation Icon
const CloudFormationIcon = () => (
    <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" fill="none">
        <path d="M20.4,15.985 L22.4,15.985 L22.4,15.184 L20.4,15.184 L20.4,15.985 Z M10.4,20.793 L12.4,20.793 L12.4,19.991 L10.4,19.991 L10.4,20.793 Z M6.4,20.793 L9.2,20.793 L9.2,19.991 L6.4,19.991 L6.4,20.793 Z M6.4,18.389 L11.2,18.389 L11.2,17.587 L6.4,17.587 L6.4,18.389 Z M6.4,13.581 L10,13.581 L10,12.78 L6.4,12.78 L6.4,13.581 Z M6.4,15.985 L19.6,15.985 L19.6,15.184 L6.4,15.184 L6.4,15.985 Z"
            fill="currentColor" />
        <path d="M14,24.799 L5.6,24.799 L5.6,11.178 L14,11.178 L14,14.382 L15.6,14.382 L15.6,10.777 C15.6,10.577 15.44,10.376 15.2,10.376 L5.2,10.376 C4.979,10.376 4.8,10.577 4.8,10.777 L4.8,25.2 C4.8,25.4 4.979,25.6 5.2,25.6 L15.2,25.6 C15.44,25.6 15.6,25.4 15.6,25.2 L15.6,17.187 L14,17.187 L14,24.799 Z"
            stroke="currentColor" strokeWidth="1" fill="none" />
        <path d="M26.4,14.782 C26.4,17.372 24.469,18.273 23.437,18.387 L16.4,18.389 L16.4,17.587 L22.8,17.587 C22.878,17.785 25.6,17.285 25.6,14.782 C25.6,12.506 23.545,12.043 23.134,11.974 C22.928,11.939 22.784,11.753 22.802,11.545 C22.802,11.538 22.603,11.53 22.804,11.523 C22.782,10.236 21.992,9.834 21.65,9.72 C21.012,9.508 20.3,9.711 19.924,10.216 C19.836,10.334 19.692,10.395 19.544,10.372 C19.399,10.35 19.277,10.25 19.227,10.111 C18.979,9.414 18.618,8.963 18.117,8.461 C16.864,7.215 15.162,6.871 13.57,7.541 C12.735,7.893 12.005,8.691 11.569,9.731 L10.831,9.42 C11.348,8.19 12.234,7.235 13.26,6.803 C15.162,6.002 17.189,6.41 18.682,7.894 C19.11,8.323 19.464,8.741 19.74,9.281 C20.337,8.839 21.143,8.707 21.903,8.96 C22.876,9.283 23.491,10.128 23.59,11.252 C24.952,11.595 26.4,12.684 26.4,14.782 L26.4,14.782 Z"
            stroke="currentColor" strokeWidth="1.2" fill="none" />
    </svg>
);

// Custom Statement of Work Icon
const StatementOfWorkIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 34" fill="none">
        <path d="M8 4h12l6 6v18a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" stroke="currentColor" strokeWidth="2" />
        <path d="M20 4v6h6" stroke="currentColor" strokeWidth="2" />

        <line x1="10" y1="14" x2="20" y2="14" stroke="currentColor" strokeWidth="1.5" />
        <line x1="10" y1="18" x2="22" y2="18" stroke="currentColor" strokeWidth="1.5" />
        <line x1="10" y1="22" x2="18" y2="22" stroke="currentColor" strokeWidth="1.5" />
        <line x1="10" y1="26" x2="16" y2="26" stroke="currentColor" strokeWidth="1.5" />
    </svg>
);

// Custom Partner Funding Icon
const PartnerFundingIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M16 4v24" strokeWidth="1.5" />
        <path d="M22 12c0-2.2-2.7-4-6-4s-6 1.8-6 4c0 2.2 2.7 4 6 4 3.3 0 6 1.8 6 4s-2.7 4-6 4-6-1.8-6-4" />
    </svg>
);

// Custom Document Review Icon
const POCFundingReviewIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none">
        {/* Document outline */}
        <path d="M6 4 L22 4 L26 8 L26 28 L6 28 Z" stroke="currentColor" strokeWidth="2" fill="none" />

        {/* Document fold corner */}
        <path d="M22 4 L22 8 L26 8" stroke="currentColor" strokeWidth="2" fill="none" />

        {/* Document content lines */}
        <line x1="10" y1="12" x2="22" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <line x1="10" y1="16" x2="18" y2="16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <line x1="10" y1="20" x2="22" y2="20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />

        {/* Magnifying glass for review */}
        <circle cx="24" cy="16" r="5" stroke="currentColor" strokeWidth="2" fill="none" />
        <line x1="27" y1="19" x2="30" y2="22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />

        {/* Checkmark inside magnifying glass */}
        <polyline points="21,16 23,18 27,14" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
);

// Custom Calculator Link Icon
const CalculatorLinkIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M10 16a5 5 0 0 0 7.07.71l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5"/>
    <path d="M14 14a5 5 0 0 0-7.07-.71l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5"/>
    <rect x="17" y="20" width="8" height="8" rx="0.5" strokeWidth="1.2"/>
    <line x1="17" y1="22.5" x2="25" y2="22.5" strokeWidth="0.8"/>
    <circle cx="19" cy="25" r="0.4" fill="currentColor"/>
    <circle cx="21" cy="25" r="0.4" fill="currentColor"/>
    <circle cx="23" cy="25" r="0.4" fill="currentColor"/>
  </svg>
);

/**
 * ChatToolbar component that provides tools for the chat interface
 * Supports file upload functionality and additional tools based on conversation stage
 */
const ChatToolbar = forwardRef(({
    chatId,
    onSendMessage,
    refreshTrigger,
    disabled = false,
    onNewMessage,
    onFileUpload,
    fileInputRef,
    chatLoading,
    isConnected,
    selectedFiles = [],
    assistantPersona = null
}, ref) => {
    const [isUploadModalVisible, setIsUploadModalVisible] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [uploadOption, setUploadOption] = useState('read');
    const [isUploading, setIsUploading] = useState(false);
    const [uploadError, setUploadError] = useState('');
    const [uploadSuccess, setUploadSuccess] = useState(false);
    const [currentStage, setCurrentStage] = useState('');
    const [isLoading, setIsLoading] = useState(true);

    // Use selected files from parent component
    const hasSelectedFiles = selectedFiles.length > 0;

    // Debug effect to monitor selected files changes
    useEffect(() => {
        console.log('📁 Selected files changed:', selectedFiles.map(f => f.name));
        console.log('📁 hasSelectedFiles:', hasSelectedFiles);
    }, [selectedFiles, hasSelectedFiles]);

    // Universal file classification state
    const [isFileClassificationModalVisible, setIsFileClassificationModalVisible] = useState(false);
    const [fileClassifications, setFileClassifications] = useState({});
    const [autoClassifications, setAutoClassifications] = useState({});
    const [pendingAction, setPendingAction] = useState(null);

    // Removed useImperativeHandle - will add after handleSendMessage is defined

    // Fetch current conversation stage
    const fetchChatStage = async () => {
        try {
            setIsLoading(true);
            const chatData = await getChatSession(chatId);
            const stage = chatData.stage || '';
            setCurrentStage(stage);
            console.debug(`Current conversation stage: ${stage}`);
        } catch (error) {
            console.error('Error fetching chat stage:', error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (chatId) {
            fetchChatStage();
        }
    }, [chatId]);



    // Re-fetch stage when refreshTrigger changes (after assistant responses)
    useEffect(() => {
        if (chatId && refreshTrigger > 0) {
            console.log(`Refreshing chat stage due to trigger: ${refreshTrigger}`);
            fetchChatStage();
        }
    }, [refreshTrigger, chatId]);

    // Define tools by category (shared between enablement and tooltip logic)
    const solutionCreationTools = ['Create Architecture Diagram', 'Pricing Calculator', 'Calculator Link', 'Statement of Work', 'Generate CloudFormation Templates'];
    const fundingAnalysisTools = ['Partner Funding Analysis'];
    const finalStageTools = ['Terraform'];

    // Check if tools should be enabled based on conversation stage and tool type
    const getToolEnabledState = (toolName) => {
        // Upload files is always enabled for all personas
        if (toolName === 'Upload files') {
            return true;
        }

        // AWS Solutions Assistant: Tools enabled based on stage
        if (assistantPersona === 'aws_solutions_assistant') {
            if (currentStage === 'SOLUTION_PROPOSED') {
                // In SOLUTION_PROPOSED stage: only diagram and calculator enabled
                return ['Create Architecture Diagram', 'Pricing Calculator'].includes(toolName);
            }
            
            if (currentStage === 'SOLUTION_FINALIZED') {
                // In SOLUTION_FINALIZED stage: all tools enabled
                return solutionCreationTools.includes(toolName) || 
                       fundingAnalysisTools.includes(toolName) || 
                       finalStageTools.includes(toolName);
            }
            
            // Other stages: no tools enabled (except upload which is handled above)
            return false;
        }

        // APN Funding Assistant: Tools available in later stages (when analyzing proposed solutions)
        if (assistantPersona === 'apn_funding_assistant') {
            // Partner Funding Analysis has special logic - enabled when files are selected OR in later stages
            if (toolName === 'Partner Funding Analysis') {
                return false;
            }

            // Other tools available in later stages for funding analysis
            if (solutionCreationTools.includes(toolName)) {
                return false;
            }

            if (finalStageTools.includes(toolName)) {
                return false;
            }
        }

        // Default behavior for other personas: available in any stage
        return true;
    };

    // Log the current stage for debugging
    useEffect(() => {
        console.log(`Current stage: ${currentStage}`);
        console.log(`Has selected files: ${hasSelectedFiles}`);
        console.log(`Create Architecture Diagram enabled: ${getToolEnabledState('Create Architecture Diagram')}`);
        console.log(`Pricing Calculator enabled: ${getToolEnabledState('Pricing Calculator')}`);
        console.log(`Partner Funding Analysis enabled: ${getToolEnabledState('Partner Funding Analysis')}`);
        console.log(`Statement of Work enabled: ${getToolEnabledState('Statement of Work')}`);
        console.log(`Generate CloudFormation Templates enabled: ${getToolEnabledState('Generate CloudFormation Templates')}`);
    }, [currentStage, hasSelectedFiles]);

    // Removed unused upload modal handlers - file upload handled by parent component

    // Universal file classification logic - now with async support
    const [shouldClassify, setShouldClassify] = useState(false);
    const [classificationOptions, setClassificationOptions] = useState([]);
    const [validationResult, setValidationResult] = useState({ valid: true, missing: [] });

    // Load classification configuration on mount and when assistant changes
    useEffect(() => {
        const loadClassificationConfig = async () => {
            try {
                const shouldUse = await FileClassificationUtils.shouldUseClassification(assistantPersona);
                setShouldClassify(shouldUse);

                if (shouldUse) {
                    const options = await FileClassificationUtils.getSelectOptions(assistantPersona);
                    setClassificationOptions(options);
                }
            } catch (error) {
                console.error('Error loading classification config:', error);
                setShouldClassify(false);
                setClassificationOptions([]);
            }
        };

        loadClassificationConfig();
    }, [assistantPersona]);

    // Load auto-classifications when files change
    useEffect(() => {
        const loadAutoClassifications = async () => {
            if (!shouldClassify || !hasSelectedFiles) {
                setAutoClassifications({});
                return;
            }

            try {
                const autoClassifs = await FileClassificationUtils.getAutoClassifications(selectedFiles, assistantPersona);
                setAutoClassifications(autoClassifs);
            } catch (error) {
                console.error('Error loading auto classifications:', error);
                setAutoClassifications({});
            }
        };

        loadAutoClassifications();
    }, [selectedFiles, assistantPersona, shouldClassify, hasSelectedFiles]);

    // Update validation when files or classifications change
    useEffect(() => {
        const updateValidation = async () => {
            if (!shouldClassify || !hasSelectedFiles) {
                setValidationResult({ valid: true, missing: [] });
                return;
            }

            try {
                const validation = await FileClassificationUtils.validateRequiredFiles(
                    selectedFiles,
                    fileClassifications,
                    assistantPersona
                );
                setValidationResult(validation);
            } catch (error) {
                console.error('Error validating files:', error);
                setValidationResult({ valid: true, missing: [] });
            }
        };

        updateValidation();
    }, [selectedFiles, fileClassifications, assistantPersona, shouldClassify, hasSelectedFiles]);

    const validateFilesNeedClassification = async () => {
        if (!hasSelectedFiles || !shouldClassify) {
            return false;
        }
        try {
            return await FileClassificationUtils.validateFilesNeedClassification(selectedFiles, assistantPersona);
        } catch (error) {
            console.error('Error checking if files need classification:', error);
            return false;
        }
    };

    // Handle universal file classification
    const handleFileClassification = (fileName, classificationType) => {
        setFileClassifications(prev => ({
            ...prev,
            [fileName]: classificationType
        }));
    };

    // Get classification options for select component
    const getSelectOptions = () => {
        return classificationOptions;
    };

    // Get current classification for a file
    const getFileClassification = (fileName) => {
        const classification = fileClassifications[fileName];
        if (classification) {
            const options = getSelectOptions();
            return options.find(opt => opt.value === classification) || null;
        }

        // Try auto-classification for display purposes
        const autoClassificationType = autoClassifications[fileName];
        if (autoClassificationType) {
            const options = getSelectOptions();
            const autoOption = options.find(opt => opt.value === autoClassificationType);
            if (autoOption) {
                // Return a modified option to show it's auto-detected
                return {
                    ...autoOption,
                    label: `${autoOption.label} (Auto-detected)`,
                    value: autoClassificationType
                };
            }
        }

        // Default to auto-detect option
        const options = getSelectOptions();
        return options.find(opt => opt.value === '') || null;
    };

    // Execute action after classification is complete
    const executeActionWithClassifications = () => {
        if (!pendingAction) return;

        const { actionType, toolName, message, options } = pendingAction;

        // Add classifications to options
        const enhancedOptions = {
            ...options,
            fileClassifications: fileClassifications
        };

        console.log('🔧 executeActionWithClassifications - Manual classifications applied:', fileClassifications);

        // Clear pending state
        setIsFileClassificationModalVisible(false);
        setFileClassifications({});
        setPendingAction(null);

        // Execute the original action
        if (actionType === 'tool') {
            executeToolAction(toolName, enhancedOptions);
        } else if (actionType === 'message') {
            if (onSendMessage) {
                onSendMessage(message, enhancedOptions);
            }
        }
    };

    // Check if action needs classification
    const checkAndHandleClassification = async (actionType, toolName = null, message = '', options = {}) => {
        try {
            const needsClassification = await validateFilesNeedClassification();

            console.log('🔧 checkAndHandleClassification:', {
                actionType,
                toolName,
                shouldClassify,
                hasSelectedFiles,
                needsClassification,
                assistantPersona,
                selectedFilesCount: selectedFiles.length,
                hasAutoClassifications: !!options.fileClassifications
            });

            // If auto-classifications are already provided and manual classification is not needed, skip modal
            if (shouldClassify && hasSelectedFiles && options.fileClassifications && !needsClassification) {
                console.log('🔧 Auto-classifications already provided, no manual classification needed');
                return false; // No modal needed, proceed with auto-classifications
            }

            if (shouldClassify && hasSelectedFiles && needsClassification) {
                console.log('🔧 Files need manual classification - showing modal');
                setPendingAction({ actionType, toolName, message, options });

                // Pre-populate with automatic classifications
                console.log('🔧 Auto classifications for modal:', autoClassifications);
                setFileClassifications(autoClassifications);

                setIsFileClassificationModalVisible(true);
                return true; // Indicates classification modal is shown
            }
        } catch (error) {
            console.error('Error in checkAndHandleClassification:', error);
        }

        console.log('🔧 No classification needed');
        return false; // No classification needed
    };



    // Execute tool action (after classification if needed)
    const executeToolAction = (toolName, options = {}) => {
        // Special handling for POC Funding Review - now uses Universal Classification
        if (toolName === 'POC Funding Review') {
            const prompt = "Please review the documents to see if they comply with Proof Of Concept funding (POC) requirements.";

            if (onSendMessage) {
                onSendMessage(prompt, {
                    useTools: true,
                    intent: 'poc_funding_review',
                    ...options
                });
            }
            return;
        }

        // Get the appropriate prompt and intent based on the tool
        let prompt = '';
        let intent = null;
        let useTools = true;

        switch (toolName) {
            case 'Create Architecture Diagram':
                prompt = "Use available tools to create a detailed and accurate architecture diagram of this solution.";
                intent = "diagram";
                break;
            case 'Pricing Calculator':
                prompt = "Using tools, provide a detailed monthly cost estimate of all AWS services that make up this solution. Include estimated data transfer out charges in the cost estimate.";
                intent = "cost";
                break;
            case 'Partner Funding Analysis':
                prompt = "Using tools, analyze the solution and extract the correct funding programs that this solution is eligible for. Create a detailed funding analysis document and provide a summary of the detailed funding analysis.";
                intent = "funding";
                break;
            case 'Calculator Link':
                prompt = "Using tools, create a pricing calculator link for the proposed solution. Use the solution details to configure the AWS Pricing Calculator with the appropriate services and usage estimates.";
                intent = "calculator";
                break;
            case 'Statement of Work':
                prompt = "Provide a realistic professional services statement of work document which matches the complexity of the project in this conversation and matches the minimum viable professional services approach for this project.";
                intent = "documentation";
                break;
            case 'Generate CloudFormation Templates':
                prompt = "Follow the workflow in the generate_cloudformation_templates tool to generate, validate and save the CloudFormation templates for this solution";
                intent = "infrastructure";
                break;
            case 'Terraform':
                prompt = "Use tools to generate Terraform code for this solution.";
                intent = "infrastructure";
                break;
            default:
                console.warn(`No prompt defined for tool: ${toolName}`);
                return;
        }

        // Send message with enhanced options
        if (onSendMessage) {
            onSendMessage(prompt, { useTools, intent, ...options });
        } else {
            console.error('onSendMessage prop not provided to ChatToolbar');
        }
    };

    // Handle tool button clicks with classification check
    const handleToolClick = async (toolName) => {
        try {
            // Check if classification is needed
            const needsClassification = await checkAndHandleClassification('tool', toolName);

            if (!needsClassification) {
                // Execute immediately if no classification needed
                executeToolAction(toolName);
            }
        } catch (error) {
            console.error('Error in handleToolClick:', error);
            // Fallback to direct execution
            executeToolAction(toolName);
        }
    };

    // Handle send message with classification check
    const handleSendMessage = async (message, options = {}) => {
        try {
            console.log('🔧 ChatToolbar.handleSendMessage called with:', {
                message,
                options,
                assistantPersona,
                hasSelectedFiles,
                selectedFilesCount: selectedFiles.length
            });

            // For APN Funding Assistant, automatically apply POC funding review validation and intent
            if (assistantPersona === 'apn_funding_assistant' && hasSelectedFiles) {
                console.log('🔧 APN Funding Assistant detected with files - applying validation');

                // Use pre-loaded auto-classifications
                console.log('🔧 Auto classifications:', autoClassifications);

                const enhancedOptions = {
                    ...options,
                    useTools: true,
                    intent: 'poc_funding_review',
                    fileClassifications: autoClassifications  // ✅ Always include auto-classifications
                };

                // Check if manual classification is needed
                const needsClassification = await checkAndHandleClassification('message', null, message, enhancedOptions);
                console.log('🔧 Manual classification needed:', needsClassification);

                if (!needsClassification) {
                    // Execute immediately with auto-classifications
                    console.log('🔧 No manual classification needed - executing with auto-classifications');
                    if (onSendMessage) {
                        onSendMessage(message, enhancedOptions);
                    }
                }
                return;
            }

            console.log('🔧 Standard flow - not APN or no files');
            // For other personas, use standard classification check
            const needsClassification = await checkAndHandleClassification('message', null, message, options);

            if (!needsClassification) {
                // Execute immediately if no classification needed
                if (onSendMessage) {
                    onSendMessage(message, options);
                }
            }
        } catch (error) {
            console.error('Error in handleSendMessage:', error);
            // Fallback to direct execution
            if (onSendMessage) {
                onSendMessage(message, options);
            }
        }
    };

    // Expose handleSendMessage method to parent component
    useImperativeHandle(ref, () => ({
        handleSendMessage: (message, options = {}) => {
            console.log('🔧 ChatToolbar.handleSendMessage called via ref with:', message, options);
            handleSendMessage(message, options);
        }
    }), [handleSendMessage]);

    // Map of tool names to their corresponding icon names in Cloudscape
    const toolIconMap = {
        'Upload file': 'upload',
        'Diagram': 'file-open',
        'Pricing Calculator': 'calculator',
        'Partner Funding': 'dollar',
        'Scope of Work': 'file-content',
        'ACE Opportunity': 'external',
        'CloudFormation': 'code',
        'Terraform': 'script'
    };

    // Tool button component with tooltip and custom styling
    const ToolButton = ({ iconName, iconComponent, title, onClick, disabled }) => {
        const isEnabled = !disabled && getToolEnabledState(title);
        const handleClick = onClick ? onClick : (() => isEnabled && handleToolClick(title));

        console.log(`ToolButton ${title}: onClick provided:`, !!onClick, 'isEnabled:', isEnabled);

        // Get appropriate tooltip message based on tool type
        const getTooltipMessage = (toolName, enabled) => {
            if (toolName === 'POC Funding Review') {
                if (!hasSelectedFiles) {
                    return 'POC Funding Review (Select files first)';
                }
                return enabled ? toolName : `${toolName} (Select files first)`;
            }

            if (enabled) return toolName;

            // Generate persona-specific tooltip messages based on the same logic used in getToolEnabledState
            if (assistantPersona === 'aws_solutions_assistant') {
                if (solutionCreationTools.includes(toolName)) {
                    return `${toolName} (Available in INITIAL, GATHERING_INFO, or SOLUTION_PROPOSED stage)`;
                }
                if (finalStageTools.includes(toolName)) {
                    return `${toolName} (Available in SOLUTION_FINALIZED stage)`;
                }
                if (fundingAnalysisTools.includes(toolName)) {
                    return `${toolName} (Select files or reach SOLUTION_PROPOSED/FINALIZED stage)`;
                }
            }

            if (assistantPersona === 'apn_funding_assistant') {
                if (solutionCreationTools.includes(toolName)) {
                    return `${toolName} (Available in SOLUTION_PROPOSED or SOLUTION_FINALIZED stage)`;
                }
                if (finalStageTools.includes(toolName)) {
                    return `${toolName} (Available in SOLUTION_FINALIZED stage)`;
                }
            }

            return toolName;
        };

        // Custom button for SVG icons
        if (iconComponent) {
            return (
                <div style={{ display: 'inline-block', margin: '0 4px' }}>
                    <button
                        onClick={handleClick}
                        disabled={!isEnabled}
                        title={getTooltipMessage(title, isEnabled)}
                        style={{
                            background: 'none',
                            border: 'none',
                            padding: '6px',
                            cursor: isEnabled ? 'pointer' : 'not-allowed',
                            opacity: isEnabled ? '1' : '0.5',
                            borderRadius: '4px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            minWidth: '36px',
                            minHeight: '36px',
                            color: 'inherit',
                            transition: 'background-color 0.2s ease',
                        }}
                        onMouseEnter={(e) => {
                            if (isEnabled) {
                                e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.1)';
                            }
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = 'transparent';
                        }}
                        aria-label={title}
                    >
                        {iconComponent()}
                    </button>
                </div>
            );
        }

        return (
            <div style={{ display: 'inline-block', margin: '0 4px' }}>
                <button
                    onClick={() => isEnabled && handleToolClick(title)}
                    disabled={!isEnabled}
                    title={getTooltipMessage(title, isEnabled)}
                    style={{
                        background: 'none',
                        border: 'none',
                        padding: '6px',
                        cursor: isEnabled ? 'pointer' : 'not-allowed',
                        opacity: isEnabled ? '1' : '0.5',
                        borderRadius: '4px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        minWidth: '36px',
                        minHeight: '36px',
                        color: 'inherit',
                        transition: 'background-color 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                        if (isEnabled) {
                            e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.1)';
                        }
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                    aria-label={title}
                >
                    <Icon name={iconName} size="medium" />
                </button>
            </div>
        );
    };

    // Define which tools to show based on assistant persona
    const getVisibleTools = () => {
        if (assistantPersona === 'apn_funding_assistant') {
            // APN Funding Assistant: Only show upload files
            return ['Upload files'];
        }
        
        if (assistantPersona === 'aws_solutions_assistant') {
            // AWS Solutions Assistant: Show all solution creation tools
            return [
                'Upload files',
                'Create Architecture Diagram',
                'Pricing Calculator',
                'Calculator Link',
                'Partner Funding Analysis',
                'Statement of Work',
                'Generate CloudFormation Templates'
            ];
        }

        // Other personas: Show all tools
        return [
            'Upload files',
            'Create Architecture Diagram',
            'Pricing Calculator',
            'Calculator Link',
            'Partner Funding Analysis',
            'Statement of Work',
            'Generate CloudFormation Templates'
        ];
    };

    const visibleTools = getVisibleTools();
    const shouldShowTool = (toolName) => visibleTools.includes(toolName);

    return (
        <>
            <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                {/* Upload Files Button */}
                {shouldShowTool('Upload files') && onFileUpload && fileInputRef && (
                    <ToolButton
                        iconComponent={UploadIcon}
                        title="Upload files"
                        disabled={disabled || chatLoading || !isConnected}
                        onClick={() => fileInputRef.current?.click()}
                    />
                )}

                {/* Additional tools - enabled based on conversation stage and persona */}
                {shouldShowTool('Create Architecture Diagram') && (
                    <ToolButton
                        iconComponent={ShareIcon}
                        title="Create Architecture Diagram"
                        disabled={disabled}
                    />
                )}

                {shouldShowTool('Pricing Calculator') && (
                    <ToolButton
                        iconComponent={CalculatorIcon}
                        title="Pricing Calculator"
                        disabled={disabled}
                    />
                )}

                {shouldShowTool('Calculator Link') && (
                    <ToolButton 
                        iconComponent={CalculatorLinkIcon}
                        title="Calculator Link" 
                        disabled={disabled}
                    />
                )}

                {shouldShowTool('Partner Funding Analysis') && (
                    <ToolButton
                        iconComponent={PartnerFundingIcon}
                        title="Partner Funding Analysis"
                        disabled={disabled}
                    />
                )}

                {shouldShowTool('Statement of Work') && (
                    <ToolButton
                        iconComponent={StatementOfWorkIcon}
                        title="Statement of Work"
                        disabled={disabled}
                    />
                )}

                {/* ACE Opportunity tool - temporarily disabled for MVP */}
                {/* <ToolButton 
                    iconName="external" 
                    title="ACE Opportunity" 
                /> */}

                {shouldShowTool('Generate CloudFormation Templates') && (
                    <ToolButton
                        iconComponent={CloudFormationIcon}
                        title="Generate CloudFormation Templates"
                        disabled={disabled}
                    />
                )}

                {/* <ToolButton 
                    iconName="script" 
                    title="Terraform" 
                /> */}

                {/* POC Funding Review - only show for non-APN personas */}
                {shouldShowTool('POC Funding Review') && (
                    <ToolButton
                        iconComponent={POCFundingReviewIcon}
                        title="POC Funding Review"
                        disabled={disabled}
                    />
                )}
            </SpaceBetween>

            {/* Universal File Classification Modal */}
            <FileClassificationModal
                isVisible={isFileClassificationModalVisible}
                onClose={() => {
                    setIsFileClassificationModalVisible(false);
                    setFileClassifications({});
                    setPendingAction(null);
                }}
                onContinue={executeActionWithClassifications}
                selectedFiles={selectedFiles}
                fileClassifications={fileClassifications}
                onFileClassification={handleFileClassification}
                autoClassifications={autoClassifications}
                classificationOptions={classificationOptions}
                validationResult={validationResult}
                assistantPersona={assistantPersona}
                getFileClassification={getFileClassification}
                getSelectOptions={getSelectOptions}
            />
        </>
    );
});

export default ChatToolbar;