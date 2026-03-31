'use client';

import { motion } from 'framer-motion';
import { Loader2, CheckCircle, AlertCircle, Download, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils/cn';
import { NeumorphicButton } from '@/components/ui/neumorphic-button';
import type { ProgressState } from '@/types';

interface PdfViewerProps {
  pdfUrl: string | null;
  progress: ProgressState | null;
  error: string | null;
  onRetry?: () => void;
}

export function PdfViewer({ pdfUrl, progress, error, onRetry }: PdfViewerProps) {
  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center py-12"
      >
        <div className={cn(
          'w-16 h-16 mx-auto mb-4 rounded-full',
          'bg-[var(--bg-inset)]',
          'shadow-[inset_4px_4px_8px_var(--shadow-inset-dark),inset_-4px_-4px_8px_var(--shadow-inset-light)]',
          'flex items-center justify-center'
        )}>
          <AlertCircle className="w-8 h-8 text-[var(--state-error)]" />
        </div>
        <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
          Unable to Load PDF
        </h3>
        <p className="text-[var(--text-secondary)] mb-4 max-w-md mx-auto">
          {error}
        </p>
        {onRetry && (
          <NeumorphicButton onClick={onRetry}>
            Try Again
          </NeumorphicButton>
        )}
      </motion.div>
    );
  }
  
  if (progress && progress.stage !== 'complete') {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center py-12"
      >
        <div className={cn(
          'w-20 h-20 mx-auto mb-6 rounded-full',
          'bg-[var(--bg-elevated)]',
          'shadow-[8px_8px_16px_var(--shadow-dark),-8px_-8px_16px_var(--shadow-light)]',
          'flex items-center justify-center'
        )}>
          <Loader2 className="w-10 h-10 text-[var(--accent-primary)] animate-spin" />
        </div>
        
        <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
          {progress.message}
        </h3>
        
        {progress.total && progress.current !== undefined && (
          <div className="max-w-xs mx-auto mt-4">
            <div className={cn(
              'h-3 rounded-full overflow-hidden',
              'bg-[var(--bg-inset)]',
              'shadow-[inset_2px_2px_4px_var(--shadow-inset-dark),inset_-2px_-2px_4px_var(--shadow-inset-light)]'
            )}>
              <motion.div
                className="h-full bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${(progress.current / progress.total) * 100}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
            <p className="text-sm text-[var(--text-muted)] mt-2">
              {progress.current} / {progress.total}
            </p>
          </div>
        )}
      </motion.div>
    );
  }
  
  if (pdfUrl) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-4"
      >
        {/* Success header */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className={cn(
              'w-10 h-10 rounded-full',
              'bg-[var(--state-success)]/20',
              'flex items-center justify-center'
            )}>
              <CheckCircle className="w-5 h-5 text-[var(--state-success)]" />
            </div>
            <div>
              <p className="font-medium text-[var(--text-primary)]">PDF Ready</p>
              <p className="text-sm text-[var(--text-muted)]">
                High quality newspaper
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <NeumorphicButton
              size="sm"
              onClick={() => window.open(pdfUrl, '_blank')}
            >
              <ExternalLink className="w-4 h-4" />
              Open
            </NeumorphicButton>
            
            <NeumorphicButton
              variant="primary"
              size="sm"
              onClick={() => {
                const link = document.createElement('a');
                link.href = pdfUrl;
                link.download = 'newspaper.pdf';
                link.click();
              }}
            >
              <Download className="w-4 h-4" />
              Download
            </NeumorphicButton>
          </div>
        </div>
        
        {/* PDF Preview */}
        <div className={cn(
          'rounded-2xl overflow-hidden',
          'bg-[var(--bg-inset)]',
          'shadow-[inset_4px_4px_8px_var(--shadow-inset-dark),inset_-4px_-4px_8px_var(--shadow-inset-light)]'
        )}>
          <iframe
            src={`${pdfUrl}#toolbar=1&navpanes=0`}
            className="w-full h-[600px] border-0"
            title="PDF Viewer"
          />
        </div>
      </motion.div>
    );
  }
  
  // Empty state
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="text-center py-16"
    >
      <div className={cn(
        'w-24 h-24 mx-auto mb-6 rounded-2xl',
        'bg-[var(--bg-inset)]',
        'shadow-[inset_4px_4px_8px_var(--shadow-inset-dark),inset_-4px_-4px_8px_var(--shadow-inset-light)]',
        'flex items-center justify-center'
      )}>
        <svg 
          className="w-12 h-12 text-[var(--text-muted)]" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
        No Newspaper Selected
      </h3>
      <p className="text-[var(--text-muted)] max-w-md mx-auto">
        Select a date, language, newspaper, and edition to view the PDF
      </p>
    </motion.div>
  );
}
