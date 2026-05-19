import React, { useState } from 'react';
import Button from '@cloudscape-design/components/button';
import { downloadSOW } from '../../services/sowService';

/**
 * Tool for downloading SOW PDF documents
 */
function SOWDownloadTool({ chatId, s3Url, versionId }) {
    const [loading, setLoading] = useState(false);
    
    const handleDownload = async (e) => {
        e.stopPropagation();
        
        try {
            setLoading(true);
            await downloadSOW(chatId, versionId);
        } catch (error) {
            console.error('Error downloading SOW:', error);
            // Could add toast notification here
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <Button
            iconName="download"
            variant="icon"
            onClick={handleDownload}
            loading={loading}
            ariaLabel="Download SOW PDF"
            title="Download Statement of Work PDF"
        />
    );
}

export default SOWDownloadTool;