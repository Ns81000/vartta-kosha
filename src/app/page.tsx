'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Newspaper, BookOpen, RefreshCw, Calendar, Languages, FileText, Download } from 'lucide-react';
import { useNewspaper } from '@/hooks/use-newspaper';
import { DatePicker } from '@/components/features/date-picker';
import { DownloadProgress } from '@/components/features/download-progress';
import { NeumorphicSelect } from '@/components/ui/neumorphic-select';
import { NeumorphicCard } from '@/components/ui/neumorphic-card';
import { NeumorphicButton } from '@/components/ui/neumorphic-button';
import { cn } from '@/lib/utils/cn';
import { format } from 'date-fns';

export default function Home() {
  const {
    date,
    language,
    newspaper,
    edition,
    languages,
    newspapers,
    editions,
    downloadReady,
    error,
    progress,
    loading,
    setDate,
    setLanguage,
    setNewspaper,
    setEdition,
    startDownload,
    triggerDownload,
    cancelDownload,
    reset,
    canStartDownload,
    isAnyLoading,
    selectedNewspaper,
    selectedEdition,
  } = useNewspaper();

  const languageOptions = languages.map(l => ({
    value: l.id,
    label: l.name,
    sublabel: l.nativeName !== l.name ? l.nativeName : undefined,
  }));

  const newspaperOptions = newspapers.map(n => ({
    value: n.id,
    label: n.name,
  }));

  const editionOptions = editions.map(e => ({
    value: e.id,
    label: e.name,
    sublabel: e.pagesCount ? `${e.pagesCount} pages` : undefined,
  }));

  const showSelectionSummary = date && language && newspaper && edition && !loading.download && !downloadReady;

  return (
    <div className="min-h-screen bg-[var(--bg-base)] flex flex-col">
      {/* Fixed Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass-effect border-b border-[var(--shadow-dark)]/10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <motion.div 
              className="flex items-center gap-3"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <div className={cn(
                'w-10 h-10 rounded-xl',
                'bg-[var(--bg-elevated)]',
                'shadow-[4px_4px_8px_var(--shadow-dark),-4px_-4px_8px_var(--shadow-light)]',
                'flex items-center justify-center'
              )}>
                <Newspaper className="w-5 h-5 text-[var(--accent-primary)]" />
              </div>
              <h1 className="text-lg font-bold font-[var(--font-heading)] text-[var(--text-primary)]">
                The Chronicle Vault
              </h1>
            </motion.div>

            {/* Right side */}
            <div className="flex items-center gap-3">
              {isAnyLoading && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className={cn(
                    'inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm',
                    'bg-[var(--bg-elevated)]',
                    'shadow-[3px_3px_6px_var(--shadow-dark),-3px_-3px_6px_var(--shadow-light)]'
                  )}
                >
                  <div className="w-2 h-2 rounded-full bg-[var(--accent-primary)] animate-pulse" />
                  <span className="text-[var(--text-muted)]">Loading...</span>
                </motion.div>
              )}
              
              {date && (
                <NeumorphicButton
                  variant="ghost"
                  size="sm"
                  onClick={reset}
                >
                  <RefreshCw className="w-4 h-4" />
                  <span className="hidden sm:inline">Reset</span>
                </NeumorphicButton>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Spacer for fixed header */}
      <div className="h-16" />

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Hero Section - shown when nothing selected */}
        <AnimatePresence mode="wait">
          {!date && (
            <motion.div
              key="hero"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="text-center mb-12"
            >
              <motion.div
                initial={{ scale: 0.8 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: 'spring' }}
                className={cn(
                  'w-20 h-20 mx-auto mb-6 rounded-3xl',
                  'bg-[var(--bg-elevated)]',
                  'shadow-[12px_12px_24px_var(--shadow-dark),-12px_-12px_24px_var(--shadow-light)]',
                  'flex items-center justify-center'
                )}
              >
                <BookOpen className="w-10 h-10 text-[var(--accent-primary)]" />
              </motion.div>
              
              <h2 className="text-3xl sm:text-4xl font-bold font-[var(--font-heading)] text-[var(--text-primary)] mb-3">
                The Chronicle Vault
              </h2>
              <p className="text-lg text-[var(--text-secondary)] max-w-lg mx-auto mb-2">
                Access Indian newspapers from across 14 languages
              </p>
              <p className="text-sm text-[var(--text-muted)] italic mb-8">
                &ldquo;Where yesterday&apos;s news becomes tomorrow&apos;s history&rdquo;
              </p>

              {/* Stats */}
              <div className="flex items-center justify-center gap-6 text-sm text-[var(--text-muted)]">
                <span className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  Jul 2025 - Today
                </span>
                <span className="flex items-center gap-2">
                  <Languages className="w-4 h-4" />
                  14 Languages
                </span>
                <span className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  100+ Papers
                </span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Selection Panel */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <NeumorphicCard className="mb-6">
            {/* Title */}
            <div className="flex items-center gap-3 mb-6">
              <div className={cn(
                'w-8 h-8 rounded-lg',
                'bg-[var(--accent-primary)]/10',
                'flex items-center justify-center'
              )}>
                <Newspaper className="w-4 h-4 text-[var(--accent-primary)]" />
              </div>
              <h3 className="text-lg font-semibold font-[var(--font-heading)] text-[var(--text-primary)]">
                Select Newspaper
              </h3>
            </div>

            {/* Selectors Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {/* Date Picker */}
              <DatePicker
                value={date}
                onChange={setDate}
                label="Date"
              />

              {/* Language Selector */}
              <NeumorphicSelect
                label="Language"
                options={languageOptions}
                value={language}
                onChange={setLanguage}
                placeholder={date ? "Select language..." : "Select date first"}
                disabled={!date || loading.languages}
                loading={loading.languages}
              />

              {/* Newspaper Selector */}
              <NeumorphicSelect
                label="Newspaper"
                options={newspaperOptions}
                value={newspaper}
                onChange={setNewspaper}
                placeholder={language ? "Select newspaper..." : "Select language first"}
                disabled={!language || loading.newspapers}
                loading={loading.newspapers}
              />

              {/* Edition Selector */}
              <NeumorphicSelect
                label="Edition"
                options={editionOptions}
                value={edition}
                onChange={setEdition}
                placeholder={newspaper ? "Select edition..." : "Select newspaper first"}
                disabled={!newspaper || loading.editions}
                loading={loading.editions}
              />
            </div>

            {/* Selection Summary & Download Button */}
            <AnimatePresence mode="wait">
              {showSelectionSummary && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className={cn(
                    'rounded-xl p-4 mb-4',
                    'bg-[var(--bg-inset)]',
                    'shadow-[inset_3px_3px_6px_var(--shadow-inset-dark),inset_-3px_-3px_6px_var(--shadow-inset-light)]'
                  )}>
                    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                      <span className="text-[var(--text-muted)]">
                        <span className="font-medium text-[var(--text-primary)]">{selectedNewspaper?.name}</span>
                      </span>
                      <span className="text-[var(--text-muted)]">
                        {date && format(date, 'MMMM d, yyyy')}
                      </span>
                      <span className="text-[var(--text-muted)]">
                        {selectedEdition?.name}
                        {selectedEdition?.pagesCount && ` • ${selectedEdition.pagesCount} pages`}
                      </span>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Download Button */}
            <NeumorphicButton
              variant="primary"
              className="w-full"
              size="lg"
              disabled={!canStartDownload}
              loading={loading.download}
              onClick={startDownload}
            >
              <Download className="w-5 h-5" />
              {loading.download ? 'Preparing Download...' : 'Download Newspaper'}
            </NeumorphicButton>

            {/* Error Display */}
            <AnimatePresence>
              {error && !loading.download && !downloadReady && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className={cn(
                    'mt-4 p-3 rounded-xl',
                    'bg-[var(--state-error)]/10',
                    'border border-[var(--state-error)]/20'
                  )}
                >
                  <p className="text-sm text-[var(--state-error)]">{error}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </NeumorphicCard>
        </motion.div>

        {/* Download Progress Section */}
        <AnimatePresence>
          {(loading.download || downloadReady || (error && progress)) && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <DownloadProgress
                progress={progress}
                downloadReady={downloadReady}
                error={loading.download ? null : error}
                onDownload={triggerDownload}
                onCancel={cancelDownload}
                onRetry={startDownload}
                newspaperName={selectedNewspaper?.name}
                editionName={selectedEdition?.name}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Info Section - shown when date is selected but no download in progress */}
        <AnimatePresence>
          {date && !loading.download && !downloadReady && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ delay: 0.3 }}
              className="mt-8"
            >
              <NeumorphicCard variant="pressed" padding="sm">
                <div className="flex flex-wrap items-center justify-between gap-4 text-xs text-[var(--text-muted)]">
                  <p><strong>Archive Range:</strong> July 29, 2025 - Today</p>
                  <p><strong>Languages:</strong> Bengali, Hindi, English, Tamil, Telugu, and 9 more</p>
                  <p><strong>Papers:</strong> 100+ regional and national publications</p>
                </div>
              </NeumorphicCard>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="mt-auto py-6 border-t border-[var(--shadow-dark)]/10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-[var(--text-muted)]">
            <p>
              © {new Date().getFullYear()} The Chronicle Vault
            </p>
            <p className="text-xs">
              Indian Newspaper Archive • 14 Languages • 100+ Publications
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
