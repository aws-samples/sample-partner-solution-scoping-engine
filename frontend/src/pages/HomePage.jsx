import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Container,
    Header,
    SpaceBetween,
    Form,
    FormField,
    Select,
    Button,
    Box,
    Alert,
    StatusIndicator,
    Input,
    Modal
} from '@cloudscape-design/components';

import { createChat, getPersonas } from '../services/chatService';

const HomePage = () => {
    const navigate = useNavigate();
    const [assistantOptions, setAssistantOptions] = useState([]);
    const [personaOptions, setPersonaOptions] = useState([]);
    const [selectedAssistant, setSelectedAssistant] = useState(null);
    const [selectedPersona, setSelectedPersona] = useState(null);
    const [selectedMethod, setSelectedMethod] = useState(null);
    const [chatName, setChatName] = useState('');
    const [showChatNameModal, setShowChatNameModal] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const [isLoadingPersonas, setIsLoadingPersonas] = useState(true);

    // Fetch personas on component mount
    useEffect(() => {
        const fetchPersonas = async () => {
            try {
                const data = await getPersonas();
                
                // Set customer personas
                setPersonaOptions(data.customers);
                
                // Find and set "Customer Technical Subject Matter Expert" as default
                const technicalSME = data.customers.find(persona => 
                    persona.label && persona.label.includes("Customer Technical Subject Matter Expert")
                );
                setSelectedPersona(technicalSME || null);

                // Set assistant personas
                setAssistantOptions(data.assistants);
                if (data.assistants.length > 0) {
                    setSelectedAssistant(data.assistants[0]);
                }
            } catch (error) {
                console.error("Error fetching personas:", error);
                setErrorMessage("Failed to load personas. Please try again later.");
            } finally {
                setIsLoadingPersonas(false);
            }
        };

        fetchPersonas();
    }, []);

    // Auto-set interaction method to email (UI hidden but backend still requires it)
    // Keep infrastructure for future expansion (voice/live chat)
    useEffect(() => {
        setSelectedMethod({ label: "Email Exchange", value: "email" });
    }, []);

    const handleStartChat = async (event) => {
        // Prevent form submission default behavior
        if (event) event.preventDefault();
        
        if (!selectedAssistant) {
            setErrorMessage('Please select an assistant persona');
            return;
        }
        
        if (!selectedPersona) {
            setErrorMessage('Please select a persona');
            return;
        }

        // Show modal to get chat name
        setShowChatNameModal(true);
    };

    const handleCreateChat = async () => {
        if (!chatName.trim()) {
            setErrorMessage('Please enter a chat name');
            return;
        }

        setIsLoading(true);
        setErrorMessage(null);
        setShowChatNameModal(false);

        try {
            // Create chat config for the createChat service function
            const chatConfig = {
                assistantId: selectedAssistant,
                customerPersona: selectedPersona,
                interactionMethod: selectedMethod.value,
                chatName: chatName.trim()
            };
            
            console.log('Creating chat with config:', chatConfig);
            
            // Use the createChat service function
            const data = await createChat(chatConfig);
            
            // Save the chat ID to localStorage
            localStorage.setItem('lastCreatedChat', JSON.stringify({
                chatId: data.chatId,
                timestamp: new Date().toISOString()
            }));
            
            // Refresh the sidebar
            if (window.refreshRecentChats) {
                window.refreshRecentChats();
            }
            
            // Navigate to the chat
            navigate(`/chat/${data.chatId}`);
            
        } catch (error) {
            console.error('Error in handleStartChat:', error);
            setErrorMessage(error.message || 'Failed to start chat');
        } finally {
            setIsLoading(false);
        }
    };

    const isStartDisabled = !selectedPersona || !selectedMethod || isLoading || isLoadingPersonas;

    return (
        <>
            <Box padding={{ vertical: "l", horizontal: "l" }}>
            {/* Regular form */}
            <form onSubmit={(e) => {
                e.preventDefault(); // Prevent default form submission
                handleStartChat(e);
            }}>
                <Form
                    actions={
                        <SpaceBetween direction="horizontal" size="xs">
                            <Button 
                                variant="primary" 
                                type="submit"
                                disabled={isStartDisabled}
                                loading={isLoading}
                            >
                                Start New Chat
                            </Button>
                        </SpaceBetween>
                    }
                    errorText={errorMessage ? (
                         <Alert 
                            statusIconAriaLabel="Error"
                            type="error"
                            header="Failed to start chat"
                         >
                             {errorMessage}
                         </Alert>
                    ) : null}
                >
                    <Container
                        header={
                            <Header variant="h2">
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
                                <span>Hi! I'm SERA, your Solutions Engine for Recommending AWS, powered by Amazon Bedrock.<br/></span>
                            </div>
                            <div style={{fontSize: '0.7em', marginLeft: '42px'}}>
                                    Helping you transform customer requirements into winning AWS solutions. Get architecture designs, pricing estimates, funding ideas, and more - all in one conversation.
                            </div>
                            </Header>
                        }
                    >
                        <SpaceBetween direction="vertical" size="l">
                            <Alert type="info" header="SERA is in limited preview.">
                                <div style={{ fontSize: '0.9em' }}>
                                    During the prototyping engagement/proof of concept, AWS may use third-party models ("Third-Party Models") that AWS does not own, and that AWS does not exercise control over. By using any prototype or proof of concept from AWS you acknowledge that the Third-Party Models are "Third-Party Content" under your agreement for services with AWS. You should perform your own independent assessment of the Third-Party Models. You should also take measures to ensure that your use of the Third-Party Models complies with your own specific quality control practices and standards, and the local rules, laws, regulations, licenses and terms of use that apply to you, your content, and the Third-Party Models. AWS does not make any representations or warranties regarding the Third-Party Models, including that use of the Third-Party Models and the associated outputs will result in a particular outcome or result. You also acknowledge that outputs generated by the Third-Party Models are Your Content/Customer Content, as defined in the AWS Customer Agreement or the agreement between you and AWS for AWS Services. You are responsible for your use of outputs from the Third-Party Models.
                                </div>
                            </Alert>
                            
                            <div style={{ marginTop: '20px' }}></div>
                            
                            <FormField
                                label="Select AI Assistant"
                                description="Choose the AI assistant you want to interact with."
                            >
                                <Select
                                    selectedOption={selectedAssistant}
                                    onChange={({ detail }) => setSelectedAssistant(detail.selectedOption)}
                                    options={assistantOptions}
                                    filteringType="none"
                                    loading={isLoadingPersonas}
                                    disabled={isLoadingPersonas}
                                    selectedAriaLabel="Selected"
                                    placeholder="Select Assistant Persona..."
                                />
                                {selectedAssistant?.description && (
                                    <Box margin={{ top: "s" }}>
                                        <StatusIndicator type="info">
                                            {selectedAssistant.description}
                                        </StatusIndicator>
                                    </Box>
                                )}
                            </FormField>

                            <FormField
                                label="Select Customer/Partner Persona"
                                description="Choose the persona you are selling to or interacting with."
                            >
                                <Select
                                    selectedOption={selectedPersona}
                                    onChange={({ detail }) => {
                                        setSelectedPersona(detail.selectedOption);
                                    }}
                                    options={personaOptions}
                                    filteringType="auto"
                                    loading={isLoadingPersonas}
                                    disabled={isLoadingPersonas}
                                    selectedAriaLabel="Selected"
                                    placeholder="Select Customer/Partner Persona..."
                                    empty="No personas available"
                                />
                                {selectedPersona?.value && selectedPersona?.description && (
                                    <Box margin={{ top: "s" }}>
                                        <StatusIndicator type="info">
                                            {selectedPersona.description}
                                        </StatusIndicator>
                                    </Box>
                                )}
                            </FormField>
                        </SpaceBetween>
                    </Container>
                </Form>
            </form>
        </Box>

        <Modal
            onDismiss={() => setShowChatNameModal(false)}
            visible={showChatNameModal}
            header="Name Your Chat"
            closeAriaLabel="Close modal"
            size="medium"
            footer={
                <Box float="right">
                    <SpaceBetween direction="horizontal" size="xs">
                        <Button variant="link" onClick={() => setShowChatNameModal(false)}>
                            Cancel
                        </Button>
                        <Button variant="primary" onClick={handleCreateChat} loading={isLoading}>
                            Create Chat
                        </Button>
                    </SpaceBetween>
                </Box>
            }
        >
            <SpaceBetween direction="vertical" size="s">
                <div>Give your chat a descriptive name to help you remember what it's about.</div>
                <div style={{ width: '70%' }}>
                    <Input
                        value={chatName}
                        onChange={({ detail }) => setChatName(detail.value)}
                        placeholder="e.g., ACME Corp Migration"
                        autoFocus
                    />
                </div>
            </SpaceBetween>
        </Modal>
        </>
    );
};

export default HomePage; 