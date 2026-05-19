import { useState, useEffect } from 'react';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Box from '@cloudscape-design/components/box';
import ExpandableSection from '@cloudscape-design/components/expandable-section';
import Link from '@cloudscape-design/components/link';
import Alert from '@cloudscape-design/components/alert';
import { getDocumentCFSignedUrl } from '../services/fileService';

const HelpPage = () => {
  const [videoUrl, setVideoUrl] = useState('');

  useEffect(() => {
    // Get signed URL for tutorial video - use 'static' as chatId for static files
    getDocumentCFSignedUrl('static', 'tutorial.mp4')
      .then(response => {
        console.log('Video URL response:', response);
        setVideoUrl(response.url || response);
      })
      .catch(err => {
        console.error('Failed to load tutorial video:', err);
        // Fallback to direct URL (will fail but shows the attempt)
        setVideoUrl('');  // Tutorial video not available
      });
  }, []);
  return (
    <Container
      header={
        <Header variant="h1">
          Getting Started with SERA
        </Header>
      }
    >
      <SpaceBetween direction="vertical" size="l">
        <Alert type="info">
          Helping you transform customer requirements into winning AWS solutions. Get architecture designs, pricing estimates, funding ideas, and more - all in one conversation..
        </Alert>

        <ExpandableSection headerText="Tutorial Video" defaultExpanded={true}>
          <Box>
            {videoUrl ? (
              <video 
                width="100%" 
                controls
                style={{ maxWidth: '800px', aspectRatio: '16/10' }}
                onError={(e) => console.error('Video error:', e)}
                onLoadStart={() => console.log('Video loading started')}
                onCanPlay={() => console.log('Video can play')}
              >
                <source src={videoUrl} type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            ) : (
              <Box>Loading tutorial video...</Box>
            )}
          </Box>
        </ExpandableSection>

        <ExpandableSection headerText="Quick Start" defaultExpanded={true}>
          <SpaceBetween direction="vertical" size="m">
            <Box variant="h3">1. Start a New Chat</Box>
            <Box>
              • Click "New Chat/Home" in The left menu, and "Start New Chat" to begin a conversation.<br/>
              • Describe your project requirements or ask questions.<br/>
              • SERA will analyze and provide AWS solutions.
            </Box>

            <Box variant="h3">2. Provide Context Data</Box>
            <Box>
              • Paste Document Text into the text Input field. Examples: Meeting summaries, emails, etc.<br/>
              • Sera can understand Migration Evaluator - copy the raw CSV and paste the first 8 columns of the rvtools DefaultUtil file (as csv, Not excel). SERA can analyze about 100 lines of data per conversation.<br/>
              • SERA will analyze the content and provide relevant recommendations.<br/>
            </Box>

            <Box variant="h3">3. Generate Solutions</Box>
            <Box>
              • As you conversation progresses, tools will be made available and activated in the toolbar below the chat input field.<br/>
              • Use the toolbar to create architecture diagrams, cost estimates, funding plans, statements of work, or CloudFormation templates.<br/>
            </Box>
          </SpaceBetween>
        </ExpandableSection>

        <ExpandableSection headerText="Sample Questions">
          <SpaceBetween direction="vertical" size="s">
            <Box>• "IHAC that wants to reduce their web app hosting costs, what are some options?"</Box>
            <Box>• "What's the best database for an e-commerce application?"</Box>
            <Box>• "Analyze this RFP and suggest an AWS solution" (Paste RFP text into chat)</Box>

          </SpaceBetween>
        </ExpandableSection>

        <ExpandableSection headerText="Tips for Best Results">
          <SpaceBetween direction="vertical" size="s">
            <Box>• Build on details as you progress in the conversation</Box>
            <Box>• Mention your industry, compliance needs, and scale requirements</Box>
            <Box>• Ask follow-up questions to refine recommendations</Box>
            <Box>• Provide relevant data for context</Box>
            <Box>• Use the chat history to build on previous conversations</Box>
          </SpaceBetween>
        </ExpandableSection>

        <ExpandableSection headerText="Manage your chats">
          <SpaceBetween direction="vertical" size="s">
            <Box>• Use the edit icon next to a recent chat in the menu to change the chat title</Box>
            <Box>• When viewing all chats, you can toggle views between Chats that are Finalized Solutions or in progress</Box>
          </SpaceBetween>
        </ExpandableSection>

        <ExpandableSection headerText="Have your solutions reviewed by human experts">
          <SpaceBetween direction="vertical" size="s">
            <Box>• Assign reviewers in Support Settings</Box>
            <Box>• Your reviewers can ask questions or create updated documents in your chat, then ready their changes to merge.</Box>
            <Box>• Use the "Merge" button to merge your reviewer's changes into your chat</Box>
          </SpaceBetween>
        </ExpandableSection>
      </SpaceBetween>
    </Container>
  );
};

export default HelpPage;
